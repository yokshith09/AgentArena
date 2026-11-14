"""Workspace tools shared by the reference agents."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

MAX_TOOL_OUTPUT = 12_000
TAIL_HEAD_CHARS = 2_000  # of MAX_TOOL_OUTPUT, kept from the start of long command output
MAX_LISTED_FILES = 500
IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}
TEST_TIMEOUT_SECONDS = 60
DEFAULT_TEMPERATURE = 0.0


class ToolError(Exception):
    """Raised when a workspace tool receives invalid input or cannot complete."""


class ToolFault:
    def __init__(self, tool: str, fail_first_n: int, message: str) -> None:
        self.tool = tool
        self.remaining = fail_first_n
        self.message = message
        self._lock = threading.Lock()

    def take_error(self, tool: str) -> str | None:
        with self._lock:
            if tool != self.tool or self.remaining == 0:
                return None
            self.remaining -= 1
            return self.message


def load_tool_fault(raw_value: str | None) -> ToolFault | None:
    if not raw_value or not raw_value.strip():
        return None
    try:
        params = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise ToolError("ARENA_TOOL_FAULT must contain valid JSON") from error
    if not isinstance(params, dict):
        raise ToolError("ARENA_TOOL_FAULT must contain a JSON object")
    if set(params) != {"tool", "fail_first_n", "message"}:
        raise ToolError("ARENA_TOOL_FAULT must define tool, fail_first_n, and message")

    tool = params["tool"]
    fail_first_n = params["fail_first_n"]
    message = params["message"]
    if tool != "run_tests":
        raise ToolError("ARENA_TOOL_FAULT supports only the run_tests tool")
    if isinstance(fail_first_n, bool) or not isinstance(fail_first_n, int) or fail_first_n < 0:
        raise ToolError("ARENA_TOOL_FAULT fail_first_n must be a non-negative integer")
    if not isinstance(message, str) or not message.strip():
        raise ToolError("ARENA_TOOL_FAULT message must be a non-empty string")
    return ToolFault(tool, fail_first_n, message)


def temperature_from_env(raw_value: str | None) -> float | None:
    """ARENA_TEMPERATURE: unset -> 0.0 (repeatability); empty string -> None (omit the parameter,
    for models that reject it); otherwise a number between 0 and 2."""
    if raw_value is None:
        return DEFAULT_TEMPERATURE
    if not raw_value.strip():
        return None
    try:
        value = float(raw_value)
    except ValueError as error:
        raise ToolError("ARENA_TEMPERATURE must be a number or empty") from error
    if not 0.0 <= value <= 2.0:
        raise ToolError("ARENA_TEMPERATURE must be between 0 and 2")
    return value


def keep_tail(text: str) -> str:
    """Bound command output but keep its END: pytest prints the failure summary last."""
    if len(text) <= MAX_TOOL_OUTPUT:
        return text
    tail_chars = MAX_TOOL_OUTPUT - TAIL_HEAD_CHARS
    omitted = len(text) - MAX_TOOL_OUTPUT
    marker = f"\n[... {omitted} characters omitted ...]\n"
    return text[:TAIL_HEAD_CHARS] + marker + text[-tail_chars:]


def workspace_file(workspace: Path, relative_path: str) -> Path:
    if not relative_path or "\x00" in relative_path or Path(relative_path).is_absolute():
        raise ToolError("path must be a non-empty relative path inside the workspace")

    root = workspace.resolve()
    try:
        target = (root / relative_path).resolve()
        target.relative_to(root)
    except (OSError, RuntimeError, ValueError) as error:
        raise ToolError("path must resolve inside the workspace") from error
    if target == root:
        raise ToolError("path must name a file inside the workspace")
    return target


def read_file(workspace: Path, relative_path: str) -> str:
    target = workspace_file(workspace, relative_path)
    try:
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ToolError(f"could not read {relative_path}: {error}") from error
    if len(content) > MAX_TOOL_OUTPUT:
        return content[:MAX_TOOL_OUTPUT] + "\n[truncated]"
    return content


def list_files(workspace: Path) -> dict[str, Any]:
    root = workspace.resolve()
    files: list[str] = []
    truncated = False
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and not (Path(current) / d).is_symlink())
        for name in sorted(names):
            path = Path(current) / name
            if path.is_symlink():
                continue
            if len(files) >= MAX_LISTED_FILES:
                truncated = True
                break
            files.append(path.relative_to(root).as_posix())
        if truncated:
            break
    return {"ok": True, "files": sorted(files), "truncated": truncated}


def write_file(workspace: Path, relative_path: str, content: str) -> dict[str, Any]:
    target = workspace_file(workspace, relative_path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ToolError(f"could not write {relative_path}: {error}") from error
    return {"ok": True, "path": relative_path}


def _text_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_tests(workspace: Path, fault: ToolFault | None = None) -> dict[str, Any]:
    failure = fault.take_error("run_tests") if fault is not None else None
    if failure is not None:
        return {"ok": False, "timed_out": False, "injected": True, "error": failure}

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=TEST_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "ok": False,
            "timed_out": True,
            "timeout_seconds": TEST_TIMEOUT_SECONDS,
            "stdout": keep_tail(_text_output(error.stdout)),
            "stderr": keep_tail(_text_output(error.stderr)),
        }
    except OSError as error:
        return {"ok": False, "error": f"could not start pytest: {error}"}

    return {
        "ok": result.returncode == 0,
        "timed_out": False,
        "exit_code": result.returncode,
        "stdout": keep_tail(result.stdout),
        "stderr": keep_tail(result.stderr),
    }


def execute_tool(
    workspace: Path,
    name: str,
    arguments: Any,
    fault: ToolFault | None = None,
) -> str:
    if not isinstance(arguments, dict):
        return json.dumps({"ok": False, "error": "tool arguments must be a JSON object"})

    try:
        if name == "read_file":
            path = arguments.get("path")
            if not isinstance(path, str):
                raise ToolError("path must be a string")
            return read_file(workspace, path)
        if name == "write_file":
            path = arguments.get("path")
            content = arguments.get("content")
            if not isinstance(path, str) or not isinstance(content, str):
                raise ToolError("path and content must be strings")
            return json.dumps(write_file(workspace, path, content))
        if name == "list_files":
            return json.dumps(list_files(workspace))
        if name == "run_tests":
            return json.dumps(run_tests(workspace, fault))
        return json.dumps({"ok": False, "error": f"unsupported tool: {name}"})
    except ToolError as error:
        return json.dumps({"ok": False, "error": str(error)})
