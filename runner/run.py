"""Runner (B2, F-03). Contract: docs/10 section 2.1 (RunSpec/RunResult) and 2.2 (agent environment).

run_agent(spec) copies the task workspace to a temp dir, applies a runner-layer fault if the scenario has
one, starts the agent as a black-box subprocess with the documented env vars, enforces a wall-clock
timeout (killing the whole process tree), and returns the final workspace plus a unified diff of what the
AGENT changed (the injected fault is part of the baseline, not of the diff).

This is the subprocess sandbox: isolation = a private temp directory + a minimal environment (no provider
keys). It is NOT a security boundary (no container hardening); see docs/16 and the Limitations page.
The orchestrator owns the lifecycle: call cleanup(result) after grading.
"""
from __future__ import annotations

import datetime as dt
import difflib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CACHE_NAMES = {"__pycache__", ".pytest_cache", ".git", ".hypothesis"}
TAIL_BYTES = 4096
MAX_DIFF_CHARS = 200_000
DEFAULT_TIMEOUT_S = 300
DUMMY_API_KEY = "arena-dummy-key"  # proxy ignores the agent's key (docs/08 section 1.2)
# Only these variables from the orchestrator's environment reach the agent: no provider keys, no DB
# credentials. (Windows needs SYSTEMROOT for Python to start.)
ENV_ALLOWLIST = ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE",
                 "LANG", "LC_ALL", "VIRTUAL_ENV", "PYTHONPATH", "ARENA_TEMPERATURE")


@dataclass
class RunSpec:
    run_id: str
    agent: dict[str, Any]          # {mode, entrypoint, source_path, model_config}
    task_dir: str | Path
    proxy_base_url: str            # e.g. http://localhost:8001 (no trailing slash needed)
    fault: dict[str, Any] | None = None   # {id, group, layer, params} or None
    timeout_s: int = DEFAULT_TIMEOUT_S


@dataclass
class RunResult:
    exit_code: int | None
    timed_out: bool
    workspace_dir: str
    diff: str
    stdout_tail: str
    stderr_tail: str
    started_at: str | None
    finished_at: str | None
    sandbox_error: str | None


def load_fault(fault_id: str, faults_dir: str | Path | None = None) -> dict[str, Any] | None:
    """Fault definition for a scenario id (docs/07 section 7); None for 'baseline'."""
    if fault_id == "baseline":
        return None
    path = Path(faults_dir or ROOT / "faults") / f"{fault_id}.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {"id": doc["id"], "group": doc["group"], "layer": doc["layer"], "params": doc.get("params") or {}}


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _copy_workspace(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*CACHE_NAMES, "*.pyc"))


def apply_instruction_fault(workspace: Path, params: dict[str, Any]) -> None:
    """Instruction-group fault (docs/03 F-10): misleading text added to a workspace file.
    params: file (relative path), and `prepend` and/or `append` text."""
    rel = params.get("file")
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ValueError("instruction fault needs a relative `file` inside the workspace")
    target = workspace / rel
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    new = f"{params.get('prepend', '')}{existing}{params.get('append', '')}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new, encoding="utf-8")


