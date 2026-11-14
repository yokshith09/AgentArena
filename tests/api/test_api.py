"""T-16: dashboard API vs docs/08 section 3 models, mock payloads, error envelope and launch
rules. Needs Postgres with the 001 schema at DATABASE_URL / PG* env (skipped otherwise).
Seeds its own `t16-*` rows and removes them afterwards."""
from __future__ import annotations

import os
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from api import stats
from api.app import Settings, create_app
from api.models import Benchmark, Event, ResilienceRow, Results, RunDetail

DSN = os.environ.get("DATABASE_URL", "")


def _db_available() -> bool:
    try:
        with psycopg.connect(DSN, connect_timeout=2) as c:
            c.execute("SELECT 1 FROM runs LIMIT 1")
        return True
    except psycopg.Error:
        return False


needs_db = pytest.mark.skipif(not _db_available(), reason="no migrated Postgres at DATABASE_URL / PG* env")
FAULT = "provider_503_outage"
BID = str(uuid.uuid4())
EMPTY_BID = str(uuid.uuid4())


@pytest.fixture(scope="module")
def faults_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("faults")
    (d / f"{FAULT}.yaml").write_text(
        f"id: {FAULT}\ngroup: provider\nlayer: proxy\ndescription: First 3 requests get 503\n"
        "params: {first_n: 3, status: 503}\n", encoding="utf8")
    return str(d)


def _run(c, agent, task, scenario, repeat, status, *, attempt=1, cost=None, steps=None,
         tool_calls=None, duration=None, conf="verified", state="done"):
    passed = None if status in (None, "INFRA_ERROR") else status == "PASS"
    return c.execute(
        "INSERT INTO runs (benchmark_id, agent_id, task_id, scenario, repeat_index, attempt, state,"
        " status, passed, cost, cost_confidence, steps, tool_calls, duration, started_at)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now()) RETURNING run_id",
        (BID, agent, task, scenario, repeat, attempt, state, status, passed, cost,
         conf if status in ("PASS", "FAIL") else None, steps, tool_calls, duration)).fetchone()[0]


