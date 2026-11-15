"""Benchmark orchestrator (B5 + B6; docs/03 F-06, docs/10 section 2.5).

Single writer of `runs`. Also writes the orchestrator-owned events: `agent_started`,
`grader_result`, and `fault_injected` for runner / agent_env faults (the proxy writes the
proxy-layer ones). Per benchmark:

1. claim a queued benchmark (or resume a running one) -> state 'running'
2. expand agents x tasks x scenarios x repeats into `runs` rows (idempotent, attempt 1)
3. execute queued runs with bounded parallelism: set 'running' BEFORE the agent starts (the
   proxy 404s otherwise), call run_agent, then grade, then finalise the row from its events
4. classify PASS / FAIL / INFRA_ERROR; INFRA_ERROR gets a new attempt, at most 3
5. after each run, stop scheduling once spend >= spend_cap_usd ('halted_spend_cap')
6. 'completed' when every slot is resolved

Restart: runs left 'running' by a dead orchestrator become INFRA_ERROR ("orchestrator
restarted") and get a new attempt, so their real spend and trace are kept rather than reused.
"""
from __future__ import annotations

import datetime as dt
import logging
import platform
import shutil
import threading
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
import yaml
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .seed import ROOT, dir_hash
from .types import RunSpec, get, to_dict

log = logging.getLogger("orchestrator")
MAX_ATTEMPTS = 3
DIFF_LIMIT = 200 * 1024  # docs/07: workspace_diff truncated at 200 KB
RUN_COLS = "run_id, benchmark_id, agent_id, task_id, scenario, repeat_index, attempt"


@dataclass
class Config:
    dsn: str = ""
    proxy_base_url: str = "http://localhost:8001"
    parallel: int = 2
    timeout_s: int = 300
    settle_s: float = 1.5     # wait for in-flight proxy event writes (docs/10 section 2.5: <= 2 s)
    poll_s: float = 2.0
    min_interval_s: float = 0.0  # minimum seconds between run starts (provider tokens/minute limits)
    faults_dir: Path = ROOT / "faults"
    pricing_file: Path = ROOT / "pricing.yaml"
    root: Path = ROOT          # task_dir / source_path in the DB are relative to this


@dataclass
class Outcome:
    status: str
    error: str | None = None


@dataclass
class Metrics:
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost: float | None = None
    cost_confidence: str | None = None
    steps: int = 0
    tool_calls: int = 0
    upstream_unrecovered: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


# ---- pure helpers (unit-tested) -------------------------------------------------------------
def aggregate(events: list[dict]) -> Metrics:
    """docs/07 section 4: run metrics from its events, in id order."""
    m = Metrics()
    llm = [e for e in events if e["type"] == "llm_call"]
    ok = [e for e in llm if 200 <= int((e["payload"] or {}).get("status_code") or 0) < 300]
    m.steps = len(ok)
    m.tool_calls = sum(1 for e in events if e["type"] == "tool_call")
    if ok:
        m.model = ok[0]["payload"].get("model")
    tin = [e["payload"].get("tokens_in") for e in llm if e["payload"].get("tokens_in") is not None]
    tout = [e["payload"].get("tokens_out") for e in llm if e["payload"].get("tokens_out") is not None]
    costs = [e["payload"].get("cost") for e in llm if e["payload"].get("cost") is not None]
    m.tokens_in = sum(tin) if tin else None
    m.tokens_out = sum(tout) if tout else None
    m.cost = round(sum(float(c) for c in costs), 6) if costs else None
    confs = [e["payload"].get("cost_confidence") for e in llm if e["payload"].get("cost_confidence")]
    m.cost_confidence = ("estimated" if "estimated" in confs else "verified") if confs else None
    # F-06 step 5: a real upstream failure counts only if the agent never succeeded after it.
    last_upstream = max((e["id"] for e in llm if e.get("error") == "upstream"), default=None)
    m.upstream_unrecovered = last_upstream is not None and not any(e["id"] > last_upstream for e in ok)
    return m


