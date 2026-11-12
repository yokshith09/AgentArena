"""Agent B using the OpenAI Agents SDK with the benchmark's Chat Completions endpoint."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from agents.decorators import tool
from agents.exceptions import ModelBehaviorError, ModelRefusalError, ModelTimeoutError, UserError
from openai import OpenAIError

from agents import (
    Agent,
    AsyncOpenAI,
    OpenAIChatCompletionsModel,
    Runner,
    set_tracing_disabled,
)

MAX_TURNS = 12
MAX_TOOL_OUTPUT = 12_000
REQUEST_TIMEOUT_SECONDS = 30
TEST_TIMEOUT_SECONDS = 60

SYSTEM_PROMPT = """\
You are Agent B, a coding agent working only in the supplied task workspace.
Use read_file to inspect files, write_file to make changes, and run_tests to
execute the workspace's pytest suite. Never request or modify paths outside the
workspace. Continue until the requested task is complete and tests have run.
"""


class AgentError(Exception):
    """Raised when required environment or final output is invalid."""


class ToolError(Exception):
    """Raised when a workspace tool receives invalid input or cannot complete."""


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise AgentError(f"Required environment variable {name} is missing.")
    return value


def _workspace_file(workspace: Path, relative_path: str) -> Path:
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


def _read_file(workspace: Path, relative_path: str) -> str:
    target = _workspace_file(workspace, relative_path)
    try:
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ToolError(f"could not read {relative_path}: {error}") from error
    if len(content) > MAX_TOOL_OUTPUT:
        return content[:MAX_TOOL_OUTPUT] + "\n[truncated]"
    return content


def _write_file(workspace: Path, relative_path: str, content: str) -> dict[str, Any]:
    target = _workspace_file(workspace, relative_path)
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


def _run_tests(workspace: Path) -> dict[str, Any]:
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
            "stdout": _text_output(error.stdout)[:MAX_TOOL_OUTPUT],
            "stderr": _text_output(error.stderr)[:MAX_TOOL_OUTPUT],
        }
    except OSError as error:
        return {"ok": False, "error": f"could not start pytest: {error}"}

    return {
        "ok": result.returncode == 0,
        "timed_out": False,
        "exit_code": result.returncode,
        "stdout": result.stdout[:MAX_TOOL_OUTPUT],
        "stderr": result.stderr[:MAX_TOOL_OUTPUT],
    }


def _tool_error(error: ToolError) -> str:
    return json.dumps({"ok": False, "error": str(error)})


@tool
def read_file(path: str) -> str:
    """Read a UTF-8 file from the task workspace."""
    try:
        return _read_file(Path(_required_env("WORKSPACE")), path)
    except ToolError as error:
        return _tool_error(error)


@tool
def write_file(path: str, content: str) -> str:
    """Write a UTF-8 file inside the task workspace."""
    try:
        result = _write_file(Path(_required_env("WORKSPACE")), path, content)
    except ToolError as error:
        return _tool_error(error)
    return json.dumps(result)


@tool
def run_tests() -> str:
    """Run pytest in the task workspace and return its result."""
    result = _run_tests(Path(_required_env("WORKSPACE")))
    return json.dumps(result)


async def run_agent() -> int:
    task_prompt = _required_env("TASK_PROMPT")
    workspace = Path(_required_env("WORKSPACE")).resolve()
    if not workspace.is_dir():
        raise AgentError("WORKSPACE must point to an existing directory.")

    base_url = _required_env("OPENAI_BASE_URL")
    if not base_url.startswith(("http://", "https://")):
        raise AgentError("OPENAI_BASE_URL must be an HTTP or HTTPS URL.")

    run_id = _required_env("RUN_ID")
    api_key = _required_env("OPENAI_API_KEY")
    model_name = _required_env("ARENA_MODEL")
    set_tracing_disabled(disabled=True)

    async with AsyncOpenAI(
        api_key=api_key,
        base_url=base_url.rstrip("/") + "/",
        default_headers={
            "X-Agent-Role": "agent-b-openai-agents",
            "User-Agent": f"AgentArena/agent-b-openai-agents ({run_id})",
        },
        max_retries=0,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as client:
        model = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
        agent = Agent(
            name="agent-b-openai-agents",
            instructions=SYSTEM_PROMPT,
            model=model,
            tools=[read_file, write_file, run_tests],
        )
        result = await Runner.run(agent, task_prompt, max_turns=MAX_TURNS)

    if not isinstance(result.final_output, str) or not result.final_output.strip():
        raise AgentError("The Agents SDK returned no final response.")
    print(result.final_output)
    return 0


def main() -> int:
    try:
        return asyncio.run(run_agent())
    except (
        AgentError,
        ModelBehaviorError,
        ModelRefusalError,
        ModelTimeoutError,
        OpenAIError,
        UserError,
    ) as error:
        print(f"Agent B error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