@pytest.fixture(scope="module")
def seeded():
    """FABRICATED TEST DATA. Benchmark: agents t16-a1, t16-a2 x tasks t16-t1, t16-t2 x
    {baseline, provider_503_outage} x n_runs 3."""
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute("INSERT INTO agents (agent_id, name, mode, entrypoint, model_config, description,"
                  " source_path) VALUES ('t16-a1','Agent One','command','python a.py','{\"model\":\"m\"}',"
                  " 'first', 'agents/a1'), ('t16-a2','Agent Two','http','http://x','{}', NULL, 'agents/a2')")
        c.execute("INSERT INTO tasks (task_id, category, prompt, workspace, grader, reference_solution,"
                  " faults_allowed, task_dir, task_hash, validated) VALUES"
                  " ('t16-t1','coding','fix it','workspace','{\"type\":\"pytest\"}','ref',%s,'d','h',true),"
                  " ('t16-t2','research','find it','workspace','{\"type\":\"answer_match\"}','ref','{}','d','h',true),"
                  " ('t16-t3','coding','draft','workspace','{\"type\":\"pytest\"}','ref','{}','d','h',false)",
                  ([FAULT],))
        cfg = ('{"name":"t16","agent_ids":["t16-a1","t16-a2"],"task_ids":["t16-t1","t16-t2"],'
               f'"scenarios":["baseline","{FAULT}"],"n_runs":3,"spend_cap_usd":5}}')
        c.execute("INSERT INTO benchmarks (benchmark_id, name, config, state) VALUES (%s,'t16',%s,'running'),"
                  " (%s,'t16-empty','{}','queued')", (BID, cfg, EMPTY_BID))
        ids = {}
        # a1 baseline on t1: PASS, PASS, FAIL (+ an INFRA attempt 1 before the FAIL's attempt 2)
        ids["pass"] = _run(c, "t16-a1", "t16-t1", "baseline", 1, "PASS", cost=0.01, steps=4, tool_calls=5, duration=10)
        _run(c, "t16-a1", "t16-t1", "baseline", 2, "PASS", cost=0.03, steps=6, tool_calls=7, duration=20,
             conf="estimated")
        _run(c, "t16-a1", "t16-t1", "baseline", 3, "INFRA_ERROR", cost=0.002)
        _run(c, "t16-a1", "t16-t1", "baseline", 3, "FAIL", attempt=2, cost=0.02, steps=5, tool_calls=6, duration=30)
        # a1 baseline on t2: PASS; one slot still running, one queued row
        _run(c, "t16-a1", "t16-t2", "baseline", 1, "PASS", cost=0.04, steps=8, tool_calls=2, duration=40)
        _run(c, "t16-a1", "t16-t2", "baseline", 2, None, state="running")
        _run(c, "t16-a1", "t16-t2", "baseline", 3, None, state="queued")
        # a1 under fault on t1: PASS, FAIL
        _run(c, "t16-a1", "t16-t1", FAULT, 1, "PASS", cost=0.05, steps=9, tool_calls=3, duration=50)
        _run(c, "t16-a1", "t16-t1", FAULT, 2, "FAIL", cost=0.06, steps=9, tool_calls=3, duration=60)
        # a2 baseline on t1: FAIL; and a slot that failed all 3 attempts (excluded)
        _run(c, "t16-a2", "t16-t1", "baseline", 1, "FAIL", cost=0.01, steps=2, tool_calls=1, duration=5)
        for attempt in (1, 2, 3):
            _run(c, "t16-a2", "t16-t1", "baseline", 2, "INFRA_ERROR", attempt=attempt)
        # a2 under fault: FAIL (baseline pass rate 0 -> resilience null)
        _run(c, "t16-a2", "t16-t1", FAULT, 1, "FAIL", cost=0.01, steps=2, tool_calls=1, duration=5)
        c.execute("INSERT INTO events (run_id, type, payload, latency, error) VALUES"
                  " (%s,'llm_call','{\"endpoint\":\"/chat/completions\",\"status_code\":200}',12,NULL),"
                  " (%s,'tool_call','{\"name\":\"run_tests\",\"call_id\":\"c1\"}',NULL,NULL)",
                  (ids["pass"], ids["pass"]))
        yield ids
        c.execute("DELETE FROM runs WHERE agent_id LIKE 't16-%'")
        c.execute("DELETE FROM benchmarks WHERE name LIKE 't16%'")
        c.execute("DELETE FROM tasks WHERE task_id LIKE 't16-%'")
        c.execute("DELETE FROM agents WHERE agent_id LIKE 't16-%'")


@pytest.fixture(scope="module")
def client(faults_dir, seeded):
    with TestClient(create_app(Settings(database_url=DSN, faults_dir=faults_dir)),
                    raise_server_exceptions=False) as c:
        yield c


def assert_error(r, status, code):
    assert r.status_code == status, r.text
    body = r.json()
    assert set(body) == {"error"} and set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == code
    return body["error"]


# ---- canonical mock payloads (docs/08 section 4) validate against the live models ------------
MOCK_RESULT = {"agent_id": "agent-a-plain", "task_id": None, "scenario": "baseline", "runs_counted": 15,
               "infra_excluded": 1,
               "pass_rate": {"passed": 11, "n": 15, "value": 0.733, "ci_low": 0.48, "ci_high": 0.89},
               "cost": {"n": 15, "mean": 0.021, "median": 0.019, "std": 0.008, "ci_low": 0.017, "ci_high": 0.025},
               "steps": {"n": 15, "mean": 7.2, "median": 7, "std": 2.1, "ci_low": 6.1, "ci_high": 8.3},
               "tool_calls": {"n": 15, "mean": 9.0, "median": 8, "std": 3.0, "ci_low": 7.5, "ci_high": 10.6},
               "duration": {"n": 15, "mean": 41.0, "median": 38.0, "std": 12.0, "ci_low": 35.0, "ci_high": 47.5},
               "cost_confidence": {"verified": 15, "estimated": 0}}