def classify(result: Any, grade: Any, grade_error: str | None, metrics: Metrics) -> Outcome:
    """F-06 step 5 (D-03). Injected faults never make INFRA_ERROR: only error='upstream' counts.

    `grade_error` is a grader *infrastructure* failure: the grader raised (GraderInfraError, CLI
    exit 2). `GradeResult.error` is different: test-level problems the agent caused (a suite timed
    out or collected no tests); those are FAIL, with the message kept on the run."""
    sandbox_error = get(result, "sandbox_error") if result is not None else "runner returned nothing"
    if sandbox_error:
        return Outcome("INFRA_ERROR", f"runner: {sandbox_error}")
    if grade_error:
        return Outcome("INFRA_ERROR", f"grader: {grade_error}")
    if metrics.upstream_unrecovered:
        return Outcome("INFRA_ERROR", "upstream LLM failure with no successful call afterwards")
    if get(result, "timed_out"):
        return Outcome("FAIL", "agent timed out")
    if get(grade, "tamper_detected"):
        return Outcome("FAIL", "tamper detected: protected files were modified")
    if get(result, "exit_code") not in (0, None) and not (get(result, "diff") or "").strip():
        return Outcome("FAIL", f"agent exited {get(result, 'exit_code')} without changing the workspace")
    if get(grade, "passed"):
        return Outcome("PASS")
    detail = "; ".join(x for x in (get(grade, "summary"), get(grade, "error")) if x)
    return Outcome("FAIL", detail or "tests failed")


def _seconds(start: Any, end: Any) -> float | None:
    def parse(v):
        if v is None or isinstance(v, dt.datetime):
            return v
        return dt.datetime.fromisoformat(str(v))
    a, b = parse(start), parse(end)
    return round((b - a).total_seconds(), 3) if a and b else None


