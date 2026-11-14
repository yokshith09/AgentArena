"""Measuring proxy (A4, F-01). Contract: docs/08 section 2; events: docs/07 section 3.

Agents call POST /runs/{run_id}/v1/chat/completions (OPENAI_BASE_URL = .../runs/{run_id}/v1).
The proxy checks the run is `running`, forwards to UPSTREAM_BASE_URL (Bifrost or mock_llm),
passes the response through, and writes one `llm_call` event plus one `tool_call` event per
requested tool call. A database failure never blocks forwarding (fail-open, logged to stderr).

Provider fault injection (A7) plugs in before forwarding, keyed on RunInfo.scenario.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.concurrency import run_in_threadpool

from .db import Database, Event, RunInfo
from .pricing import Pricing

log = logging.getLogger("proxy")

PREVIEW_LIMIT = 8 * 1024  # docs/07 section 3: bodies over 8 KB are stored truncated
ROOT = Path(__file__).resolve().parent.parent
# Request headers never forwarded upstream. Authorization is the agent's dummy key (08 section 1.2);
# accept-encoding is dropped so upstream bytes stay uncompressed and pass through unchanged.
DROP_REQUEST_HEADERS = {"host", "content-length", "authorization", "connection", "accept-encoding",
                        "x-agent-role", "transfer-encoding"}
DROP_RESPONSE_HEADERS = {"content-length", "content-encoding", "transfer-encoding", "connection"}


@dataclass
class Settings:
    upstream_base_url: str = field(
        default_factory=lambda: os.environ.get("UPSTREAM_BASE_URL", "http://bifrost:8080/v1"))
    # Empty = libpq defaults/environment (PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE).
    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", ""))
    pricing_file: str = field(
        default_factory=lambda: os.environ.get("PRICING_FILE", str(ROOT / "pricing.yaml")))
    # Only if the Bifrost deployment requires a key; never the agent's key.
    upstream_api_key: str = field(default_factory=lambda: os.environ.get("BIFROST_API_KEY", ""))
    upstream_timeout_s: float = 600.0


def openai_error(status: int, message: str, type_: str, code: str, headers: dict | None = None):
    return JSONResponse({"error": {"message": message, "type": type_, "param": None, "code": code}},
                        status_code=status, headers=headers)


def preview(raw: bytes | str) -> tuple[str, bool]:
    text = raw.decode("utf8", "replace") if isinstance(raw, bytes) else raw
    return (text[:PREVIEW_LIMIT], True) if len(text) > PREVIEW_LIMIT else (text, False)


def error_tag(status: int) -> str | None:
    """5xx, 429 and unreachable upstream are 'upstream' (orchestrator -> INFRA_ERROR candidates,
    docs/10 section 2.5). Other 4xx are the agent's own request errors: free text, not INFRA."""
    if status < 400:
        return None
    if status >= 500 or status == 429:
        return "upstream"
    return f"http_{status}"