MOCK_RUN = {"run_id": "22222222-2222-4222-8222-222222222222", "benchmark_id": "11111111-1111-4111-8111-111111111111",
            "agent_id": "agent-a-plain", "task_id": "fix-off-by-one", "scenario": "provider_503_outage",
            "repeat_index": 1, "attempt": 1, "state": "done", "status": "PASS", "passed": True,
            "model": "mock-model", "tokens_in": 1200, "tokens_out": 300, "cost": 0.0042, "cost_confidence": "verified",
            "duration": 37.5, "steps": 6, "tool_calls": 8, "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:00:40Z", "error": None,
            "env_fingerprint": {"model": "mock-model", "date": "2026-01-01", "task_hash": "abc"},
            "grader_result": {"passed": True, "tamper_detected": False, "suites": [], "summary": "mock"},
            "workspace_diff": "--- a/x.py\n+++ b/x.py\n@@ ...\n"}
MOCK_EVENT = {"id": 2, "run_id": "2222", "ts": "2026-01-01T00:00:01Z", "type": "llm_call", "agent_role": None,
              "payload": {"endpoint": "/chat/completions", "status_code": 503}, "latency": 4, "error": "injected"}
MOCK_RESILIENCE = {"agent_id": "agent-a-plain", "scenario": "provider_503_outage",
                   "baseline_pass_rate": {"passed": 11, "n": 15, "value": 0.733, "ci_low": 0.48, "ci_high": 0.89},
                   "scenario_pass_rate": {"passed": 4, "n": 15, "value": 0.267, "ci_low": 0.11, "ci_high": 0.52},
                   "resilience_score": 0.364}


def test_doc08_mock_payloads_validate_against_models():
    Results.model_validate({"benchmark_id": "11111111-1111-4111-8111-111111111111",
                            "generated_at": "2026-01-01T00:00:00Z", "items": [MOCK_RESULT]})
    RunDetail.model_validate(MOCK_RUN)
    Event.model_validate(MOCK_EVENT)
    ResilienceRow.model_validate(MOCK_RESILIENCE)


# ---- 3.1 catalog & health --------------------------------------------------------------------
@needs_db
def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "db": "ok"}


def test_health_reports_db_down(faults_dir):
    with TestClient(create_app(Settings(database_url="host=127.0.0.1 port=1 connect_timeout=1",
                                        faults_dir=faults_dir))) as c:
        assert c.get("/api/health").json() == {"status": "ok", "db": "down"}


@needs_db
def test_agents_list_and_get(client):
    page = client.get("/api/agents", params={"limit": 200}).json()
    ours = [a for a in page["items"] if a["agent_id"].startswith("t16-")]
    assert ours == [
        {"agent_id": "t16-a1", "name": "Agent One", "mode": "command", "entrypoint": "python a.py",
         "model_config": {"model": "m"}, "description": "first"},
        {"agent_id": "t16-a2", "name": "Agent Two", "mode": "http", "entrypoint": "http://x",
         "model_config": {}, "description": None}]
    assert page["total"] >= 2
    assert client.get("/api/agents/t16-a1").json()["name"] == "Agent One"
    assert_error(client.get("/api/agents/nope"), 404, "NOT_FOUND")


@needs_db
def test_tasks_with_category_filter(client):
    items = client.get("/api/tasks", params={"category": "research", "limit": 200}).json()["items"]
    t2 = next(t for t in items if t["task_id"] == "t16-t2")
    assert t2 == {"task_id": "t16-t2", "category": "research", "prompt": "find it",
                  "grader_type": "answer_match", "faults_allowed": [], "validated": True, "weak": None}
    assert all(t["category"] == "research" for t in items)


