"""Orchestrator (B5/B6, F-06) and seed loader (A-1). T-13 / T-14.

Pure tests: aggregation and classification. DB tests: each one runs on its own throwaway
database (migrated with db/migrate.py), so nothing touches the dev database. A fake runner
writes llm_call events the way the proxy would, and a fake grader decides pass/fail.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb

from db import migrate
from orchestrator import seed
from orchestrator.core import Config, Metrics, Orchestrator, aggregate, classify
from orchestrator.types import GradeResult, RunResult, SuiteResult

ROOT = Path(__file__).resolve().parents[2]
DSN = os.environ.get("DATABASE_URL", "")


# ---- aggregation (docs/07 section 4) ------------------------------------------------------------
def ev(i, type_="llm_call", error=None, **payload):
    return {"id": i, "type": type_, "payload": payload, "error": error}


def test_aggregate_counts_and_sums():
    m = aggregate([
        ev(1, "agent_started"),
        ev(2, status_code=503, error="injected", cost=0.0, cost_confidence="verified"),
        ev(3, status_code=200, model="m1", tokens_in=10, tokens_out=5, cost=0.001, cost_confidence="verified"),
        ev(4, "tool_call"), ev(5, "tool_call"),
        ev(6, status_code=200, model="m2", tokens_in=20, tokens_out=7, cost=0.002, cost_confidence="estimated"),
    ])
    assert (m.steps, m.tool_calls, m.model) == (2, 2, "m1")
    assert (m.tokens_in, m.tokens_out, m.cost, m.cost_confidence) == (30, 12, 0.003, "estimated")
    assert m.upstream_unrecovered is False


def test_aggregate_without_llm_calls_is_null():
    m = aggregate([ev(1, "agent_started")])
    assert (m.steps, m.tokens_in, m.cost, m.cost_confidence, m.model) == (0, None, None, None, None)


@pytest.mark.parametrize("events, unrecovered", [
    ([ev(1, status_code=502, error="upstream")], True),
    ([ev(1, status_code=502, error="upstream"), ev(2, status_code=200)], False),     # recovered
    ([ev(1, status_code=200), ev(2, status_code=503, error="upstream")], True),      # failed last
    ([ev(1, status_code=503, error="injected")], False),                             # injected never counts
])
def test_upstream_rule(events, unrecovered):
    assert aggregate(events).upstream_unrecovered is unrecovered


# ---- classification (F-06 step 5, D-03) ---------------------------------------------------------
OK_RUN = RunResult(exit_code=0, timed_out=False, workspace_dir="/w", diff="+x")
PASS_GRADE = GradeResult(passed=True, tamper_detected=False)
FAIL_GRADE = GradeResult(passed=False, tamper_detected=False, summary="2 tests failed")


@pytest.mark.parametrize("result, grade, grade_error, metrics, status, msg", [
    ({"sandbox_error": "spawn failed"}, None, None, Metrics(), "INFRA_ERROR", "runner: spawn failed"),
    (OK_RUN, None, "pytest missing", Metrics(), "INFRA_ERROR", "grader: pytest missing"),
    (OK_RUN, PASS_GRADE, None, Metrics(upstream_unrecovered=True), "INFRA_ERROR", "upstream"),
    (RunResult(None, True, "/w"), PASS_GRADE, None, Metrics(), "FAIL", "timed out"),
    (OK_RUN, GradeResult(passed=True, tamper_detected=True), None, Metrics(), "FAIL", "tamper"),
    (RunResult(1, False, "/w", diff=""), PASS_GRADE, None, Metrics(), "FAIL", "without changing"),
    (RunResult(1, False, "/w", diff="+x"), PASS_GRADE, None, Metrics(), "PASS", None),
    (OK_RUN, FAIL_GRADE, None, Metrics(), "FAIL", "2 tests failed"),
    # GradeResult.error = agent-caused test problem (exec-core grader): FAIL, not INFRA
    (OK_RUN, {"passed": False, "tamper_detected": False, "summary": "visible failed",
              "error": "hidden suite collected no tests"}, None, Metrics(), "FAIL", "collected no tests"),
    (OK_RUN, PASS_GRADE, None, Metrics(), "PASS", None),
    ({"exit_code": 0, "timed_out": False, "workspace_dir": "/w", "diff": "+x"},
     {"passed": True, "tamper_detected": False}, None, Metrics(), "PASS", None),   # plain dicts work
])
def test_classify(result, grade, grade_error, metrics, status, msg):
    out = classify(result, grade, grade_error, metrics)
    assert out.status == status
    assert (out.error is None) if msg is None else (msg in out.error)


# ---- seed loader (no DB needed for reading) -----------------------------------------------------
def make_task(root: Path, task_id: str, faults=(), folder=None):
    d = root / (folder or task_id)
    (d / "workspace").mkdir(parents=True)
    (d / "workspace" / "app.py").write_text("x = 1\n", encoding="utf8")
    (d / "task.yaml").write_text(f"task_id: {task_id}\ncategory: coding\nfaults_allowed: {list(faults)}\n",
                                 encoding="utf8")
    (d / "prompt.md").write_text(f"Fix {task_id}.\n", encoding="utf8")
    (d / "grader.yaml").write_text("type: pytest\nconfig: {timeout_s: 60}\n", encoding="utf8")
    return d


def make_agent(root: Path, name: str):
    d = root / name
    d.mkdir(parents=True)
    (d / "agent.yaml").write_text(f"name: {name}\nmode: command\nentrypoint: python agent.py\n"
                                  "model_config: { model: mock-model }\ndescription: test agent\n", encoding="utf8")
    return d


def test_seed_reads_repo_agents():
    agents = seed.read_agents(ROOT / "agents")
    assert {"agent-a-plain", "agent-b-openai-agents", "agent-c-test-retry"} <= {a["agent_id"] for a in agents}
    assert all(a["source_path"].startswith("agents/") for a in agents)


def test_seed_requires_validator_or_trust(tmp_path, monkeypatch):
    monkeypatch.setattr(seed, "_validator", lambda: None)       # as before grader/validate.py existed
    make_task(tmp_path, "t1")
    with pytest.raises(RuntimeError, match="--trust"):
        seed.read_tasks(tmp_path)
    rows, rejected = seed.read_tasks(tmp_path, trust=True)
    assert [r["task_id"] for r in rows] == ["t1"] and rows[0]["grader"]["type"] == "pytest"
    assert rows[0]["prompt"] == "Fix t1.\n" and len(rows[0]["task_hash"]) == 64 and rejected == []


def test_seed_rejects_folder_name_mismatch_and_uses_validator(tmp_path, monkeypatch):
    make_task(tmp_path, "good")
    make_task(tmp_path, "bad", folder="bad")
    make_task(tmp_path, "other-id", folder="mismatch")
    monkeypatch.setattr(seed, "_validator", lambda: lambda d: {
        "ok": not d.endswith("bad"), "checks": [{"name": "broken_state_fails", "ok": False}]})
    rows, rejected = seed.read_tasks(tmp_path)
    assert [r["task_id"] for r in rows] == ["good"]
    assert any("broken_state_fails" in r for r in rejected) and any("folder name" in r for r in rejected)


def test_task_hash_changes_with_content(tmp_path):
    d = make_task(tmp_path, "t1")
    h1 = seed.dir_hash(d)
    (d / "workspace" / "app.py").write_text("x = 2\n", encoding="utf8")
    assert seed.dir_hash(d) != h1


# ---- orchestrator on a throwaway DB -------------------------------------------------------------
def _server_ok() -> bool:
    try:
        with psycopg.connect(DSN, connect_timeout=2) as c:
            c.execute("SELECT 1")
        return True
    except psycopg.Error:
        return False


needs_db = pytest.mark.skipif(not _server_ok(), reason="no Postgres at DATABASE_URL / PG* env")


@pytest.fixture
def db():
    name = f"arena_orch_test_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute(f'CREATE DATABASE "{name}"')
    dsn = make_conninfo(DSN, dbname=name)
    migrate.migrate(dsn, log=lambda *_: None)
    try:
        yield dsn
    finally:
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture
def world(db, tmp_path, monkeypatch):
    """Agents a1/a2/a3, tasks t1/t2 (t1 allows both test faults), faults dir, loaded via seed.load.
    The fake tasks have no tests, so the real validator is switched off for them."""
    monkeypatch.setattr(seed, "_validator", lambda: None)
    agents_dir, tasks_dir, faults = tmp_path / "agents", tmp_path / "tasks", tmp_path / "faults"
    for a in ("a1", "a2", "a3"):
        make_agent(agents_dir, a)
    make_task(tasks_dir, "t1", faults=("provider_503_outage", "tool_run_tests_error"))
    make_task(tasks_dir, "t2")
    faults.mkdir()
    (faults / "provider_503_outage.yaml").write_text(
        "id: provider_503_outage\ngroup: provider\nlayer: proxy\ndescription: d\n"
        "params: { first_n: 3, status: 503 }\n", encoding="utf8")
    (faults / "tool_run_tests_error.yaml").write_text(
        "id: tool_run_tests_error\ngroup: tool\nlayer: agent_env\ndescription: d\n"
        "params: { tool: run_tests, fail_first_n: 2 }\n", encoding="utf8")
    rows, _ = seed.read_tasks(tasks_dir, trust=True)
    with psycopg.connect(db, autocommit=True) as c:
        seed.load(c, seed.read_agents(agents_dir), rows)
    return {"dsn": db, "root": tmp_path, "faults": faults}


class Fake:
    """Fake runner + grader. `behaviour[agent_id]` decides what a run does; the runner writes
    llm_call / tool_call events directly, as the proxy would."""

    def __init__(self, dsn, behaviour):
        self.dsn, self.behaviour, self.specs, self.workspaces = dsn, behaviour, [], []

    def run_agent(self, spec):
        self.specs.append(spec)
        agent = Path(spec.agent["source_path"]).name
        b = self.behaviour.get(agent, {})
        attempt_fail = b.get("sandbox_error_attempts", 0)
        with psycopg.connect(self.dsn, autocommit=True) as c:
            attempt = c.execute("SELECT attempt FROM runs WHERE run_id = %s", (spec.run_id,)).fetchone()[0]
            if attempt <= attempt_fail:
                return RunResult(None, False, "", sandbox_error="container did not start")
            if b.get("raise"):
                raise RuntimeError("runner exploded")
            for i, (status, err) in enumerate(b.get("calls", [(200, None)])):
                c.execute("INSERT INTO events (run_id, type, payload, latency, error) VALUES (%s,'llm_call',%s,5,%s)",
                          (spec.run_id, Jsonb({"status_code": status, "model": "mock-model",
                                               "tokens_in": 100 if status == 200 else None,
                                               "tokens_out": 10 if status == 200 else None,
                                               "cost": b.get("cost", 0.001) if status == 200 else 0.0,
                                               "cost_confidence": "verified"}), err))
            for _ in range(b.get("tools", 1)):
                c.execute("INSERT INTO events (run_id, type, payload) VALUES (%s,'tool_call','{}')", (spec.run_id,))
        ws = tempfile.mkdtemp(prefix="orch-test-")
        self.workspaces.append(ws)
        return RunResult(0, False, ws, diff="+fix", started_at="2026-11-15T10:00:00+00:00",
                         finished_at="2026-11-15T10:00:04.5+00:00")

    def grade(self, task_dir, workspace_dir):
        b = next((v for k, v in self.behaviour.items() if v.get("grade_raise")), None)
        if b and Path(task_dir).name == b.get("grade_raise"):
            raise RuntimeError("grader exploded")
        return GradeResult(passed=Path(task_dir).name == "t1", tamper_detected=False,
                           suites=[SuiteResult("visible", True, 3, 0), SuiteResult("hidden", True, 2, 0)])


def orch(world, fake, parallel=2, cleanup=None):
    return Orchestrator(Config(dsn=world["dsn"], proxy_base_url="http://proxy.test:8001", parallel=parallel,
                               settle_s=0, faults_dir=world["faults"], pricing_file=ROOT / "pricing.yaml",
                               root=world["root"]), fake.run_agent, fake.grade, cleanup)


def launch(dsn, **cfg):
    base = {"name": "b", "agent_ids": ["a1"], "task_ids": ["t1"], "scenarios": ["baseline"], "n_runs": 1,
            "spend_cap_usd": 5.0}
    base.update(cfg)
    with psycopg.connect(dsn, autocommit=True) as c:
        return str(c.execute("INSERT INTO benchmarks (name, config) VALUES (%s, %s) RETURNING benchmark_id",
                             (base["name"], Jsonb(base))).fetchone()[0])


def q(dsn, sql, *args):
    with psycopg.connect(dsn) as c:
        return c.execute(sql, args).fetchall()


@needs_db
def test_full_matrix_completes_with_metrics_and_events(world):
    fake = Fake(world["dsn"], {"a1": {"calls": [(200, None), (200, None)], "tools": 3}, "a2": {}})
    bid = launch(world["dsn"], agent_ids=["a1", "a2"], task_ids=["t1", "t2"],
                 scenarios=["baseline", "provider_503_outage"], n_runs=2)
    assert orch(world, fake).run_once() == 1
    assert q(world["dsn"], "SELECT state, error FROM benchmarks WHERE benchmark_id=%s", bid) == [("completed", None)]
    runs = q(world["dsn"], "SELECT agent_id, task_id, status, passed, steps, tool_calls, tokens_in, cost,"
             " cost_confidence, duration, state FROM runs WHERE benchmark_id=%s", bid)
    assert len(runs) == 16 and {r[10] for r in runs} == {"done"}
    by = {(r[0], r[1]): r for r in runs}
    status, passed, steps, tools, tin, cost, conf, duration = by[("a1", "t1")][2:10]
    assert (status, passed, steps, tools, tin, conf) == ("PASS", True, 2, 3, 200, "verified")
    assert (float(cost), float(duration)) == (0.002, 4.5)      # numeric columns come back as Decimal
    assert by[("a2", "t2")][2:4] == ("FAIL", False)              # fake grader fails t2
    rid = q(world["dsn"], "SELECT run_id FROM runs WHERE benchmark_id=%s LIMIT 1", bid)[0][0]
    types = [t for (t,) in q(world["dsn"], "SELECT type FROM events WHERE run_id=%s ORDER BY id", rid)]
    assert types[0] == "agent_started" and types[-1] == "grader_result"
    detail = q(world["dsn"], "SELECT env_fingerprint, grader_result, workspace_diff FROM runs WHERE run_id=%s", rid)[0]
    assert detail[0]["model"] == "mock-model" and len(detail[0]["task_hash"]) == 64
    assert len(detail[1]["suites"]) == 2 and detail[2] == "+fix"
    assert all(not Path(w).exists() for w in fake.workspaces)    # orchestrator released workspaces
    assert fake.specs[0].proxy_base_url == "http://proxy.test:8001"
    assert Path(fake.specs[0].task_dir).name in ("t1", "t2") and Path(fake.specs[0].task_dir).is_absolute()


@needs_db
def test_infra_error_retried_then_excluded(world):
    fake = Fake(world["dsn"], {"a1": {"sandbox_error_attempts": 99}, "a2": {"sandbox_error_attempts": 1}})
    bid = launch(world["dsn"], agent_ids=["a1", "a2"])
    orch(world, fake).run_once()
    rows = q(world["dsn"], "SELECT agent_id, attempt, status, passed, error FROM runs WHERE benchmark_id=%s"
             " ORDER BY agent_id, attempt", bid)
    assert [(a, n, s) for a, n, s, _, _ in rows] == [
        ("a1", 1, "INFRA_ERROR"), ("a1", 2, "INFRA_ERROR"), ("a1", 3, "INFRA_ERROR"),   # then excluded
        ("a2", 1, "INFRA_ERROR"), ("a2", 2, "PASS")]                                    # recovered
    assert rows[0][3] is None and "container did not start" in rows[0][4]
    assert q(world["dsn"], "SELECT state FROM benchmarks WHERE benchmark_id=%s", bid) == [("completed",)]


@needs_db
def test_upstream_vs_injected_classification(world):
    fake = Fake(world["dsn"], {
        "a1": {"calls": [(503, "injected"), (503, "injected"), (200, None)]},   # fault then recovery
        "a2": {"calls": [(200, None), (502, "upstream")]},                      # real outage, never recovered
    })
    bid = launch(world["dsn"], agent_ids=["a1", "a2"])
    orch(world, fake).run_once()
    rows = dict(q(world["dsn"], "SELECT agent_id, status FROM runs WHERE benchmark_id=%s AND attempt=1", bid))
    assert rows == {"a1": "PASS", "a2": "INFRA_ERROR"}


@needs_db
def test_spend_cap_halts_scheduling(world):
    fake = Fake(world["dsn"], {"a1": {"cost": 0.01}})
    bid = launch(world["dsn"], n_runs=6, spend_cap_usd=0.025)
    orch(world, fake, parallel=1).run_once()
    assert q(world["dsn"], "SELECT state FROM benchmarks WHERE benchmark_id=%s", bid) == [("halted_spend_cap",)]
    counts = dict(q(world["dsn"], "SELECT state, count(*) FROM runs WHERE benchmark_id=%s GROUP BY state", bid))
    assert counts == {"done": 3, "queued": 3}                       # 0.01 x 3 >= 0.025, then stop


@needs_db
def test_restart_recovers_interrupted_run(world):
    fake = Fake(world["dsn"], {"a1": {}})
    bid = launch(world["dsn"], n_runs=2)
    with psycopg.connect(world["dsn"], autocommit=True) as c:      # simulate a crash mid-benchmark
        c.execute("UPDATE benchmarks SET state='running', started_at=now() WHERE benchmark_id=%s", (bid,))
        c.execute("INSERT INTO runs (benchmark_id, agent_id, task_id, repeat_index, state, started_at)"
                  " VALUES (%s,'a1','t1',1,'running',now())", (bid,))
    orch(world, fake).run_once()
    rows = q(world["dsn"], "SELECT repeat_index, attempt, status, error FROM runs WHERE benchmark_id=%s"
             " ORDER BY repeat_index, attempt", bid)
    assert [(r, a, s) for r, a, s, _ in rows] == [(1, 1, "INFRA_ERROR"), (1, 2, "PASS"), (2, 1, "PASS")]
    assert "orchestrator restarted" in rows[0][3]
    assert q(world["dsn"], "SELECT state FROM benchmarks WHERE benchmark_id=%s", bid) == [("completed",)]


@needs_db
def test_completed_slots_are_not_rerun(world):
    fake = Fake(world["dsn"], {"a1": {}})
    bid = launch(world["dsn"], n_runs=2)
    o = orch(world, fake)
    o.run_once()
    with psycopg.connect(world["dsn"], autocommit=True) as c:      # re-open the same benchmark
        c.execute("UPDATE benchmarks SET state='running' WHERE benchmark_id=%s", (bid,))
    o.run_once()
    assert len(fake.specs) == 2


@needs_db
def test_unknown_ids_fail_the_benchmark(world):
    bid = launch(world["dsn"], agent_ids=["a1", "ghost"])
    orch(world, Fake(world["dsn"], {})).run_once()
    state, error = q(world["dsn"], "SELECT state, error FROM benchmarks WHERE benchmark_id=%s", bid)[0]
    assert state == "failed" and "ghost" in error


@needs_db
def test_runner_and_grader_crashes_are_infra(world):
    fake = Fake(world["dsn"], {"a1": {"raise": True}, "a2": {"grade_raise": "t2"}})
    bid = launch(world["dsn"], agent_ids=["a1", "a2"], task_ids=["t2"])
    orch(world, fake).run_once()
    rows = {a: e for a, e in q(world["dsn"], "SELECT agent_id, error FROM runs WHERE benchmark_id=%s"
                                              " AND attempt=1", bid)}
    assert "runner exploded" in rows["a1"] and "grader exploded" in rows["a2"]
    assert {s for (s,) in q(world["dsn"], "SELECT DISTINCT status FROM runs WHERE benchmark_id=%s", bid)} \
        == {"INFRA_ERROR"}


@needs_db
def test_agent_env_fault_passed_to_runner_and_logged(world):
    fake = Fake(world["dsn"], {"a1": {}})
    bid = launch(world["dsn"], scenarios=["tool_run_tests_error", "provider_503_outage"])
    orch(world, fake).run_once()
    faults = {s.fault["id"] if s.fault else None for s in fake.specs}
    assert faults == {"tool_run_tests_error", None}                 # proxy fault is the proxy's job
    rows = q(world["dsn"], "SELECT r.scenario, e.payload FROM events e JOIN runs r USING (run_id)"
             " WHERE r.benchmark_id=%s AND e.type='fault_injected'", bid)
    assert [(s, p["fault_id"], p["group"]) for s, p in rows] == [
        ("tool_run_tests_error", "tool_run_tests_error", "tool")]


@needs_db
def test_runner_cleanup_is_used_when_given(world):
    fake, released = Fake(world["dsn"], {"a1": {}}), []
    launch(world["dsn"], n_runs=2)
    orch(world, fake, cleanup=lambda result: released.append(result.workspace_dir)).run_once()
    assert sorted(released) == sorted(fake.workspaces)
    assert all(Path(w).exists() for w in fake.workspaces)   # our own rmtree was not used
