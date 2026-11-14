"""Proxy tests T-01...T-05 (docs/09). Need Postgres with the 001 schema at DATABASE_URL
(e.g. `docker compose up -d migrate`); skipped otherwise. mock_llm runs in-process."""
from __future__ import annotations

import json
import os
import statistics
import threading
import time
import uuid

import httpx
import psycopg
import pytest
from fastapi.testclient import TestClient

from mock_llm import server as mock
from proxy.app import PREVIEW_LIMIT, Settings, create_app

DSN = os.environ.get("DATABASE_URL", "")  # empty = libpq PG* environment variables
AGENT, TASK = "test-proxy-agent", "test-proxy-task"
PRICE_IN, PRICE_OUT = 1.0, 2.0  # per 1M tokens, test-only values


def _db_available() -> bool:
    try:
        with psycopg.connect(DSN, connect_timeout=2) as c:
            c.execute("SELECT 1 FROM events LIMIT 1")
        return True
    except psycopg.Error:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="no migrated Postgres at DATABASE_URL / PG* env")


@pytest.fixture(scope="module")
def mock_port():
    srv = mock.serve(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


def script(*responses, fail_n=0, status=503):
    mock.STATE.update(i=0, script={"responses": list(responses)}, fail={"n": fail_n, "status": status})


@pytest.fixture(scope="module")
def conn():
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute("INSERT INTO agents(agent_id,name,mode,entrypoint,source_path) VALUES"
                  " (%s,%s,'command','python agent.py','agents/test') ON CONFLICT DO NOTHING", (AGENT, AGENT))
        c.execute("INSERT INTO tasks(task_id,category,prompt,workspace,grader,reference_solution,task_dir,task_hash)"
                  " VALUES (%s,'coding','p','workspace','{}','ref','tasks/test','h') ON CONFLICT DO NOTHING", (TASK,))
        yield c
        c.execute("DELETE FROM runs WHERE agent_id=%s", (AGENT,))
        c.execute("DELETE FROM tasks WHERE task_id=%s", (TASK,))
        c.execute("DELETE FROM agents WHERE agent_id=%s", (AGENT,))


@pytest.fixture
def run_id(conn):
    rid = str(uuid.uuid4())
    conn.execute("INSERT INTO runs(run_id,agent_id,task_id,state,started_at) VALUES (%s,%s,%s,'running',now())",
                 (rid, AGENT, TASK))
    return rid


@pytest.fixture(scope="module")
def pricing_file(tmp_path_factory):
    p = tmp_path_factory.mktemp("pricing") / "pricing.yaml"
    p.write_text(f'version: "test"\ncurrency: USD\nmodels:\n  "mock-model":\n'
                 f'    effective_from: "2026-01-01"\n    input_per_1m_tokens: {PRICE_IN}\n'
                 f'    output_per_1m_tokens: {PRICE_OUT}\n', encoding="utf8")
    return str(p)


def make_client(pricing_file, upstream, dsn=DSN):
    return TestClient(create_app(Settings(upstream_base_url=upstream, database_url=dsn,
                                          pricing_file=pricing_file)))


@pytest.fixture
def client(mock_port, pricing_file):
    with make_client(pricing_file, f"http://127.0.0.1:{mock_port}/v1") as c:
        yield c


def events(conn, rid):
    rows = conn.execute("SELECT type, payload, latency, error, agent_role FROM events"
                        " WHERE run_id=%s ORDER BY id", (rid,)).fetchall()
    return [dict(zip(("type", "payload", "latency", "error", "agent_role"), r)) for r in rows]


def chat(**kw):
    return {"model": "mock-model", "messages": [{"role": "user", "content": "hi"}], **kw}


def expected_cost(tin, tout):
    return round((tin * PRICE_IN + tout * PRICE_OUT) / 1_000_000, 6)


# ---- T-01 non-stream ----------------------------------------------------------------------
def test_t01_non_stream_logs_tokens_cost_latency(client, conn, run_id):
    script({"text": "hello"})
    r = client.post(f"/runs/{run_id}/v1/chat/completions", json=chat(),
                    headers={"Authorization": "Bearer dummy"})
    assert r.status_code == 200
    body = r.json()
    assert body["choices"][0]["message"]["content"] == "hello"
    [ev] = events(conn, run_id)
    p, u = ev["payload"], body["usage"]
    assert ev["type"] == "llm_call" and ev["error"] is None
    assert (p["tokens_in"], p["tokens_out"]) == (u["prompt_tokens"], u["completion_tokens"])
    assert p["cost"] == expected_cost(u["prompt_tokens"], u["completion_tokens"])
    assert p["cost_confidence"] == "verified"
    assert p["endpoint"] == "/chat/completions" and p["stream"] is False and p["status_code"] == 200
    assert p["model"] == "mock-model" and p["finish_reason"] == "stop"
    assert isinstance(ev["latency"], int) and ev["latency"] >= 0


def test_agent_role_header_is_stored(client, conn, run_id):
    script({"text": "x"})
    client.post(f"/runs/{run_id}/v1/chat/completions", json=chat(), headers={"X-Agent-Role": "planner"})
    assert events(conn, run_id)[0]["agent_role"] == "planner"


def test_large_bodies_are_truncated(client, conn, run_id):
    script({"text": "x"})
    big = chat(messages=[{"role": "user", "content": "a" * (PREVIEW_LIMIT * 2)}])
    assert client.post(f"/runs/{run_id}/v1/chat/completions", json=big).status_code == 200
    p = events(conn, run_id)[0]["payload"]
    assert p["truncated"] is True and len(p["request_preview"]) == PREVIEW_LIMIT


# ---- T-02 streaming -----------------------------------------------------------------------
def test_t02_stream_passthrough_injects_include_usage(client, conn, run_id, mock_port):
    script({"text": "streamed"})
    direct = httpx.post(f"http://127.0.0.1:{mock_port}/v1/chat/completions",
                        json=chat(stream=True, stream_options={"include_usage": True})).content
    script({"text": "streamed"})
    with client.stream("POST", f"/runs/{run_id}/v1/chat/completions", json=chat(stream=True)) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        proxied = b"".join(r.iter_raw())
    assert proxied == direct  # chunks unchanged; usage chunk present because the proxy added include_usage
    usage = next(json.loads(l[6:])["usage"] for l in proxied.split(b"\n")
                 if l.startswith(b"data: {") and b'"usage"' in l)
    [ev] = events(conn, run_id)
    p = ev["payload"]
    assert p["stream"] is True and p["finish_reason"] == "stop"
    assert (p["tokens_in"], p["tokens_out"]) == (usage["prompt_tokens"], usage["completion_tokens"])
    assert p["cost_confidence"] == "verified"


# ---- T-04 tool calls ----------------------------------------------------------------------
@pytest.mark.parametrize("stream", [False, True])
def test_t04_n_tool_calls_give_n_events(client, conn, run_id, stream):
    script({"tool_calls": [{"name": "read_file", "arguments": '{"path": "a.py"}'},
                           {"name": "run_tests", "arguments": "{}"}]})
    with client.stream("POST", f"/runs/{run_id}/v1/chat/completions", json=chat(stream=stream)) as r:
        r.read()
    evs = events(conn, run_id)
    assert [e["type"] for e in evs] == ["llm_call", "tool_call", "tool_call"]
    assert [e["payload"]["name"] for e in evs[1:]] == ["read_file", "run_tests"]
    assert evs[1]["payload"]["arguments_preview"] == '{"path": "a.py"}'
    assert evs[1]["payload"]["call_id"] == "call_0_0"
    assert evs[0]["payload"]["finish_reason"] == "tool_calls"


# ---- T-05 errors --------------------------------------------------------------------------
@pytest.mark.parametrize("rid", [str(uuid.uuid4()), "not-a-uuid"])
def test_t05_unknown_run_404(client, rid):
    r = client.post(f"/runs/{rid}/v1/chat/completions", json=chat())
    assert r.status_code == 404
    assert r.json()["error"]["type"] == "invalid_request_error"
    assert r.json()["error"]["code"] == "run_not_found"


def test_t05_finished_run_404(client, conn, run_id):
    conn.execute("UPDATE runs SET state='done', status='PASS', passed=true WHERE run_id=%s", (run_id,))
    assert client.post(f"/runs/{run_id}/v1/chat/completions", json=chat()).status_code == 404
    assert events(conn, run_id) == []


def test_t05_upstream_5xx_passed_through_and_tagged(client, conn, run_id):
    script({"text": "x"}, fail_n=1, status=503)
    r = client.post(f"/runs/{run_id}/v1/chat/completions", json=chat())
    assert r.status_code == 503 and r.json()["error"]["message"] == "mock failure"
    [ev] = events(conn, run_id)
    assert ev["error"] == "upstream" and ev["payload"]["status_code"] == 503
    assert ev["payload"]["cost_confidence"] is None


def test_t05_upstream_unreachable_502_tagged(pricing_file, conn, run_id):
    with make_client(pricing_file, "http://127.0.0.1:1/v1") as c:
        r = c.post(f"/runs/{run_id}/v1/chat/completions", json=chat())
    assert r.status_code == 502 and r.json()["error"]["code"] == "upstream_unreachable"
    assert events(conn, run_id)[0]["error"] == "upstream"


def test_t05_db_down_still_forwards(mock_port, pricing_file):
    script({"text": "still here"})
    with make_client(pricing_file, f"http://127.0.0.1:{mock_port}/v1",
                     dsn="host=127.0.0.1 port=1 connect_timeout=1") as c:
        r = c.post(f"/runs/{uuid.uuid4()}/v1/chat/completions", json=chat())
    assert r.status_code == 200 and r.json()["choices"][0]["message"]["content"] == "still here"


# ---- headers, missing usage, unknown price (stub upstream) --------------------------------
def stub_upstream(client, handler):
    client.app.state.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_headers_rewritten_for_upstream(client, run_id):
    seen = {}

    def handler(req: httpx.Request):
        seen.update(req.headers)
        return httpx.Response(200, json={"model": "mock-model", "choices": [],
                                         "usage": {"prompt_tokens": 1, "completion_tokens": 1}})
    stub_upstream(client, handler)
    client.post(f"/runs/{run_id}/v1/chat/completions", json=chat(),
                headers={"Authorization": "Bearer agent-dummy", "X-Agent-Role": "coder"})
    assert seen["x-bf-lh-run_id"] == run_id
    assert "authorization" not in seen and "x-agent-role" not in seen


def test_missing_usage_is_estimated_zero_cost(client, conn, run_id):
    stub_upstream(client, lambda req: httpx.Response(
        200, json={"model": "mock-model", "choices": [{"message": {"content": "x"}, "finish_reason": "stop"}]}))
    assert client.post(f"/runs/{run_id}/v1/chat/completions", json=chat()).status_code == 200
    p = events(conn, run_id)[0]["payload"]
    assert (p["tokens_in"], p["tokens_out"], p["cost"], p["cost_confidence"]) == (None, None, 0.0, "estimated")
    assert "usage" in p["warning"]


def test_unpriced_model_is_estimated_null_cost(client, conn, run_id):
    stub_upstream(client, lambda req: httpx.Response(
        200, json={"model": "other", "choices": [], "usage": {"prompt_tokens": 5, "completion_tokens": 7}}))
    client.post(f"/runs/{run_id}/v1/chat/completions", json=chat(model="other"))
    p = events(conn, run_id)[0]["payload"]
    assert (p["tokens_in"], p["tokens_out"], p["cost"], p["cost_confidence"]) == (5, 7, None, "estimated")


def test_other_endpoints_forwarded_and_logged(client, conn, run_id):
    stub_upstream(client, lambda req: httpx.Response(
        200, json={"object": "list", "data": [], "model": "mock-model",
                   "usage": {"prompt_tokens": 3, "completion_tokens": 0}}))
    r = client.post(f"/runs/{run_id}/v1/embeddings", json={"model": "mock-model", "input": "x"})
    assert r.status_code == 200
    assert events(conn, run_id)[0]["payload"]["endpoint"] == "/embeddings"


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# ---- T-03 added latency (in-process; the live number is measured against uvicorn) --------
def test_t03_added_latency_is_small(client, run_id, mock_port):
    script({"text": "x"})
    url = f"http://127.0.0.1:{mock_port}/v1/chat/completions"
    with httpx.Client() as direct:
        def timed(fn):
            t = time.perf_counter(); fn(); return (time.perf_counter() - t) * 1000
        d = [timed(lambda: direct.post(url, json=chat())) for _ in range(20)]
        p = [timed(lambda: client.post(f"/runs/{run_id}/v1/chat/completions", json=chat()))
             for _ in range(20)]
    added = statistics.median(p) - statistics.median(d)
    print(f"\nT-03 median direct={statistics.median(d):.1f} ms proxy={statistics.median(p):.1f} ms "
          f"added={added:.1f} ms")
    assert added < 50  # NFR-03 target