@needs_db
def test_scenarios_always_include_baseline(client):
    body = client.get("/api/scenarios").json()
    assert [s["id"] for s in body["items"]] == ["baseline", FAULT] and body["total"] == 2
    assert body["items"][0] == {"id": "baseline", "group": "baseline", "layer": "none",
                                "description": "No fault injected"}


# ---- pagination & error envelope -------------------------------------------------------------
@needs_db
@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 201}, {"offset": -1}])
def test_pagination_bounds(client, params):
    err = assert_error(client.get("/api/agents", params=params), 422, "VALIDATION_ERROR")
    assert err["details"]["fields"]


@needs_db
def test_unknown_route_uses_envelope(client):
    assert_error(client.get("/api/nope"), 404, "NOT_FOUND")


# ---- 3.2 benchmarks --------------------------------------------------------------------------
@needs_db
def test_benchmark_progress_and_spend(client):
    b = Benchmark.model_validate(client.get(f"/api/benchmarks/{BID}").json())
    # 2 agents x 2 tasks x 2 scenarios x 3 runs = 24 slots. Latest attempt per existing slot:
    # done: a1/t1/base r1,r2,r3(attempt 2) + a1/t2/base r1 + a1/t1/fault r1,r2 + a2/t1/base r1
    #       + a2/t1/fault r1 = 8; running 1; excluded 1 (a2/t1/base r2, attempt 3); queued = rest.
    assert b.progress.model_dump() == {"total": 24, "queued": 14, "running": 1, "done": 8,
                                       "infra_error": 0, "excluded": 1}
    assert b.spend_usd == pytest.approx(0.01 + 0.03 + 0.002 + 0.02 + 0.04 + 0.05 + 0.06 + 0.01 + 0.01)
    assert b.state == "running" and b.config["n_runs"] == 3


@needs_db
def test_benchmark_list_newest_first_and_404(client):
    items = client.get("/api/benchmarks", params={"limit": 200}).json()["items"]
    created = [b["created_at"] for b in items]
    assert created == sorted(created, reverse=True)
    assert_error(client.get(f"/api/benchmarks/{uuid.uuid4()}"), 404, "NOT_FOUND")
    assert_error(client.get("/api/benchmarks/not-a-uuid"), 404, "NOT_FOUND")


def launch(**over):
    cfg = {"name": "t16-launch", "agent_ids": ["t16-a1"], "task_ids": ["t16-t1"],
           "scenarios": ["baseline", FAULT], "n_runs": 2, "spend_cap_usd": 1.5}
    cfg.update(over)
    return {k: v for k, v in cfg.items() if v is not None}


@needs_db
def test_launch_creates_queued_benchmark(client):
    r = client.post("/api/benchmarks", json=launch())
    assert r.status_code == 202, r.text
    b = Benchmark.model_validate(r.json())
    assert b.state == "queued" and b.spend_usd == 0 and b.progress.total == 4 and b.progress.queued == 4
    assert b.config["scenarios"] == ["baseline", FAULT]
    assert client.get(f"/api/benchmarks/{b.benchmark_id}").status_code == 200


@needs_db
def test_launch_scenarios_default_to_baseline(client):
    cfg = launch()
    del cfg["scenarios"]
    r = client.post("/api/benchmarks", json=cfg)
    assert r.status_code == 202 and r.json()["config"]["scenarios"] == ["baseline"]


@needs_db
@pytest.mark.parametrize("over, field", [
    ({"agent_ids": ["t16-a1", "ghost"]}, "agent_ids"),
    ({"task_ids": ["t16-t1", "ghost"]}, "task_ids"),
    ({"task_ids": ["t16-t3"]}, "task_ids"),                       # not validated
    ({"scenarios": ["baseline", "made_up"]}, "scenarios"),
    ({"task_ids": ["t16-t1", "t16-t2"]}, "scenarios"),            # fault not allowed for t2
    ({"n_runs": 0}, "n_runs"),
    ({"n_runs": 11}, "n_runs"),
    ({"spend_cap_usd": 0}, "spend_cap_usd"),
    ({"name": ""}, "name"),
    ({"name": "x" * 81}, "name"),
    ({"models": ["m"]}, "models"),                                # P2 field rejected in P0
])
def test_launch_validation_rules(client, over, field):
    err = assert_error(client.post("/api/benchmarks", json=launch(**over)), 422, "VALIDATION_ERROR")
    assert field in err["details"]["fields"], err


