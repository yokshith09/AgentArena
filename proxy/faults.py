"""Provider fault injection (A7, F-10). Definitions: faults/*.yaml (docs/07 section 7).

A run whose `scenario` is a provider/proxy fault gets its first `params.first_n` LLM requests
answered by the proxy with `params.status` (503 outage / 429 rate limit) instead of being
forwarded. First-N has no randomness, so the same run_id always sees the same sequence (T-20).
The per-run count is kept in memory and seeded from the run's existing `fault_injected` events,
so a proxy restart mid-run does not inject again.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from starlette.concurrency import run_in_threadpool

log = logging.getLogger("proxy.faults")

GROUPS = {"provider", "tool", "instruction", "environment"}
LAYERS = {"proxy", "agent_env", "runner"}
REQUIRED = ("id", "group", "layer", "description", "params")


class FaultConfigError(ValueError):
    """Invalid fault YAML. Raised at startup so a bad catalog never runs silently."""


@dataclass(frozen=True)
class Fault:
    id: str
    group: str
    layer: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def first_n(self) -> int:
        return int(self.params["first_n"])

    @property
    def status(self) -> int:
        return int(self.params["status"])


def _validate(doc: Any, path: Path) -> Fault:
    if not isinstance(doc, dict):
        raise FaultConfigError(f"{path.name}: not a mapping")
    if missing := [k for k in REQUIRED if k not in doc]:
        raise FaultConfigError(f"{path.name}: missing key(s) {', '.join(missing)}")
    if doc["id"] != path.stem:
        raise FaultConfigError(f"{path.name}: id {doc['id']!r} must match the file name")
    if doc["group"] not in GROUPS:
        raise FaultConfigError(f"{path.name}: group must be one of {sorted(GROUPS)}")
    if doc["layer"] not in LAYERS:
        raise FaultConfigError(f"{path.name}: layer must be one of {sorted(LAYERS)}")
    if not isinstance(doc["params"], dict):
        raise FaultConfigError(f"{path.name}: params must be a mapping")
    fault = Fault(doc["id"], doc["group"], doc["layer"], str(doc["description"]), doc["params"])
    if fault.layer == "proxy":
        if fault.group != "provider":
            raise FaultConfigError(f"{path.name}: proxy-layer faults must be group provider")
        n, status = fault.params.get("first_n"), fault.params.get("status")
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            raise FaultConfigError(f"{path.name}: params.first_n must be an integer >= 1")
        if not isinstance(status, int) or not 400 <= status <= 599:
            raise FaultConfigError(f"{path.name}: params.status must be an HTTP error status (4xx/5xx)")
    return fault


def load_faults(faults_dir: str | Path) -> dict[str, Fault]:
    """Every faults/*.yaml, validated. Raises FaultConfigError on the first problem."""
    out: dict[str, Fault] = {}
    for path in sorted(Path(faults_dir).glob("*.y*ml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf8"))
        except yaml.YAMLError as e:
            raise FaultConfigError(f"{path.name}: invalid YAML: {e}") from e
        fault = _validate(doc, path)
        if fault.id in out:
            raise FaultConfigError(f"{path.name}: duplicate fault id {fault.id!r}")
        out[fault.id] = fault
    return out


@dataclass(frozen=True)
class Injection:
    fault: Fault
    call: int  # 1-based index of this injected call within the run

    @property
    def detail(self) -> str:
        return f"call {self.call} of {self.fault.first_n}"


class ProviderFaults:
    """Decides, per request, whether to inject. Only proxy-layer faults are handled here."""

    def __init__(self, faults: dict[str, Fault], count_existing):
        self.faults = {k: f for k, f in faults.items() if f.layer == "proxy"}
        self._count_existing = count_existing  # (run_id, fault_id) -> int, blocking (DB)
        self._counts: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def next(self, run_id: str, scenario: str | None) -> Injection | None:
        fault = self.faults.get(scenario or "")
        if fault is None:
            return None
        async with self._lock:
            if run_id not in self._counts:
                try:
                    self._counts[run_id] = await run_in_threadpool(self._count_existing, run_id, fault.id)
                except Exception as e:  # noqa: BLE001 - DB trouble must not block; start from 0
                    log.error("run %s: could not read prior injections, assuming 0: %s", run_id, e)
                    self._counts[run_id] = 0
            done = self._counts[run_id]
            if done >= fault.first_n:
                return None
            self._counts[run_id] = done + 1
            return Injection(fault, done + 1)
