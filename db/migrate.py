"""Apply pending SQL migrations in order (A2; docs/07 section 9).

Files: db/migrations/NNN_description.sql, forward-only, never edited once applied. Each pending
file runs in its own transaction together with its `schema_migrations` row, so a failing
migration leaves nothing behind. A session advisory lock lets several services start at once.

Usage:  python db/migrate.py [--dir db/migrations] [--dry-run]
Connection: DATABASE_URL, or libpq PG* variables when it is unset.
Exit codes: 0 = up to date, 1 = a migration failed, 2 = bad migration directory.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
NAME = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
LOCK_ID = 0x6172656E61  # "arena": advisory lock key shared by all migrators


class MigrationError(Exception):
    """A migration failed (exit 1)."""


class MigrationDirError(MigrationError):
    """The migrations directory itself is invalid (exit 2)."""


def discover(directory: Path) -> list[tuple[str, Path]]:
    """[(version, path)] sorted; version = file stem, e.g. '001_init'."""
    found: dict[str, tuple[str, Path]] = {}
    for path in sorted(directory.glob("*.sql")):
        m = NAME.match(path.name)
        if not m:
            raise MigrationDirError(f"{path.name}: expected NNN_lowercase_name.sql")
        if m.group(1) in found:
            raise MigrationDirError(f"{path.name}: number {m.group(1)} already used by {found[m.group(1)][1].name}")
        found[m.group(1)] = (path.stem, path)
    return [found[k] for k in sorted(found)]


def applied_versions(conn: psycopg.Connection) -> set[str]:
    # 001_init creates schema_migrations itself, so a fresh database has no table yet.
    if conn.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0] is None:
        return set()
    return {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}


def migrate(dsn: str = "", directory: Path = MIGRATIONS_DIR, dry_run: bool = False,
            log=print) -> list[str]:
    """Apply pending migrations; return the versions applied (or that would be, with dry_run)."""
    migrations = discover(Path(directory))
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
        try:
            done = applied_versions(conn)
            if unknown := sorted(done - {v for v, _ in migrations}):
                log(f"warning: applied version(s) with no file here: {', '.join(unknown)}")
            pending = [(v, p) for v, p in migrations if v not in done]
            for version, path in pending:
                if dry_run:
                    log(f"pending  {version}")
                    continue
                log(f"applying {version}")
                try:
                    with conn.transaction():
                        conn.execute(path.read_text(encoding="utf8"))
                        conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)"
                                     " ON CONFLICT DO NOTHING", (version,))
                except psycopg.Error as e:
                    raise MigrationError(f"{version} failed and was rolled back: {e}") from e
            if not pending:
                log(f"up to date ({len(done)} applied)")
            return [v for v, _ in pending]
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", type=Path, default=MIGRATIONS_DIR)
    ap.add_argument("--dry-run", action="store_true", help="list pending migrations only")
    args = ap.parse_args(argv)
    try:
        migrate(os.environ.get("DATABASE_URL", ""), args.dir, args.dry_run)
    except MigrationError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2 if isinstance(e, MigrationDirError) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
