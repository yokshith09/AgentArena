"""A2 migration runner. Each DB test creates and drops its own throwaway database on the
server at DATABASE_URL / PG* env (needs CREATEDB, which the compose `arena` user has)."""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from db import migrate as m

ROOT = Path(__file__).resolve().parents[2]
DSN = os.environ.get("DATABASE_URL", "")


def _server_ok() -> bool:
    try:
        with psycopg.connect(DSN, connect_timeout=2) as c:
            c.execute("SELECT 1")
        return True
    except psycopg.Error:
        return False


needs_db = pytest.mark.skipif(not _server_ok(), reason="no Postgres at DATABASE_URL / PG* env")


@pytest.fixture
def fresh_db():
    name = f"arena_mig_test_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute(f'CREATE DATABASE "{name}"')
    try:
        yield make_conninfo(DSN, dbname=name)
    finally:
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture
def mig_dir(tmp_path):
    d = tmp_path / "migrations"
    d.mkdir()
    shutil.copy(ROOT / "db" / "migrations" / "001_init.sql", d)
    return d


def quiet(*_):
    pass


def tables(dsn) -> set[str]:
    with psycopg.connect(dsn) as c:
        return {r[0] for r in c.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}


def versions(dsn) -> list[str]:
    with psycopg.connect(dsn) as c:
        return [r[0] for r in c.execute("SELECT version FROM schema_migrations ORDER BY version")]


# ---- discovery (no DB) ------------------------------------------------------------------------
def test_repo_migrations_are_well_formed():
    assert m.discover(ROOT / "db" / "migrations")[0][0] == "001_init"


@pytest.mark.parametrize("files, msg", [
    (["001_init.sql", "1_bad.sql"], "expected NNN"),
    (["001_init.sql", "002_Add-Col.sql"], "expected NNN"),
    (["001_init.sql", "001_again.sql"], "already used"),
])
def test_discover_rejects_bad_names(tmp_path, files, msg):
    for f in files:
        (tmp_path / f).write_text("SELECT 1;", encoding="utf8")
    with pytest.raises(m.MigrationDirError, match=msg):
        m.discover(tmp_path)


def test_discover_sorts_numerically(tmp_path):
    for f in ("010_c.sql", "002_b.sql", "001_a.sql"):
        (tmp_path / f).write_text("SELECT 1;", encoding="utf8")
    assert [v for v, _ in m.discover(tmp_path)] == ["001_a", "002_b", "010_c"]


def test_cli_exit_2_on_bad_directory(tmp_path):
    (tmp_path / "bad.sql").write_text("SELECT 1;", encoding="utf8")
    assert m.main(["--dir", str(tmp_path)]) == 2


# ---- applying (throwaway DB) ------------------------------------------------------------------
@needs_db
def test_fresh_database_gets_full_schema_and_is_idempotent(fresh_db, mig_dir):
    assert m.migrate(fresh_db, mig_dir, log=quiet) == ["001_init"]
    assert {"agents", "tasks", "benchmarks", "runs", "events", "schema_migrations"} <= tables(fresh_db)
    assert versions(fresh_db) == ["001_init"]
    assert m.migrate(fresh_db, mig_dir, log=quiet) == []          # second run: nothing to do


@needs_db
def test_database_initialised_by_initdb_is_recognised(fresh_db, mig_dir):
    # Simulates the old path: Postgres initdb ran 001_init.sql directly.
    with psycopg.connect(fresh_db, autocommit=True) as c:
        c.execute((mig_dir / "001_init.sql").read_text(encoding="utf8"))
    assert m.migrate(fresh_db, mig_dir, log=quiet) == []


@needs_db
def test_new_migration_applies_in_order(fresh_db, mig_dir):
    m.migrate(fresh_db, mig_dir, log=quiet)
    (mig_dir / "003_c.sql").write_text("ALTER TABLE runs ADD COLUMN c3 int;", encoding="utf8")
    (mig_dir / "002_b.sql").write_text("ALTER TABLE runs ADD COLUMN c2 int;"
                                       " ALTER TABLE runs RENAME COLUMN c2 TO c2b;", encoding="utf8")
    assert m.migrate(fresh_db, mig_dir, log=quiet) == ["002_b", "003_c"]
    assert versions(fresh_db) == ["001_init", "002_b", "003_c"]


@needs_db
def test_failing_migration_rolls_back_and_stops(fresh_db, mig_dir):
    m.migrate(fresh_db, mig_dir, log=quiet)
    (mig_dir / "002_half.sql").write_text(
        "ALTER TABLE runs ADD COLUMN half int; SELECT * FROM no_such_table;", encoding="utf8")
    (mig_dir / "003_after.sql").write_text("ALTER TABLE runs ADD COLUMN after3 int;", encoding="utf8")
    with pytest.raises(m.MigrationError, match="002_half failed and was rolled back"):
        m.migrate(fresh_db, mig_dir, log=quiet)
    assert versions(fresh_db) == ["001_init"]
    with psycopg.connect(fresh_db) as c:
        cols = {r[0] for r in c.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'runs'")}
    assert "half" not in cols and "after3" not in cols


@needs_db
def test_dry_run_changes_nothing(fresh_db, mig_dir):
    lines = []
    assert m.migrate(fresh_db, mig_dir, dry_run=True, log=lines.append) == ["001_init"]
    assert lines == ["pending  001_init"]
    assert "agents" not in tables(fresh_db)


@needs_db
def test_cli_exit_codes(fresh_db, mig_dir, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", fresh_db)
    assert m.main(["--dir", str(mig_dir)]) == 0
    (mig_dir / "002_broken.sql").write_text("THIS IS NOT SQL;", encoding="utf8")
    assert m.main(["--dir", str(mig_dir)]) == 1
