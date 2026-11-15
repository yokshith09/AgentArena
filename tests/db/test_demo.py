"""X7 demo data: export from one throwaway DB, load into another, compare; refuse a second load."""
from __future__ import annotations

import os
import uuid

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from db import demo, migrate

DSN = os.environ.get("DATABASE_URL", "")


def _server_ok() -> bool:
    try:
        with psycopg.connect(DSN, connect_timeout=2) as c:
            c.execute("SELECT 1")
        return True
    except psycopg.Error:
        return False


pytestmark = pytest.mark.skipif(not _server_ok(), reason="no Postgres at DATABASE_URL / PG* env")


@pytest.fixture
def two_dbs():
    names = [f"arena_demo_test_{uuid.uuid4().hex[:8]}" for _ in range(2)]
    with psycopg.connect(DSN, autocommit=True) as c:
        for n in names:
            c.execute(f'CREATE DATABASE "{n}"')
    try:
        yield [make_conninfo(DSN, dbname=n) for n in names]
    finally:
        with psycopg.connect(DSN, autocommit=True) as c:
            for n in names:
                c.execute(f'DROP DATABASE IF EXISTS "{n}" WITH (FORCE)')


def _seed(dsn) -> tuple[str, str]:
    migrate.migrate(dsn, log=lambda *_: None)
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute("INSERT INTO agents (agent_id, name, mode, entrypoint, model_config, source_path)"
                  " VALUES ('a', 'a', 'command', 'python a.py', '{\"model\": \"m\"}', 'agents/a'),"
                  " ('unused', 'unused', 'command', 'x', '{}', 'x')")
        c.execute("INSERT INTO tasks (task_id, category, prompt, workspace, grader, reference_solution,"
                  " faults_allowed, task_dir, task_hash, validated)"
                  " VALUES ('t', 'coding', 'p', 'workspace', '{\"type\": \"pytest\"}', 'r', '{x}', 'tasks/t', 'h', true)")
        keep, other = (str(c.execute("INSERT INTO benchmarks (name, config, state) VALUES (%s, '{}', 'completed')"
                                     " RETURNING benchmark_id", (n,)).fetchone()[0]) for n in ("keep", "other"))
        for bid in (keep, other):
            rid = c.execute("INSERT INTO runs (benchmark_id, agent_id, task_id, state, status, passed, cost,"
                            " grader_result, started_at, finished_at) VALUES (%s, 'a', 't', 'done', 'PASS', true,"
                            " 0.000123, '{\"passed\": true}', now(), now()) RETURNING run_id", (bid,)).fetchone()[0]
            for t in ("agent_started", "llm_call", "grader_result"):
                c.execute("INSERT INTO events (run_id, type, payload) VALUES (%s, %s, %s)",
                          (rid, t, psycopg.types.json.Jsonb({"note": "quote ' and \\ backslash", "t": t})))
    return keep, other


def _dump(dsn, bid):
    with psycopg.connect(dsn) as c:
        runs = c.execute("SELECT run_id, agent_id, status, cost, grader_result FROM runs WHERE benchmark_id=%s",
                         (bid,)).fetchall()
        events = c.execute("SELECT e.type, e.payload FROM events e JOIN runs r USING (run_id)"
                           " WHERE r.benchmark_id=%s ORDER BY e.id", (bid,)).fetchall()
        agents = c.execute("SELECT agent_id FROM agents ORDER BY 1").fetchall()
    return runs, events, agents


def test_export_load_roundtrip(two_dbs, tmp_path):
    src, dst = two_dbs
    keep, other = _seed(src)
    out = tmp_path / "demo.sql"
    counts = demo.export(src, [keep], out)
    assert counts == {"benchmarks": 1, "runs": 1, "events": 3, "agents": 1, "tasks": 1}
    assert other not in out.read_text(encoding="utf8")            # only the chosen benchmark
    demo.load(dst, out)
    s_runs, s_events, _ = _dump(src, keep)
    d_runs, d_events, d_agents = _dump(dst, keep)
    assert s_runs == d_runs and s_events == d_events              # values, JSON and quoting survive
    assert d_agents == [("a",)]                                   # unreferenced agents not exported
    with pytest.raises(psycopg.errors.UniqueViolation):
        demo.load(dst, out)                                       # second load refused, all-or-nothing
    assert _dump(dst, keep)[1] == s_events


def test_export_refuses_unknown_or_unfinished(two_dbs, tmp_path):
    src, _ = two_dbs
    keep, _ = _seed(src)
    with pytest.raises(SystemExit, match="unknown"):
        demo.export(src, [str(uuid.uuid4())], tmp_path / "x.sql")
    with psycopg.connect(src, autocommit=True) as c:
        c.execute("UPDATE benchmarks SET state='running' WHERE benchmark_id=%s", (keep,))
    with pytest.raises(SystemExit, match="not finished"):
        demo.export(src, [keep], tmp_path / "x.sql")
