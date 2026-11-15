"""Shapes exchanged with the runner and grader (docs/10 sections 2.1 and 2.3).

The runner (`runner.run.run_agent`) and grader (`grader.grade.grade`) are owned by Dev-C. They
may return these dataclasses, their own objects with the same attribute names, or plain dicts:
`get()` reads any of them, so the orchestrator does not depend on how they are built.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunSpec:
    run_id: str
    agent: dict[str, Any]          # {mode, entrypoint, source_path, model_config}
    task_dir: str                  # absolute path of the task folder (docs/07 section 5)
    fault: dict[str, Any] | None   # runner / agent_env fault definition, else None
    proxy_base_url: str            # e.g. http://localhost:8001 (no trailing slash)
    timeout_s: int = 300


@dataclass
class RunResult:
    exit_code: int | None
    timed_out: bool
    workspace_dir: str
    diff: str = ""
    stdout_tail: str = ""
    stderr_tail: str = ""
    started_at: str | None = None   # ISO-8601
    finished_at: str | None = None
    sandbox_error: str | None = None  # non-null => INFRA_ERROR


@dataclass
class SuiteResult:
    name: str            # "visible" | "hidden"
    passed: bool
    tests_total: int
    tests_failed: int


@dataclass
class GradeResult:
    passed: bool
    tamper_detected: bool
    suites: list[SuiteResult] = field(default_factory=list)
    summary: str = ""
    error: str | None = None  # non-null => grader infrastructure failure => INFRA_ERROR


def get(obj: Any, name: str, default: Any = None) -> Any:
    """Attribute or key access, so dataclasses, other objects and dicts all work."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def to_dict(obj: Any) -> dict[str, Any]:
    """JSON-ready dict of a GradeResult-like object (nested suites included)."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        d = dict(obj)
    else:
        d = {k: getattr(obj, k) for k in ("passed", "tamper_detected", "suites", "summary", "error")
             if hasattr(obj, k)}
    d["suites"] = [s if isinstance(s, dict) else
                   {k: getattr(s, k, None) for k in ("name", "passed", "tests_total", "tests_failed")}
                   for s in (d.get("suites") or [])]
    return d
