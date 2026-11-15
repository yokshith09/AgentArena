"""Demo data freeze (X7): export real benchmarks to db/demo-data.sql and load them elsewhere.

  python db/demo.py export --benchmark ID [--benchmark ID ...] [--out db/demo-data.sql]
  python db/demo.py load [--file db/demo-data.sql]

export writes the chosen benchmarks plus every agent, task, run and event they reference, as plain
SQL INSERTs in one transaction. Fabricated fixtures are never exported unless named explicitly.
Event ids are not kept: events are inserted in their original order and get fresh ids, so the file
loads into a database that already has other events. load applies db/migrations first, then the
file; loading the same benchmarks twice fails (primary keys) and changes nothing.
Connection: DATABASE_URL, or libpq PG* variables when unset.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import migrate

DEFAULT_FILE = Path(__file__).resolve().parent / "demo-data.sql"
TABLES = {
    "agents": ["agent_id", "name", "mode", "entrypoint", "model_config", "description", "source_path", "created_at"],
    "tasks": ["task_id", "category", "prompt", "workspace", "grader", "reference_solution", "faults_allowed",
              "task_dir", "task_hash", "validated", "weak", "created_at"],
    "benchmarks": ["benchmark_id", "name", "config", "state", "error", "created_at", "started_at", "finished_at"],
    "runs": ["run_id", "agent_id", "task_id", "scenario", "model", "status", "passed", "tokens_in", "tokens_out",
             "cost", "cost_confidence", "duration", "steps", "env_fingerprint", "benchmark_id", "repeat_index",
             "attempt", "state", "tool_calls", "started_at", "finished_at", "grader_result", "workspace_diff", "error"],
    "events": ["run_id", "ts", "type", "agent_role", "payload", "latency", "error"],
}
JSON_COLS = {"model_config", "grader", "config", "env_fingerprint", "grader_result", "payload"}
UPSERT_IGNORE = {"agents": "agent_id", "tasks": "task_id"}  # may already exist from the seed loader


def _rows(conn, table: str, where: str, args) -> list[dict]:
    cols = sql.SQL(", ").join(map(sql.Identifier, TABLES[table]))
    order = {"events": "id", "runs": "started_at NULLS LAST, run_id", "benchmarks": "created_at"}.get(table, "1")
    q = sql.SQL("SELECT {} FROM {} WHERE " + where + " ORDER BY " + order).format(cols, sql.Identifier(table))
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        return cur.execute(q, args).fetchall()


def _insert(conn, table: str, row: dict) -> str:
    cols = TABLES[table]
    values = [Jsonb(row[c]) if c in JSON_COLS and row[c] is not None else row[c] for c in cols]
    stmt = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, cols)),
        sql.SQL(", ").join(sql.Literal(v) for v in values))
    if table in UPSERT_IGNORE:
        stmt = sql.SQL("{} ON CONFLICT ({}) DO NOTHING").format(stmt, sql.Identifier(UPSERT_IGNORE[table]))
    return stmt.as_string(conn) + ";\n"


def export(dsn: str, benchmark_ids: list[str], out: Path) -> dict[str, int]:
    with psycopg.connect(dsn) as conn:
        benches = _rows(conn, "benchmarks", "benchmark_id = ANY(%s::uuid[])", (benchmark_ids,))
        missing = set(benchmark_ids) - {str(b["benchmark_id"]) for b in benches}
        if missing:
            raise SystemExit(f"unknown benchmark id(s): {', '.join(sorted(missing))}")
        not_done = [b["name"] for b in benches if b["state"] not in ("completed", "halted_spend_cap")]
        if not_done:
            raise SystemExit(f"benchmark(s) not finished: {', '.join(not_done)}")
        runs = _rows(conn, "runs", "benchmark_id = ANY(%s::uuid[])", (benchmark_ids,))
        run_ids = [r["run_id"] for r in runs]
        agents = _rows(conn, "agents", "agent_id = ANY(%s)", (sorted({r["agent_id"] for r in runs}),))
        tasks = _rows(conn, "tasks", "task_id = ANY(%s)", (sorted({r["task_id"] for r in runs}),))
        events = _rows(conn, "events", "run_id = ANY(%s)", (run_ids,))
        counts = {"benchmarks": len(benches), "runs": len(runs), "events": len(events),
                  "agents": len(agents), "tasks": len(tasks)}
        lines = [
            "-- AgentArena demo data (X7): REAL benchmark runs, not fixtures.\n",
            f"-- Exported {dt.datetime.now(dt.UTC).isoformat(timespec='seconds')} by db/demo.py.\n",
            "-- Load into a fresh database with:  python db/demo.py load\n",
            "-- Contents: " + ", ".join(f"{v} {k}" for k, v in counts.items()) + ".\n",
            *[f"--   {b['benchmark_id']}  {b['name']}\n" for b in benches],
            "BEGIN;\n",
            *[_insert(conn, "agents", r) for r in agents],
            *[_insert(conn, "tasks", r) for r in tasks],
            *[_insert(conn, "benchmarks", r) for r in benches],
            *[_insert(conn, "runs", r) for r in runs],
            *[_insert(conn, "events", r) for r in events],
            "COMMIT;\n",
        ]
    out.write_text("".join(lines), encoding="utf8", newline="\n")
    return counts


def load(dsn: str, path: Path) -> None:
    migrate.migrate(dsn)
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(path.read_text(encoding="utf8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Export or load the frozen demo data (X7).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export")
    ex.add_argument("--benchmark", action="append", required=True, help="benchmark id (repeatable)")
    ex.add_argument("--out", type=Path, default=DEFAULT_FILE)
    ld = sub.add_parser("load")
    ld.add_argument("--file", type=Path, default=DEFAULT_FILE)
    args = ap.parse_args(argv)
    dsn = os.environ.get("DATABASE_URL", "")
    if args.cmd == "export":
        counts = export(dsn, args.benchmark, args.out)
        print(f"wrote {args.out}: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    else:
        try:
            load(dsn, args.file)
        except psycopg.errors.UniqueViolation:
            print("error: this demo data is already loaded (nothing changed)", file=sys.stderr)
            return 1
        print(f"loaded {args.file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
