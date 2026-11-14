"""T-20: provider faults (503 outage, 429 rate limit) fire exactly first-N, emit fault_injected,
are reproducible per run_id, and are tagged 'injected' (never 'upstream'). Plus fault-loader
validation. DB-backed tests need the compose Postgres (skipped otherwise)."""
from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from mock_llm import server as mock
from proxy.app import Settings, create_app
from proxy.faults import FaultConfigError, load_faults

ROOT = Path(__file__).resolve().parents[2]
DSN = os.environ.get("DATABASE_URL", "")
AGENT, TASK = "test-fault-agent", "test-fault-task"


def _db_available() -> bool:
    try:
        with psycopg.connect(DSN, connect_timeout=2) as c:
            c.execute("SELECT 1 FROM events LIMIT 1")
        return True
    except psycopg.Error:
        return False


needs_db = pytest.mark.skipif(not _db_available(), reason="no migrated Postgres at DATABASE_URL / PG* env")


# ---- loader -----------------------------------------------------------------------------------
def test_repo_fault_catalog_loads():
    faults = load_faults(ROOT / "faults")
    assert {k: (f.group, f.layer, f.first_n, f.status) for k, f in faults.items()} == {
        "provider_503_outage": ("provider", "proxy", 3, 503),
        "provider_429_ratelimit": ("provider", "proxy", 2, 429),
    }


GOOD = {"id": "x", "group": "provider", "layer": "proxy", "description": "d",
        "params": "{ first_n: 2, status: 503 }"}


def write_fault(d: Path, name="x", **over) -> Path:
    doc = {**GOOD, **over}
    lines = [f"{k}: {v}" for k, v in doc.items() if v is not None]
    (d / f"{name}.yaml").write_text("\n".join(lines) + "\n", encoding="utf8")
    return d


@pytest.mark.parametrize("over, msg", [
    ({"params": None}, "missing key"),
    ({"id": "other"}, "must match the file name"),
    ({"group": "weather"}, "group must be"),
    ({"layer": "kernel"}, "layer must be"),
    ({"params": "{ first_n: 0, status: 503 }"}, "first_n"),
    ({"params": "{ first_n: 2, status: 200 }"}, "params.status"),
    ({"params": "{ status: 503 }"}, "first_n"),
    ({"group": "tool"}, "must be group provider"),
    ({"params": "[1, 2]"}, "params must be a mapping"),
])
def test_loader_rejects_invalid_definitions(tmp_path, over, msg):
    with pytest.raises(FaultConfigError, match=msg):
        load_faults(write_fault(tmp_path, **over))


def test_loader_rejects_broken_yaml_and_duplicates(tmp_path):
    (tmp_path / "x.yaml").write_text("id: [unclosed\n", encoding="utf8")
    with pytest.raises(FaultConfigError, match="invalid YAML"):
        load_faults(tmp_path)
    (tmp_path / "x.yaml").unlink()
    write_fault(tmp_path)
    (tmp_path / "x.yml").write_text((tmp_path / "x.yaml").read_text(), encoding="utf8")
    with pytest.raises(FaultConfigError, match="duplicate"):
        load_faults(tmp_path)


def test_non_proxy_faults_load_but_are_not_injected(tmp_path):
    (tmp_path / "tool_run_tests_error.yaml").write_text(
        "id: tool_run_tests_error\ngroup: tool\nlayer: agent_env\ndescription: d\n"
        "params: { tool: run_tests, fail_first_n: 2 }\n", encoding="utf8")
    assert "tool_run_tests_error" in load_faults(tmp_path)


def test_proxy_refuses_to_start_with_invalid_catalog(tmp_path):
    write_fault(tmp_path, group="weather")
    with pytest.raises(FaultConfigError):
        create_app(Settings(faults_dir=str(tmp_path), pricing_file=str(ROOT / "pricing.yaml")))