# ---- 3.4 runs & events -----------------------------------------------------------------------
@needs_db
def test_runs_filters(client):
    page = client.get("/api/runs", params={"benchmark_id": BID, "limit": 200}).json()
    assert page["total"] == 14  # 4 + 3 + 2 (a1) + 4 + 1 (a2) seeded rows
    for p, n in [({"status": "INFRA_ERROR"}, 4), ({"state": "running"}, 1), ({"agent_id": "t16-a2"}, 5),
                 ({"scenario": FAULT}, 3), ({"task_id": "t16-t2"}, 3)]:
        assert client.get("/api/runs", params={"benchmark_id": BID, **p}).json()["total"] == n, p
    assert_error(client.get("/api/runs", params={"status": "MAYBE"}), 422, "VALIDATION_ERROR")
    assert_error(client.get("/api/runs", params={"benchmark_id": "x"}), 422, "VALIDATION_ERROR")


@needs_db
def test_run_detail_and_events(client, seeded):
    rid = str(seeded["pass"])
    d = RunDetail.model_validate(client.get(f"/api/runs/{rid}").json())
    assert (d.status, d.cost, d.steps, d.env_fingerprint, d.grader_result) == ("PASS", 0.01, 4, None, None)
    ev = client.get(f"/api/runs/{rid}/events").json()
    assert ev["total"] == 2 and [e["type"] for e in ev["items"]] == ["llm_call", "tool_call"]
    assert ev["items"][0]["run_id"] == rid and ev["items"][0]["ts"].endswith("Z")
    assert len(client.get(f"/api/runs/{rid}/events", params={"limit": 1}).json()["items"]) == 1
    assert_error(client.get(f"/api/runs/{rid}/events", params={"limit": 1001}), 422, "VALIDATION_ERROR")
    assert_error(client.get(f"/api/runs/{uuid.uuid4()}"), 404, "NOT_FOUND")
    assert_error(client.get(f"/api/runs/{uuid.uuid4()}/events"), 404, "NOT_FOUND")


# ---- 3.5 results ------------------------------------------------------------------------------
@needs_db
def test_leaderboard_numbers(client):
    body = Results.model_validate(client.get(f"/api/benchmarks/{BID}/results").json())
    a1, a2 = body.items
    assert (a1.agent_id, a2.agent_id) == ("t16-a1", "t16-a2")         # pass rate desc
    # a1 baseline: PASS, PASS, FAIL, PASS counted; one INFRA attempt excluded
    assert (a1.runs_counted, a1.infra_excluded) == (4, 1)
    assert a1.pass_rate.model_dump() == stats.wilson(3, 4)
    assert a1.cost.mean == pytest.approx((0.01 + 0.03 + 0.02 + 0.04) / 4)
    assert a1.steps.median == 5.5 and a1.cost_confidence.model_dump() == {"verified": 3, "estimated": 1}
    # a2 baseline: one FAIL counted, 3 INFRA attempts excluded; n=1 -> null std / CI
    assert (a2.runs_counted, a2.infra_excluded, a2.pass_rate.value) == (1, 3, 0.0)
    assert (a2.cost.n, a2.cost.std, a2.cost.ci_low) == (1, None, None)
    assert body.items[0].task_id is None and body.generated_at.tzinfo is not None


