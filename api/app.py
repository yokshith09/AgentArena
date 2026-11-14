"""Dashboard REST API (A5, F-08). Contract: docs/08 section 3; stats: api/stats (F-07).

Read-only over the DB except POST /api/benchmarks, which only inserts a `queued` benchmark
(the orchestrator picks it up). Statistics are computed here, never in the UI.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg.types.json import Jsonb
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import stats
from .db import Pool
from .models import (
    Agent,
    Benchmark,
    BenchmarkConfig,
    ErrorEnvelope,
    Event,
    Health,
    Page,
    Resilience,
    Results,
    Run,
    RunDetail,
    Scenario,
    TaskSummary,
)

log = logging.getLogger("api")
ROOT = Path(__file__).resolve().parent.parent
MAX_ATTEMPTS = 3  # INFRA_ERROR retries per slot (F-06); a slot at this attempt is "excluded"
BASELINE = Scenario(id="baseline", group="baseline", layer="none", description="No fault injected")
RUN_COLS = ("run_id, benchmark_id, agent_id, task_id, scenario, repeat_index, attempt, state, status,"
            " passed, model, tokens_in, tokens_out, cost, cost_confidence, duration, steps, tool_calls,"
            " started_at, finished_at, error")


@dataclass
class Settings:
    # Empty = libpq defaults/environment (PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE).
    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", ""))
    faults_dir: str = field(default_factory=lambda: os.environ.get("FAULTS_DIR", str(ROOT / "faults")))
    cors_origins: list[str] = field(default_factory=lambda: [
        o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()])


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status, self.code, self.message, self.details = status, code, message, details


def not_found(what: str, ident: str) -> ApiError:
    return ApiError(404, "NOT_FOUND", f"{what} {ident} not found")


def invalid(fields: dict[str, str], message: str = "validation failed") -> ApiError:
    return ApiError(422, "VALIDATION_ERROR", message, {"fields": fields})


def envelope(status: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message, "details": details}},
                        status_code=status)


def as_uuid(value: str, what: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError:
        raise not_found(what, value) from None


def load_scenarios(faults_dir: str) -> dict[str, Scenario]:
    """baseline + one scenario per faults/*.yaml (docs/07 section 7). Invalid files fail loudly."""
    out = {"baseline": BASELINE}
    for path in sorted(Path(faults_dir).glob("*.y*ml")):
        doc = yaml.safe_load(path.read_text(encoding="utf8")) or {}
        sc = Scenario(id=doc["id"], group=doc["group"], layer=doc["layer"],
                      description=doc.get("description", ""))
        out[sc.id] = sc
    return out


def _f(x: Any) -> float | None:
    return None if x is None else float(x)


def run_out(row: dict) -> dict:
    row = dict(row)
    for k in ("run_id", "benchmark_id"):
        row[k] = None if row[k] is None else str(row[k])
    for k in ("cost", "duration"):
        row[k] = _f(row[k])
    return row


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    pool = Pool(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        pool.close()

    app = FastAPI(title="AgentArena API", lifespan=lifespan,
                  responses={404: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}})
    app.state.pool, app.state.settings = pool, settings
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["GET", "POST"], allow_headers=["*"])

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, e: ApiError):
        return envelope(e.status, e.code, e.message, e.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        fields = {".".join(str(p) for p in err["loc"] if p != "body") or "body": err["msg"]
                  for err in e.errors()}
        return envelope(422, "VALIDATION_ERROR", "request validation failed", {"fields": fields})

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        code = {404: "NOT_FOUND", 409: "CONFLICT", 422: "VALIDATION_ERROR"}.get(e.status_code, "INTERNAL")
        return envelope(e.status_code, code, str(e.detail), None)

    @app.exception_handler(Exception)
    async def _internal(_: Request, e: Exception):
        log.exception("unhandled error")
        return envelope(500, "INTERNAL", f"{type(e).__name__}: internal error", None)

    def scenarios() -> dict[str, Scenario]:
        return load_scenarios(settings.faults_dir)

    # ---- 3.1 catalog & health ----------------------------------------------------------------
    @app.get("/api/health", response_model=Health)
    def health():
        try:
            with pool.conn() as c:
                c.execute("SELECT 1")
            return {"status": "ok", "db": "ok"}
        except Exception as e:  # noqa: BLE001 - health reports any DB failure as "down"
            log.warning("health: db down: %s", e)
            return {"status": "ok", "db": "down"}

    @app.get("/api/agents", response_model=Page[Agent])
    def list_agents(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
        with pool.conn() as c:
            total = c.execute("SELECT count(*) AS n FROM agents").fetchone()["n"]
            items = c.execute("SELECT agent_id, name, mode, entrypoint, model_config, description"
                              " FROM agents ORDER BY agent_id LIMIT %s OFFSET %s", (limit, offset)).fetchall()
        return {"items": items, "total": total}

    @app.get("/api/agents/{agent_id}", response_model=Agent)
    def get_agent(agent_id: str):
        with pool.conn() as c:
            row = c.execute("SELECT agent_id, name, mode, entrypoint, model_config, description"
                            " FROM agents WHERE agent_id = %s", (agent_id,)).fetchone()
        if not row:
            raise not_found("agent", agent_id)
        return row

    @app.get("/api/tasks", response_model=Page[TaskSummary])
    def list_tasks(category: str | None = None, limit: int = Query(50, ge=1, le=200),
                   offset: int = Query(0, ge=0)):
        where, args = ("WHERE category = %s", [category]) if category else ("", [])
        with pool.conn() as c:
            total = c.execute(f"SELECT count(*) AS n FROM tasks {where}", args).fetchone()["n"]
            items = c.execute(
                "SELECT task_id, category, prompt, grader->>'type' AS grader_type, faults_allowed,"
                f" validated, weak FROM tasks {where} ORDER BY task_id LIMIT %s OFFSET %s",
                [*args, limit, offset]).fetchall()
        return {"items": items, "total": total}

    @app.get("/api/scenarios", response_model=Page[Scenario])
    def list_scenarios():
        items = list(scenarios().values())
        return {"items": items, "total": len(items)}

    # ---- 3.2 benchmarks ------------------------------------------------------------------------
    def benchmark_out(c, row: dict) -> dict:
        bid = row["benchmark_id"]
        latest = c.execute(
            "SELECT DISTINCT ON (agent_id, task_id, scenario, repeat_index) state, status, attempt"
            " FROM runs WHERE benchmark_id = %s"
            " ORDER BY agent_id, task_id, scenario, repeat_index, attempt DESC", (bid,)).fetchall()
        spend = c.execute("SELECT coalesce(sum(cost), 0) AS s FROM runs WHERE benchmark_id = %s",
                          (bid,)).fetchone()["s"]
        cfg = row["config"] or {}
        try:
            total = (len(cfg["agent_ids"]) * len(cfg["task_ids"])
                     * len(cfg.get("scenarios") or ["baseline"]) * int(cfg["n_runs"]))
        except (KeyError, TypeError, ValueError):
            total = len(latest)  # config without a full matrix: count the slots that exist
        p = {"total": total, "queued": 0, "running": 0, "done": 0, "infra_error": 0, "excluded": 0}
        for r in latest:
            if r["state"] == "running":
                p["running"] += 1
            elif r["state"] == "done" and r["status"] == "INFRA_ERROR":
                p["excluded" if r["attempt"] >= MAX_ATTEMPTS else "infra_error"] += 1
            elif r["state"] == "done":
                p["done"] += 1
        p["queued"] = max(0, total - p["running"] - p["done"] - p["infra_error"] - p["excluded"])
        return {**row, "benchmark_id": str(bid), "config": cfg, "progress": p, "spend_usd": float(spend)}

    bench_cols = "benchmark_id, name, config, state, error, created_at, started_at, finished_at"

    @app.post("/api/benchmarks", response_model=Benchmark, status_code=202)
    def create_benchmark(cfg: BenchmarkConfig):
        known = scenarios()
        fields: dict[str, str] = {}
        with pool.conn() as c:
            agents = {r["agent_id"] for r in c.execute(
                "SELECT agent_id FROM agents WHERE agent_id = ANY(%s)", (cfg.agent_ids,))}
            tasks = {r["task_id"]: r for r in c.execute(
                "SELECT task_id, validated, faults_allowed FROM tasks WHERE task_id = ANY(%s)",
                (cfg.task_ids,))}
            if missing := [a for a in cfg.agent_ids if a not in agents]:
                fields["agent_ids"] = "unknown agent(s): " + ", ".join(missing)
            if missing := [t for t in cfg.task_ids if t not in tasks]:
                fields["task_ids"] = "unknown task(s): " + ", ".join(missing)
            elif unvalidated := [t for t in cfg.task_ids if not tasks[t]["validated"]]:
                fields["task_ids"] = "task(s) not validated: " + ", ".join(unvalidated)
            if unknown := [s for s in cfg.scenarios if s not in known]:
                fields["scenarios"] = "unknown scenario(s): " + ", ".join(unknown)
            elif "task_ids" not in fields:
                bad = [f"{s} not allowed for {t}" for s in cfg.scenarios if s != "baseline"
                       for t in cfg.task_ids if s not in (tasks[t]["faults_allowed"] or [])]
                if bad:
                    fields["scenarios"] = "; ".join(bad)
            if fields:
                raise invalid(fields, "benchmark launch rejected")
            row = c.execute(f"INSERT INTO benchmarks (name, config) VALUES (%s, %s) RETURNING {bench_cols}",
                            (cfg.name, Jsonb(cfg.model_dump()))).fetchone()
            return benchmark_out(c, row)

    @app.get("/api/benchmarks", response_model=Page[Benchmark])
    def list_benchmarks(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
        with pool.conn() as c:
            total = c.execute("SELECT count(*) AS n FROM benchmarks").fetchone()["n"]
            rows = c.execute(f"SELECT {bench_cols} FROM benchmarks ORDER BY created_at DESC, benchmark_id"
                             " LIMIT %s OFFSET %s", (limit, offset)).fetchall()
            return {"items": [benchmark_out(c, r) for r in rows], "total": total}

    def fetch_benchmark(c, benchmark_id: str) -> dict:
        bid = as_uuid(benchmark_id, "benchmark")
        row = c.execute(f"SELECT {bench_cols} FROM benchmarks WHERE benchmark_id = %s", (bid,)).fetchone()
        if not row:
            raise not_found("benchmark", benchmark_id)
        return row

    @app.get("/api/benchmarks/{benchmark_id}", response_model=Benchmark)
    def get_benchmark(benchmark_id: str):
        with pool.conn() as c:
            return benchmark_out(c, fetch_benchmark(c, benchmark_id))

    # ---- 3.4 runs & events ---------------------------------------------------------------------
    @app.get("/api/runs", response_model=Page[Run])
    def list_runs(benchmark_id: str | None = None, agent_id: str | None = None,
                  task_id: str | None = None, scenario: str | None = None,
                  status: str | None = Query(None, pattern="^(PASS|FAIL|INFRA_ERROR)$"),
                  state: str | None = Query(None, pattern="^(queued|running|done)$"),
                  limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
        conds, args = [], []
        if benchmark_id is not None:
            try:
                benchmark_id = str(uuid.UUID(benchmark_id))
            except ValueError:
                raise invalid({"benchmark_id": "not a UUID"}) from None
        for col, val in (("benchmark_id", benchmark_id), ("agent_id", agent_id), ("task_id", task_id),
                         ("scenario", scenario), ("status", status), ("state", state)):
            if val is not None:
                conds.append(f"{col} = %s")
                args.append(val)
        where = ("WHERE " + " AND ".join(conds)) if conds else ""
        with pool.conn() as c:
            total = c.execute(f"SELECT count(*) AS n FROM runs {where}", args).fetchone()["n"]
            rows = c.execute(f"SELECT {RUN_COLS} FROM runs {where}"
                             " ORDER BY started_at DESC NULLS FIRST, run_id LIMIT %s OFFSET %s",
                             [*args, limit, offset]).fetchall()
        return {"items": [run_out(r) for r in rows], "total": total}

    @app.get("/api/runs/{run_id}", response_model=RunDetail)
    def get_run(run_id: str):
        rid = as_uuid(run_id, "run")
        with pool.conn() as c:
            row = c.execute(f"SELECT {RUN_COLS}, env_fingerprint, grader_result, workspace_diff"
                            " FROM runs WHERE run_id = %s", (rid,)).fetchone()
        if not row:
            raise not_found("run", run_id)
        return run_out(row)

    @app.get("/api/runs/{run_id}/events", response_model=Page[Event])
    def list_events(run_id: str, limit: int = Query(200, ge=1, le=1000), offset: int = Query(0, ge=0)):
        rid = as_uuid(run_id, "run")
        with pool.conn() as c:
            if not c.execute("SELECT 1 FROM runs WHERE run_id = %s", (rid,)).fetchone():
                raise not_found("run", run_id)
            total = c.execute("SELECT count(*) AS n FROM events WHERE run_id = %s", (rid,)).fetchone()["n"]
            rows = c.execute("SELECT id, run_id, ts, type, agent_role, payload, latency, error FROM events"
                             " WHERE run_id = %s ORDER BY ts, id LIMIT %s OFFSET %s",
                             (rid, limit, offset)).fetchall()
        return {"items": [{**r, "run_id": str(r["run_id"])} for r in rows], "total": total}

    # ---- 3.5 results / 3.6 resilience ----------------------------------------------------------
    def finished_runs(c, bid: str, *, scenario: str | None = None, agent_ids: list[str] | None = None,
                      category: str | None = None) -> list[dict]:
        conds, args = ["r.benchmark_id = %s", "r.state = 'done'"], [bid]
        if scenario is not None:
            conds.append("r.scenario = %s")
            args.append(scenario)
        if agent_ids:
            conds.append("r.agent_id = ANY(%s)")
            args.append(agent_ids)
        if category:
            conds.append("t.category = %s")
            args.append(category)
        return c.execute(
            "SELECT r.agent_id, r.task_id, r.scenario, r.status, r.cost, r.steps, r.tool_calls,"
            " r.duration, r.cost_confidence FROM runs r JOIN tasks t ON t.task_id = r.task_id"
            " WHERE " + " AND ".join(conds), args).fetchall()

    @app.get("/api/benchmarks/{benchmark_id}/results", response_model=Results)
    def results(benchmark_id: str, group_by: str = Query("agent", pattern="^(agent|agent_task)$"),
                scenario: str = "baseline", agent_ids: str | None = None, category: str | None = None):
        ids = [a.strip() for a in agent_ids.split(",") if a.strip()] if agent_ids else None
        with pool.conn() as c:
            bid = str(fetch_benchmark(c, benchmark_id)["benchmark_id"])
            runs = finished_runs(c, bid, scenario=scenario, agent_ids=ids, category=category)
        groups: dict[tuple, list[dict]] = defaultdict(list)
        for r in runs:
            groups[(r["agent_id"], r["task_id"] if group_by == "agent_task" else None)].append(r)
        rows = [stats.result_row(a, t, scenario, g) for (a, t), g in groups.items()]
        return {"items": stats.sort_rows(rows), "benchmark_id": bid,
                "generated_at": dt.datetime.now(dt.UTC)}

    @app.get("/api/benchmarks/{benchmark_id}/resilience", response_model=Resilience)
    def resilience(benchmark_id: str):
        with pool.conn() as c:
            bid = str(fetch_benchmark(c, benchmark_id)["benchmark_id"])
            runs = finished_runs(c, bid)
        by: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in runs:
            by[(r["agent_id"], r["scenario"])].append(r)

        def rate(group: list[dict]) -> dict:
            counted = [r for r in group if r["status"] in stats.COUNTED]
            return stats.wilson(sum(r["status"] == "PASS" for r in counted), len(counted))

        items = []
        for (agent, sc), group in sorted(by.items()):
            if sc == "baseline":
                continue
            base, scen = rate(by.get((agent, "baseline"), [])), rate(group)
            items.append({"agent_id": agent, "scenario": sc, "baseline_pass_rate": base,
                          "scenario_pass_rate": scen, "resilience_score": stats.resilience_score(base, scen)})
        return {"items": items}

    return app


logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = create_app()