def _agent_env(spec: RunSpec, workspace: Path, prompt: str, tool_fault: str) -> dict[str, str]:
    env = {k: os.environ[k] for k in ENV_ALLOWLIST if k in os.environ}
    base = spec.proxy_base_url.rstrip("/")
    env.update({
        "TASK_PROMPT": prompt,
        "WORKSPACE": str(workspace),
        "OPENAI_BASE_URL": f"{base}/runs/{spec.run_id}/v1",
        "RUN_ID": spec.run_id,
        "OPENAI_API_KEY": DUMMY_API_KEY,
        "ARENA_TOOL_FAULT": tool_fault,
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    model = (spec.agent.get("model_config") or {}).get("model")
    if model:
        env["ARENA_MODEL"] = str(model)
    return env


def _kill_tree(proc: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, check=False)
        else:
            import signal
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass
    try:
        proc.kill()
    except OSError:
        pass


def _tail(path: Path) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    return data[-TAIL_BYTES:].decode("utf-8", errors="replace")


def _text_files(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in CACHE_NAMES)
        for name in sorted(names):
            path = Path(current) / name
            if name.endswith(".pyc"):
                continue
            try:
                out[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                out[path.relative_to(root).as_posix()] = "<binary or unreadable file>\n"
    return out


def workspace_diff(before: Path, after: Path) -> str:
    """Unified diff of text files; truncated at MAX_DIFF_CHARS."""
    a, b = _text_files(before), _text_files(after)
    chunks = []
    for name in sorted(set(a) | set(b)):
        if a.get(name) == b.get(name):
            continue
        chunks.extend(difflib.unified_diff(
            a.get(name, "").splitlines(keepends=True), b.get(name, "").splitlines(keepends=True),
            fromfile=f"a/{name}" if name in a else "/dev/null",
            tofile=f"b/{name}" if name in b else "/dev/null"))
        if chunks and not chunks[-1].endswith("\n"):
            chunks.append("\n")
    text = "".join(chunks)
    if len(text) > MAX_DIFF_CHARS:
        text = text[:MAX_DIFF_CHARS] + "\n[diff truncated]\n"
    return text


def _fail(work: Path | None, message: str) -> RunResult:
    return RunResult(exit_code=None, timed_out=False, workspace_dir=str(work / "workspace") if work else "",
                     diff="", stdout_tail="", stderr_tail="", started_at=None, finished_at=None,
                     sandbox_error=message)


def run_agent(spec: RunSpec) -> RunResult:
    """Run one agent on one task. Never raises: setup problems become `sandbox_error` (-> INFRA_ERROR)."""
    work: Path | None = None
    try:
        agent = spec.agent
        if agent.get("mode") != "command":
            return _fail(None, f"unsupported agent mode {agent.get('mode')!r} (only 'command' is implemented)")
        task = Path(spec.task_dir)
        if not (task / "workspace").is_dir() or not (task / "prompt.md").is_file():
            return _fail(None, f"task folder incomplete: {task}")
        source = Path(agent["source_path"])
        source = source if source.is_absolute() else ROOT / source
        if not source.is_dir():
            return _fail(None, f"agent source_path not found: {source}")
        argv = shlex.split(agent["entrypoint"])
        if not argv:
            return _fail(None, "agent entrypoint is empty")
        if argv[0] in ("python", "python3"):
            argv[0] = sys.executable  # same interpreter and packages as the orchestrator

        work = Path(tempfile.mkdtemp(prefix="arena-run-"))
        workspace = work / "workspace"
        _copy_workspace(task / "workspace", workspace)

        fault, tool_fault = spec.fault, ""
        if fault and fault.get("layer") == "runner":
            if fault.get("group") != "instruction":
                return _fail(work, f"unsupported runner fault group {fault.get('group')!r}")
            apply_instruction_fault(workspace, fault.get("params") or {})
        elif fault and fault.get("layer") == "agent_env":
            tool_fault = json.dumps(fault.get("params") or {})
        baseline = work / "baseline"
        _copy_workspace(workspace, baseline)  # snapshot AFTER the fault: diff shows only the agent's edits

        prompt = (task / "prompt.md").read_text(encoding="utf-8").strip()
        env = _agent_env(spec, workspace, prompt, tool_fault)
        out_path, err_path = work / "stdout.txt", work / "stderr.txt"
        popen_kwargs: dict[str, Any] = {}
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True
    except (OSError, ValueError, KeyError, yaml.YAMLError) as error:
        return _fail(work, f"setup failed: {error}")

    started = _now()
    timed_out = False
    exit_code: int | None = None
    try:
        with open(out_path, "wb") as out, open(err_path, "wb") as err:
            proc = subprocess.Popen(argv, cwd=source, env=env, stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                                    **popen_kwargs)
            try:
                exit_code = proc.wait(timeout=spec.timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_tree(proc)
                proc.wait()
    except OSError as error:
        return _fail(work, f"could not start the agent: {error}")
    finished = _now()

    return RunResult(
        exit_code=None if timed_out else exit_code, timed_out=timed_out, workspace_dir=str(workspace),
        diff=workspace_diff(baseline, workspace), stdout_tail=_tail(out_path), stderr_tail=_tail(err_path),
        started_at=started, finished_at=finished, sandbox_error=None)


def cleanup(result: RunResult) -> None:
    """Delete the run's temp dir (the parent of workspace_dir). Call after grading."""
    if result.workspace_dir:
        shutil.rmtree(Path(result.workspace_dir).parent, ignore_errors=True)