@needs_db
def test_compare_grid_and_filters(client):
    rows = client.get(f"/api/benchmarks/{BID}/results", params={"group_by": "agent_task"}).json()["items"]
    assert {(r["agent_id"], r["task_id"]) for r in rows} == {("t16-a1", "t16-t1"), ("t16-a1", "t16-t2"),
                                                             ("t16-a2", "t16-t1")}
    t2 = next(r for r in rows if r["task_id"] == "t16-t2")
    assert t2["pass_rate"]["value"] == 1.0 and t2["runs_counted"] == 1
    only_a2 = client.get(f"/api/benchmarks/{BID}/results", params={"agent_ids": "t16-a2"}).json()["items"]
    assert [r["agent_id"] for r in only_a2] == ["t16-a2"]
    research = client.get(f"/api/benchmarks/{BID}/results", params={"category": "research"}).json()["items"]
    assert [(r["agent_id"], r["runs_counted"]) for r in research] == [("t16-a1", 1)]
    fault = client.get(f"/api/benchmarks/{BID}/results", params={"scenario": FAULT}).json()["items"]
    assert all(r["scenario"] == FAULT for r in fault) and len(fault) == 2
    assert_error(client.get(f"/api/benchmarks/{BID}/results", params={"group_by": "task"}),
                 422, "VALIDATION_ERROR")


@needs_db
def test_results_empty_benchmark(client):
    body = client.get(f"/api/benchmarks/{EMPTY_BID}/results").json()
    assert body["items"] == [] and body["benchmark_id"] == EMPTY_BID
    b = client.get(f"/api/benchmarks/{EMPTY_BID}").json()
    assert b["progress"] == {"total": 0, "queued": 0, "running": 0, "done": 0, "infra_error": 0, "excluded": 0}


# ---- 3.6 resilience ---------------------------------------------------------------------------
@needs_db
def test_resilience(client):
    items = client.get(f"/api/benchmarks/{BID}/resilience").json()["items"]
    rows = {r["agent_id"]: ResilienceRow.model_validate(r) for r in items}
    assert set(rows) == {"t16-a1", "t16-a2"} and all(r.scenario == FAULT for r in rows.values())
    a1 = rows["t16-a1"]
    assert a1.baseline_pass_rate.value == 0.75 and a1.scenario_pass_rate.value == 0.5
    assert a1.resilience_score == pytest.approx(0.5 / 0.75, abs=1e-6)
    assert rows["t16-a2"].resilience_score is None                     # baseline pass rate 0
    assert client.get(f"/api/benchmarks/{EMPTY_BID}/resilience").json() == {"items": []}


# ---- lifecycle event types (migration 002) ---------------------------------------------------
def _has_migration_002() -> bool:
    try:
        with psycopg.connect(DSN, connect_timeout=2) as c:
            return c.execute("SELECT 1 FROM schema_migrations WHERE version ="
                             " '002_event_lifecycle_types'").fetchone() is not None
    except psycopg.Error:
        return False


@needs_db
@pytest.mark.skipif(not _has_migration_002(), reason="run db/migrate.py: needs migration 002")
def test_events_endpoint_returns_lifecycle_event_types(client, seeded):
    with psycopg.connect(DSN, autocommit=True) as c:
        rid = str(c.execute("INSERT INTO runs (agent_id, task_id, state, started_at)"
                            " VALUES ('t16-a1', 't16-t1', 'running', now()) RETURNING run_id").fetchone()[0])
        c.execute("INSERT INTO events (run_id, type, payload) VALUES"
                  " (%s, 'agent_started', '{\"task_id\": \"t16-t1\"}'),"
                  " (%s, 'llm_call', '{\"status_code\": 200}'),"
                  " (%s, 'grader_result', '{\"passed\": true, \"suite_count\": 2}')", (rid, rid, rid))
    r = client.get(f"/api/runs/{rid}/events")
    assert r.status_code == 200, r.text
    items = [Event.model_validate(e) for e in r.json()["items"]]
    assert [e.type for e in items] == ["agent_started", "llm_call", "grader_result"]
    assert items[2].payload == {"passed": True, "suite_count": 2}