# ---- injection (T-20) -------------------------------------------------------------------------
@pytest.fixture(scope="module")
def mock_port():
    srv = mock.serve(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


@pytest.fixture(scope="module")
def conn():
    if not _db_available():
        pytest.skip("no migrated Postgres at DATABASE_URL / PG* env")
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute("INSERT INTO agents(agent_id,name,mode,entrypoint,source_path) VALUES"
                  " (%s,%s,'command','python agent.py','agents/test') ON CONFLICT DO NOTHING", (AGENT, AGENT))
        c.execute("INSERT INTO tasks(task_id,category,prompt,workspace,grader,reference_solution,task_dir,task_hash)"
                  " VALUES (%s,'coding','p','workspace','{}','ref','tasks/test','h') ON CONFLICT DO NOTHING", (TASK,))
        yield c
        c.execute("DELETE FROM runs WHERE agent_id=%s", (AGENT,))
        c.execute("DELETE FROM tasks WHERE task_id=%s", (TASK,))
        c.execute("DELETE FROM agents WHERE agent_id=%s", (AGENT,))


def new_run(conn, scenario: str) -> str:
    rid = str(uuid.uuid4())
    conn.execute("INSERT INTO runs(run_id,agent_id,task_id,scenario,state,started_at)"
                 " VALUES (%s,%s,%s,%s,'running',now())", (rid, AGENT, TASK, scenario))
    return rid


def app_client(mock_port):
    return TestClient(create_app(Settings(upstream_base_url=f"http://127.0.0.1:{mock_port}/v1",
                                          database_url=DSN, faults_dir=str(ROOT / "faults"),
                                          pricing_file=str(ROOT / "pricing.yaml"))))


@pytest.fixture
def client(mock_port):
    with app_client(mock_port) as c:
        yield c


def call(client, rid, **kw):
    body = {"model": "mock-model", "messages": [{"role": "user", "content": "hi"}], **kw}
    return client.post(f"/runs/{rid}/v1/chat/completions", json=body)


def events(conn, rid):
    return conn.execute("SELECT type, payload, error FROM events WHERE run_id=%s ORDER BY id",
                        (rid,)).fetchall()


def reset_mock():
    mock.STATE.update(i=0, script={"responses": [{"text": "ok"}]}, fail={"n": 0, "status": 503})


@needs_db
@pytest.mark.parametrize("scenario, n, status, type_", [
    ("provider_503_outage", 3, 503, "server_error"),
    ("provider_429_ratelimit", 2, 429, "rate_limit_error"),
])
def test_t20_first_n_injected_then_pass_through(client, conn, scenario, n, status, type_):
    reset_mock()
    rid = new_run(conn, scenario)
    responses = [call(client, rid) for _ in range(n + 2)]
    assert [r.status_code for r in responses] == [status] * n + [200, 200]
    for k, r in enumerate(responses[:n], start=1):
        err = r.json()["error"]
        assert (err["type"], err["code"]) == (type_, "injected_fault")
        assert err["message"] == f"injected fault {scenario}: call {k} of {n}"
        assert r.headers.get("retry-after") == ("1" if status == 429 else None)
    assert mock.STATE["i"] == 2  # injected calls never reached the upstream

    evs = events(conn, rid)
    injected = [e for e in evs if e[0] == "fault_injected"]
    assert [p for _, p, _ in injected] == [
        {"fault_id": scenario, "group": "provider", "detail": f"call {k} of {n}"} for k in range(1, n + 1)]
    llm = [(p["status_code"], err) for t, p, err in evs if t == "llm_call"]
    assert llm == [(status, "injected")] * n + [(200, None)] * 2   # never 'upstream' -> never INFRA
    first = next(p for t, p, _ in evs if t == "llm_call")
    assert (first["cost"], first["cost_confidence"], first["tokens_in"], first["fault_id"]) == \
        (0.0, "verified", None, scenario)
    # ordering: each fault_injected event directly precedes its injected llm_call
    assert [t for t, _, _ in evs[: 2 * n]] == ["fault_injected", "llm_call"] * n


@needs_db
def test_t20_reproducible_for_same_scenario_and_run(client, conn, mock_port):
    reset_mock()
    seqs = []
    for _ in range(2):
        rid = new_run(conn, "provider_503_outage")
        seqs.append([call(client, rid).status_code for _ in range(5)])
    assert seqs[0] == seqs[1] == [503, 503, 503, 200, 200]


@needs_db
def test_restart_mid_run_does_not_inject_again(conn, mock_port):
    reset_mock()
    rid = new_run(conn, "provider_503_outage")
    with app_client(mock_port) as c1:
        assert call(c1, rid).status_code == 503
    with app_client(mock_port) as c2:   # fresh proxy process: count is seeded from the DB
        assert [call(c2, rid).status_code for _ in range(3)] == [503, 503, 200]


@needs_db
def test_baseline_and_non_proxy_scenarios_are_not_injected(client, conn):
    reset_mock()
    for scenario in ("baseline", "tool_run_tests_error", "unknown_scenario"):
        rid = new_run(conn, scenario)
        assert call(client, rid).status_code == 200
        assert not [e for e in events(conn, rid) if e[0] == "fault_injected"]


@needs_db
def test_streaming_request_gets_json_injected_error(client, conn):
    reset_mock()
    rid = new_run(conn, "provider_429_ratelimit")
    r = call(client, rid, stream=True)
    assert r.status_code == 429 and r.json()["error"]["code"] == "injected_fault"
    assert events(conn, rid)[1][1]["stream"] is True


@needs_db
def test_agent_role_recorded_on_injected_events(client, conn):
    reset_mock()
    rid = new_run(conn, "provider_503_outage")
    client.post(f"/runs/{rid}/v1/chat/completions", json={"model": "mock-model", "messages": []},
                headers={"X-Agent-Role": "planner"})
    roles = conn.execute("SELECT agent_role FROM events WHERE run_id=%s", (rid,)).fetchall()
    assert roles == [("planner",), ("planner",)]