class StreamAccumulator:
    """Parses OpenAI SSE chunks as they pass through, without altering them."""

    def __init__(self):
        self._buf = b""
        self.model = None
        self.usage = None
        self.finish_reason = None
        self.tool_calls: dict[int, dict] = {}
        self.raw_head = bytearray()

    def feed(self, chunk: bytes) -> None:
        if len(self.raw_head) <= PREVIEW_LIMIT:
            self.raw_head += chunk[: PREVIEW_LIMIT + 1 - len(self.raw_head)]
        self._buf += chunk
        *lines, self._buf = self._buf.split(b"\n")
        for line in lines:
            self._line(line.strip())

    def close(self) -> None:
        if self._buf.strip():
            self._line(self._buf.strip())
        self._buf = b""

    def _line(self, line: bytes) -> None:
        if not line.startswith(b"data:"):
            return
        data = line[5:].strip()
        if not data or data == b"[DONE]":
            return
        try:
            obj = json.loads(data)
        except ValueError:
            return
        self.model = obj.get("model") or self.model
        if obj.get("usage"):
            self.usage = obj["usage"]
        for ch in obj.get("choices") or []:
            if ch.get("finish_reason"):
                self.finish_reason = ch["finish_reason"]
            for tc in (ch.get("delta") or {}).get("tool_calls") or []:
                slot = self.tool_calls.setdefault(tc.get("index", len(self.tool_calls)),
                                                  {"id": None, "name": "", "arguments": ""})
                slot["id"] = tc.get("id") or slot["id"]
                fn = tc.get("function") or {}
                slot["name"] += fn.get("name") or ""
                slot["arguments"] += fn.get("arguments") or ""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    pricing = Pricing.load(settings.pricing_file)
    db = Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.upstream_timeout_s, connect=10.0))
        yield
        await app.state.client.aclose()
        db.close()

    app = FastAPI(title="AgentArena measuring proxy", lifespan=lifespan)
    app.state.settings, app.state.pricing, app.state.db = settings, pricing, db

    def build_events(*, run_id: str, endpoint: str, req: dict | None, raw_req: bytes, status: int,
                     model: str | None, usage: dict | None, finish_reason: str | None,
                     tool_calls: list[dict], stream: bool, raw_resp: bytes, latency: int,
                     error: str | None, role: str | None, run: RunInfo | None) -> list[Event]:
        req_model = (req or {}).get("model")
        tokens_in = tokens_out = cost = confidence = None
        warning = None
        if usage:
            tokens_in = int(usage.get("prompt_tokens") or 0)
            tokens_out = int(usage.get("completion_tokens") or 0)
        if 200 <= status < 300:
            day = (run.started_at.date() if run and run.started_at else dt.date.today())
            if usage:
                # pricing.yaml is keyed by the requested (Bifrost) model name; fall back to the
                # model the provider reports.
                cost = pricing.cost(req_model, day, tokens_in, tokens_out)
                if cost is None and model:
                    cost = pricing.cost(model, day, tokens_in, tokens_out)
                if cost is None:
                    confidence = "estimated"
                    warning = f"no price for model {req_model or model!r} on {day} in pricing.yaml"
                else:
                    confidence = "verified"
            else:
                # F-01 step 6, P0 rule: null tokens, cost 0, estimated, plus a warning.
                cost, confidence = 0.0, "estimated"
                warning = "upstream response had no usage block"
            if warning:
                log.warning("run %s: %s", run_id, warning)
        req_prev, req_cut = preview(raw_req)
        resp_prev, resp_cut = preview(raw_resp)
        payload = {
            "endpoint": "/" + endpoint, "model": req_model or model, "response_model": model,
            "status_code": status, "tokens_in": tokens_in, "tokens_out": tokens_out,
            "cost": cost, "cost_confidence": confidence, "finish_reason": finish_reason,
            "stream": stream, "request_preview": req_prev, "response_preview": resp_prev,
            "pricing_version": pricing.version,
        }
        if warning:
            payload["warning"] = warning
        if req_cut or resp_cut:
            payload["truncated"] = True
        events = [Event("llm_call", payload, latency=latency, error=error, agent_role=role)]
        for tc in tool_calls:
            args, cut = preview(tc.get("arguments") or "")
            p = {"name": tc.get("name"), "arguments_preview": args, "call_id": tc.get("id")}
            if cut:
                p["truncated"] = True
            events.append(Event("tool_call", p, agent_role=role))
        return events

    async def write_events(run_id: str, events: list[Event]) -> None:
        try:
            await run_in_threadpool(db.insert_events, run_id, events)
        except Exception as e:  # noqa: BLE001 - never block the agent on a DB failure (F-01)
            log.error("run %s: event write failed, %d event(s) lost: %s", run_id, len(events), e)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.api_route("/runs/{run_id}/v1/{endpoint:path}",
                   methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def forward(run_id: str, endpoint: str, request: Request):
        try:
            run_id = str(uuid.UUID(run_id))
        except ValueError:
            return openai_error(404, f"run {run_id} not found or not running",
                                "invalid_request_error", "run_not_found")
        run: RunInfo | None = None
        try:
            run = await run_in_threadpool(db.get_run, run_id)
        except Exception as e:  # noqa: BLE001 - any DB failure means fail-open
            # DB down: forward anyway so the agent is not blocked (T-05); events will be lost.
            log.error("run %s: run lookup failed, forwarding unchecked: %s", run_id, e)
        else:
            if run is None or run.state != "running":
                return openai_error(404, f"run {run_id} not found or not running",
                                    "invalid_request_error", "run_not_found")

        # A7 hook: provider faults for run.scenario are applied here, before forwarding.

        raw_req = await request.body()
        req_json = None
        if raw_req:
            try:
                req_json = json.loads(raw_req)
            except ValueError:
                req_json = None
        stream = isinstance(req_json, dict) and req_json.get("stream") is True
        if stream:
            opts = req_json.get("stream_options")
            if not isinstance(opts, dict) or "include_usage" not in opts:
                req_json["stream_options"] = {**(opts if isinstance(opts, dict) else {}),
                                              "include_usage": True}  # A-02
                raw_req = json.dumps(req_json).encode()

        headers = {k: v for k, v in request.headers.items() if k.lower() not in DROP_REQUEST_HEADERS}
        headers["x-bf-lh-run_id"] = run_id
        if settings.upstream_api_key:
            headers["authorization"] = f"Bearer {settings.upstream_api_key}"
        url = settings.upstream_base_url.rstrip("/") + "/" + endpoint
        if request.url.query:
            url += "?" + request.url.query
        role = request.headers.get("x-agent-role")
        client: httpx.AsyncClient = app.state.client
        common = {"run_id": run_id, "endpoint": endpoint,
                  "req": req_json if isinstance(req_json, dict) else None,
                  "raw_req": raw_req, "stream": stream, "role": role, "run": run}

        t0 = time.perf_counter()
        upstream_req = client.build_request(request.method, url, headers=headers, content=raw_req)
        try:
            resp = await client.send(upstream_req, stream=True)
        except httpx.HTTPError as e:
            latency = int((time.perf_counter() - t0) * 1000)
            msg = f"upstream unreachable: {type(e).__name__}: {e}"
            await write_events(run_id, build_events(
                **common, status=502, model=None, usage=None, finish_reason=None, tool_calls=[],
                raw_resp=msg.encode(), latency=latency, error="upstream"))
            return openai_error(502, msg, "server_error", "upstream_unreachable")

        out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in DROP_RESPONSE_HEADERS}
        is_sse = resp.headers.get("content-type", "").startswith("text/event-stream")

        if not (stream and is_sse and resp.status_code < 400):
            try:
                body = await resp.aread()
            finally:
                await resp.aclose()
            latency = int((time.perf_counter() - t0) * 1000)
            obj = None
            try:
                obj = json.loads(body) if body else None
            except ValueError:
                pass
            obj = obj if isinstance(obj, dict) else {}
            choices = obj.get("choices") or []
            tool_calls = [{"id": tc.get("id"), "name": (tc.get("function") or {}).get("name"),
                           "arguments": (tc.get("function") or {}).get("arguments")}
                          for ch in choices for tc in ((ch.get("message") or {}).get("tool_calls") or [])]
            await write_events(run_id, build_events(
                **common, status=resp.status_code, model=obj.get("model"), usage=obj.get("usage"),
                finish_reason=(choices[0].get("finish_reason") if choices else None),
                tool_calls=tool_calls, raw_resp=body, latency=latency,
                error=error_tag(resp.status_code)))
            return Response(body, status_code=resp.status_code, headers=out_headers)

        acc = StreamAccumulator()

        async def relay():
            try:
                async for chunk in resp.aiter_raw():
                    acc.feed(chunk)
                    yield chunk
            finally:
                await resp.aclose()
                acc.close()
                latency = int((time.perf_counter() - t0) * 1000)
                calls = [acc.tool_calls[i] for i in sorted(acc.tool_calls)]
                await write_events(run_id, build_events(
                    **common, status=resp.status_code, model=acc.model, usage=acc.usage,
                    finish_reason=acc.finish_reason, tool_calls=calls, raw_resp=bytes(acc.raw_head),
                    latency=latency, error=error_tag(resp.status_code)))

        return StreamingResponse(relay(), status_code=resp.status_code, headers=out_headers,
                                 media_type=resp.headers.get("content-type"))

    return app


logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = create_app()
