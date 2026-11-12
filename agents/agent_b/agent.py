"""Agent B using the OpenAI Agents SDK with the benchmark's Chat Completions endpoint."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
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
REQUEST_TIMEOUT_SECONDS = 30
AGENT_ROLE = "agent-b-openai-agents"

SYSTEM_PROMPT = """\
You are Agent B, a coding agent working only in the supplied task workspace.
Use read_file to inspect files, write_file to make changes, and run_tests to
execute the workspace's pytest suite. Never request or modify paths outside the
workspace. Continue until the requested task is complete and tests have run.
"""


class AgentError(Exception):
    """Raised when required environment or final output is invalid."""


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise AgentError(f"Required environment variable {name} is missing.")
    return value


def _load_shared_tools() -> Any:
    module_name = f"agentarena_{Path(__file__).parent.name}_tools"
    module_path = Path(__file__).resolve().parents[1] / "common" / "tools.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load shared tools from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SHARED_TOOLS = _load_shared_tools()


def _tool_error(error: Exception) -> str:
    return json.dumps({"ok": False, "error": str(error)})


def _create_tools(workspace: Path, fault: Any) -> list[Any]:
    @tool
    def read_file(path: str) -> str:
        """Read a UTF-8 file from the task workspace."""
        try:
            return SHARED_TOOLS.read_file(workspace, path)
        except SHARED_TOOLS.ToolError as error:
            return _tool_error(error)

    @tool
    def write_file(path: str, content: str) -> str:
        """Write a UTF-8 file inside the task workspace."""
        try:
            result = SHARED_TOOLS.write_file(workspace, path, content)
        except SHARED_TOOLS.ToolError as error:
            return _tool_error(error)
        return json.dumps(result)

    @tool
    def run_tests() -> str:
        """Run pytest in the task workspace and return its result."""
        result = SHARED_TOOLS.run_tests(workspace, fault)
        return json.dumps(result)

    return [read_file, write_file, run_tests]


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
    try:
        tool_fault = SHARED_TOOLS.load_tool_fault(os.environ.get("ARENA_TOOL_FAULT", ""))
    except SHARED_TOOLS.ToolError as error:
        raise AgentError(str(error)) from error
    set_tracing_disabled(disabled=True)

    async with AsyncOpenAI(
        api_key=api_key,
        base_url=base_url.rstrip("/") + "/",
        default_headers={
            "X-Agent-Role": AGENT_ROLE,
            "User-Agent": f"AgentArena/{AGENT_ROLE} ({run_id})",
        },
        max_retries=0,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as client:
        model = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
        agent = Agent(
            name=AGENT_ROLE,
            instructions=SYSTEM_PROMPT,
            model=model,
            tools=_create_tools(workspace, tool_fault),
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
