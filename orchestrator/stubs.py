"""Stand-in runner and grader (docs/10 section 4: "stubbed Runner/Grader returning canned
results"), used with `python -m orchestrator --stub` until Dev-C's runner and grader land.

The stub runner copies the task's workspace, optionally makes one real chat call through the
proxy (so the proxy writes genuine `llm_call` events, e.g. against mock_llm), and appends a line
to a file so there is a diff. The stub grader passes or fails deterministically from the
workspace path. Neither runs an agent or any tests: results are NOT benchmark data.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

import httpx

from .types import GradeResult, RunResult, RunSpec, SuiteResult, get


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def run_agent(spec: RunSpec) -> RunResult:
    started = _now()
    ws = Path(tempfile.mkdtemp(prefix=f"arena-stub-{spec.run_id[:8]}-"))
    src = Path(spec.task_dir) / "workspace"
    if src.is_dir():
        shutil.copytree(src, ws, dirs_exist_ok=True)
    if os.environ.get("ORCH_STUB_LLM", "1") == "1":
        model = (get(spec.agent, "model_config") or {}).get("model", "mock-model")
        url = f"{spec.proxy_base_url}/runs/{spec.run_id}/v1/chat/completions"
        try:
            httpx.post(url, json={"model": model, "messages": [{"role": "user", "content": "stub run"}]},
                       headers={"Authorization": "Bearer dummy"}, timeout=60)
        except httpx.HTTPError as e:
            return RunResult(exit_code=None, timed_out=False, workspace_dir=str(ws), started_at=started,
                             finished_at=_now(), sandbox_error=f"stub could not reach proxy: {e}")
    (ws / "STUB_EDIT.txt").write_text("edited by the stub runner\n", encoding="utf8")
    diff = "--- /dev/null\n+++ b/STUB_EDIT.txt\n@@ -0,0 +1 @@\n+edited by the stub runner\n"
    return RunResult(exit_code=0, timed_out=False, workspace_dir=str(ws), diff=diff,
                     started_at=started, finished_at=_now())


def grade(task_dir: str, workspace_dir: str) -> GradeResult:
    passed = int(hashlib.sha256(workspace_dir.encode()).hexdigest(), 16) % 2 == 0
    suites = [SuiteResult("visible", passed, 1, 0 if passed else 1),
              SuiteResult("hidden", passed, 1, 0 if passed else 1)]
    return GradeResult(passed=passed, tamper_detected=False, suites=suites,
                       summary="stub grader (not a real test run)")