# ---- orchestrator ---------------------------------------------------------------------------
class Orchestrator:
    def __init__(self, config: Config, run_agent: Callable[[RunSpec], Any],
                 grade: Callable[[str, str], Any], cleanup: Callable[[Any], None] | None = None):
        self.cfg = config
        self.run_agent = run_agent
        self.grade = grade
        self.cleanup = cleanup  # runner.run.cleanup: deletes the run's whole temp dir
        self._stop = threading.Event()
        self._last_start = 0.0
        self.faults = self._load_faults()
        self.pricing_version = str((yaml.safe_load(config.pricing_file.read_text(encoding="utf8"))
                                    or {}).get("version")) if config.pricing_file.exists() else None

    def _load_faults(self) -> dict[str, dict]:
        from proxy.faults import load_faults  # same validation as the proxy (fails fast)
        return {k: {"id": f.id, "group": f.group, "layer": f.layer, "description": f.description,
                    "params": f.params} for k, f in load_faults(self.cfg.faults_dir).items()}

    def connect(self) -> psycopg.Connection:
        return psycopg.connect(self.cfg.dsn, autocommit=True, row_factory=dict_row,
                               options="-c timezone=UTC")

    def stop(self) -> None:
        self._stop.set()

    # -- entry points --
    def recover(self) -> int:
        """Runs left 'running' by a dead orchestrator -> INFRA_ERROR + new attempt."""
        with self.connect() as c:
            orphans = c.execute(
                f"UPDATE runs SET state = 'done', status = 'INFRA_ERROR', passed = NULL, finished_at = now(),"
                f" error = 'orchestrator restarted while the run was in progress'"
                f" WHERE state = 'running' AND benchmark_id IS NOT NULL RETURNING {RUN_COLS}").fetchall()
            for r in orphans:
                self._retry(c, r)
        if orphans:
            log.warning("recovered %d run(s) interrupted by a restart", len(orphans))
        return len(orphans)

    def run_once(self) -> int:
        """Process benchmarks until none is queued or running. Returns how many were processed."""
        self.recover()
        n = 0
        while not self._stop.is_set() and (b := self.claim()) is not None:
            self.process(b)
            n += 1
        return n

    def serve(self) -> None:
        log.info("orchestrator polling every %.1fs (parallel=%d, proxy=%s)",
                 self.cfg.poll_s, self.cfg.parallel, self.cfg.proxy_base_url)
        self.recover()
        while not self._stop.is_set():
            try:
                b = self.claim()
            except psycopg.OperationalError as e:  # F-06: DB down -> back off and retry
                log.error("database unavailable, retrying: %s", e)
                self._stop.wait(5)
                continue
            if b is None:
                self._stop.wait(self.cfg.poll_s)
            else:
                self.process(b)

    # -- benchmark level --
    def claim(self) -> dict | None:
        with self.connect() as c:
            row = c.execute("SELECT * FROM benchmarks WHERE state = 'running' ORDER BY started_at LIMIT 1").fetchone()
            if row:
                return row
            return c.execute(
                "UPDATE benchmarks SET state = 'running', started_at = coalesce(started_at, now())"
                " WHERE benchmark_id = (SELECT benchmark_id FROM benchmarks WHERE state = 'queued'"
                " ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING *").fetchone()

    def process(self, bench: dict) -> str:
        bid, cfg = str(bench["benchmark_id"]), bench["config"] or {}
        log.info("benchmark %s (%s): start", bid, bench["name"])
        with self.connect() as c:
            problem = self._check_config(c, cfg)
            if problem:
                self._finish(c, bid, "failed", problem)
                log.error("benchmark %s failed: %s", bid, problem)
                return "failed"
            self._expand(c, bid, cfg)
        cap = float(cfg.get("spend_cap_usd") or 0) or None
        in_flight: set[Future] = set()
        halted = False
        with ThreadPoolExecutor(max_workers=self.cfg.parallel, thread_name_prefix="run") as pool:
            while not self._stop.is_set():
                if not halted and cap is not None and self._spend(bid) >= cap:
                    halted = True
                    log.warning("benchmark %s: spend cap $%.4f reached; no new runs", bid, cap)
                while not halted and len(in_flight) < self.cfg.parallel:
                    if self._pace():
                        break  # stop requested while waiting
                    run = self._claim_run(bid)
                    if run is None:
                        break
                    in_flight.add(pool.submit(self._execute_safely, run))
                if not in_flight:
                    break
                done, in_flight = wait(in_flight, return_when=FIRST_COMPLETED)
                for f in done:
                    f.result()
        if self._stop.is_set():
            log.info("benchmark %s: stopped; it resumes on the next start", bid)
            return "running"
        state = "halted_spend_cap" if halted else "completed"
        with self.connect() as c:
            self._finish(c, bid, state, None)
        log.info("benchmark %s: %s (spend $%.6f)", bid, state, self._spend(bid))
        return state

    def _pace(self) -> bool:
        """Wait until min_interval_s has passed since the last run start. True if stopped meanwhile."""
        wait_s = self._last_start + self.cfg.min_interval_s - time.monotonic()
        if wait_s > 0 and self._stop.wait(wait_s):
            return True
        self._last_start = time.monotonic()
        return False

    def _check_config(self, c, cfg: dict) -> str | None:
        for key in ("agent_ids", "task_ids", "n_runs"):
            if not cfg.get(key):
                return f"config is missing {key}"
        agents = {r["agent_id"] for r in c.execute("SELECT agent_id FROM agents WHERE agent_id = ANY(%s)",
                                                   (cfg["agent_ids"],))}
        tasks = {r["task_id"] for r in c.execute("SELECT task_id FROM tasks WHERE task_id = ANY(%s)",
                                                 (cfg["task_ids"],))}
        missing = [a for a in cfg["agent_ids"] if a not in agents] + [t for t in cfg["task_ids"] if t not in tasks]
        if missing:
            return "unknown agent/task id(s): " + ", ".join(missing)
        unknown = [s for s in cfg.get("scenarios") or ["baseline"] if s != "baseline" and s not in self.faults]
        return ("unknown scenario(s): " + ", ".join(unknown)) if unknown else None

    def _expand(self, c, bid: str, cfg: dict) -> None:
        rows = [(bid, a, t, s, r) for a in cfg["agent_ids"] for t in cfg["task_ids"]
                for s in cfg.get("scenarios") or ["baseline"] for r in range(1, int(cfg["n_runs"]) + 1)]
        with c.cursor() as cur:
            cur.executemany("INSERT INTO runs (benchmark_id, agent_id, task_id, scenario, repeat_index, attempt,"
                            " state) VALUES (%s, %s, %s, %s, %s, 1, 'queued') ON CONFLICT DO NOTHING", rows)

    def _claim_run(self, bid: str) -> dict | None:
        with self.connect() as c:
            return c.execute(
                f"UPDATE runs SET state = 'running', started_at = now() WHERE run_id = (SELECT run_id FROM runs"
                f" WHERE benchmark_id = %s AND state = 'queued' ORDER BY repeat_index, attempt, agent_id, task_id,"
                f" scenario LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING {RUN_COLS}", (bid,)).fetchone()

    def _spend(self, bid: str) -> float:
        with self.connect() as c:
            return float(c.execute("SELECT coalesce(sum(cost), 0) AS s FROM runs WHERE benchmark_id = %s",
                                   (bid,)).fetchone()["s"])

    def _finish(self, c, bid: str, state: str, error: str | None) -> None:
        c.execute("UPDATE benchmarks SET state = %s, error = %s, finished_at = now() WHERE benchmark_id = %s",
                  (state, error, bid))

    # -- run level --
    def _execute_safely(self, run: dict) -> None:
        try:
            self.execute(run)
        except Exception as e:  # one broken run must not stop the benchmark (logged below)
            log.exception("run %s: orchestrator error", run["run_id"])
            with self.connect() as c:
                c.execute("UPDATE runs SET state = 'done', status = 'INFRA_ERROR', passed = NULL,"
                          " finished_at = now(), error = %s WHERE run_id = %s AND state = 'running'",
                          (f"orchestrator: {type(e).__name__}: {e}", run["run_id"]))
                self._retry(c, run)

    def execute(self, run: dict) -> Outcome:
        rid = str(run["run_id"])
        with self.connect() as c:
            agent = c.execute("SELECT * FROM agents WHERE agent_id = %s", (run["agent_id"],)).fetchone()
            task = c.execute("SELECT * FROM tasks WHERE task_id = %s", (run["task_id"],)).fetchone()
        task_dir = (self.cfg.root / task["task_dir"]).resolve()
        agent_dir = (self.cfg.root / agent["source_path"]).resolve()
        fault = self.faults.get(run["scenario"])
        local_fault = fault if fault and fault["layer"] in ("runner", "agent_env") else None
        fingerprint = {
            "model": (agent["model_config"] or {}).get("model"), "date": dt.date.today().isoformat(),
            "task_hash": task["task_hash"], "pricing_version": self.pricing_version,
            "agent_source_hash": dir_hash(agent_dir) if agent_dir.is_dir() else None,
            "python": platform.python_version(), "image_digest": None,
        }
        with self.connect() as c:
            c.execute("UPDATE runs SET env_fingerprint = %s WHERE run_id = %s", (Jsonb(fingerprint), rid))
            self._event(c, rid, "agent_started", {"task_id": run["task_id"]})
            if local_fault:
                self._event(c, rid, "fault_injected", {
                    "fault_id": local_fault["id"], "group": local_fault["group"],
                    "detail": "applied by the runner" if local_fault["layer"] == "runner"
                    else "passed to the agent via ARENA_TOOL_FAULT"})

        spec = RunSpec(run_id=rid, agent={"mode": agent["mode"], "entrypoint": agent["entrypoint"],
                                          "source_path": str(agent_dir), "model_config": agent["model_config"]},
                       task_dir=str(task_dir), fault=local_fault,
                       proxy_base_url=self.cfg.proxy_base_url.rstrip("/"), timeout_s=self.cfg.timeout_s)
        try:
            result = self.run_agent(spec)
        except Exception as e:  # noqa: BLE001 - runner crash is an infrastructure error
            result = {"sandbox_error": f"{type(e).__name__}: {e}"}

        grade = grade_error = None
        if not get(result, "sandbox_error") and get(result, "workspace_dir"):
            try:
                grade = self.grade(str(task_dir), str(get(result, "workspace_dir")))
            except Exception as e:  # noqa: BLE001 - grader raised = infrastructure failure (exit 2)
                grade_error = f"{type(e).__name__}: {e}"
        if grade is not None:
            with self.connect() as c:
                self._event(c, rid, "grader_result", {"passed": bool(get(grade, "passed")),
                                                      "suite_count": len(get(grade, "suites") or [])})
        self._release(result)

        if self.cfg.settle_s:
            time.sleep(self.cfg.settle_s)  # let the proxy finish writing in-flight events
        with self.connect() as c:
            events = c.execute("SELECT id, type, payload, error FROM events WHERE run_id = %s ORDER BY id",
                               (rid,)).fetchall()
            m = aggregate(events)
            outcome = classify(result, grade, grade_error, m)
            diff = get(result, "diff") or ""
            c.execute(
                "UPDATE runs SET state = 'done', status = %s, passed = %s, model = coalesce(%s, model),"
                " tokens_in = %s, tokens_out = %s, cost = %s, cost_confidence = %s, duration = %s, steps = %s,"
                " tool_calls = %s, finished_at = now(), grader_result = %s, workspace_diff = %s, error = %s"
                " WHERE run_id = %s",
                (outcome.status, None if outcome.status == "INFRA_ERROR" else outcome.status == "PASS",
                 m.model or fingerprint["model"], m.tokens_in, m.tokens_out, m.cost, m.cost_confidence,
                 _seconds(get(result, "started_at"), get(result, "finished_at")), m.steps, m.tool_calls,
                 Jsonb(to_dict(grade)) if grade is not None else None, diff[:DIFF_LIMIT] or None,
                 outcome.error, rid))
            if outcome.status == "INFRA_ERROR":
                self._retry(c, run)
        log.info("run %s %s/%s/%s r%d a%d: %s%s", rid[:8], run["agent_id"], run["task_id"], run["scenario"],
                 run["repeat_index"], run["attempt"], outcome.status,
                 f" ({outcome.error})" if outcome.error else "")
        return outcome

    def _release(self, result: Any) -> None:
        """After grading (doc 10 2.1): the runner's cleanup() if given, else delete workspace_dir."""
        if self.cleanup is not None and not isinstance(result, dict):
            try:
                self.cleanup(result)
                return
            except Exception:  # fall back to deleting the workspace ourselves
                log.warning("runner cleanup failed; deleting the workspace directly", exc_info=True)
        ws = get(result, "workspace_dir")
        if ws:
            shutil.rmtree(ws, ignore_errors=True)

    def _retry(self, c, run: dict) -> None:
        if run["attempt"] >= MAX_ATTEMPTS:
            log.warning("run slot %s/%s/%s r%d excluded after %d INFRA_ERROR attempts", run["agent_id"],
                        run["task_id"], run["scenario"], run["repeat_index"], MAX_ATTEMPTS)
            return
        c.execute("INSERT INTO runs (benchmark_id, agent_id, task_id, scenario, repeat_index, attempt, state)"
                  " VALUES (%s, %s, %s, %s, %s, %s, 'queued') ON CONFLICT DO NOTHING",
                  (run["benchmark_id"], run["agent_id"], run["task_id"], run["scenario"],
                   run["repeat_index"], run["attempt"] + 1))

    @staticmethod
    def _event(c, rid: str, type_: str, payload: dict) -> None:
        c.execute("INSERT INTO events (run_id, type, payload) VALUES (%s, %s, %s)", (rid, type_, Jsonb(payload)))
