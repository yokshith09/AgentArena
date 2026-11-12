"""Framework-free Agent A using the OpenAI-compatible chat-completions API."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MAX_TURNS = 12
REQUEST_TIMEOUT_SECONDS = 30
AGENT_ROLE = "agent-a-plain"

SYSTEM_PROMPT = """\
You are Agent A, a coding agent working only in the supplied task workspace.
Use read_file to inspect files, write_file to make changes, and run_tests to
execute the workspace's pytest suite. Never request or modify paths outside the
workspace. Continue until the requested task is complete and tests have run.
"""

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 file from the task workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a UTF-8 file inside the task workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run pytest in the task workspace.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
]


class AgentError(Exception):
    """Raised when the agent cannot continue safely or communicate with the model."""


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


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise AgentError(f"Required environment variable {name} is missing.")
    return value


def _request_completion(
    base_url: str,
    api_key: str,
    run_id: str,
    model: str,
    messages: list[dict[str, Any]],
    agent_role: str,
) -> dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
    }).encode("utf-8")
    request = Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Agent-Role": agent_role,
            "User-Agent": f"AgentArena/{agent_role} ({run_id})",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            response_body = response.read()
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")[:2_000]
        raise AgentError(f"LLM endpoint returned HTTP {error.code}: {details}") from error
    except URLError as error:
        raise AgentError(f"LLM endpoint request failed: {error.reason}") from error
    except TimeoutError as error:
        raise AgentError("LLM endpoint request timed out.") from error

    try:
        data = json.loads(response_body)
    except (json.JSONDecodeError, UnicodeError) as error:
        raise AgentError("LLM endpoint returned invalid JSON.") from error

    choices = data.get("choices") if isinstance(data, dict) else None
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise AgentError("LLM endpoint response has no completion choice.")
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        raise AgentError("LLM endpoint response has no assistant message.")
    return message


def _tool_result(
    workspace: Path,
    call: Any,
    fault: Any,
) -> dict[str, str]:
    if not isinstance(call, dict):
        raise AgentError("LLM returned a malformed tool call.")
    call_id = call.get("id")
    function = call.get("function")
    if not isinstance(call_id, str) or not isinstance(function, dict):
        raise AgentError("LLM returned a tool call without an id or function.")

    name = function.get("name")
    raw_arguments = function.get("arguments", "{}")
    if not isinstance(name, str) or not isinstance(raw_arguments, str):
        raise AgentError("LLM returned malformed tool-call fields.")
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        content = json.dumps({"ok": False, "error": "tool arguments are not valid JSON"})
    else:
        content = SHARED_TOOLS.execute_tool(workspace, name, arguments, fault)
    return {"role": "tool", "tool_call_id": call_id, "content": content}


def run_agent(
    system_prompt: str = SYSTEM_PROMPT,
    agent_role: str = AGENT_ROLE,
) -> int:
    task_prompt = _required_env("TASK_PROMPT")
    workspace = Path(_required_env("WORKSPACE")).resolve()
    if not workspace.is_dir():
        raise AgentError("WORKSPACE must point to an existing directory.")

    base_url = _required_env("OPENAI_BASE_URL")
    if not base_url.startswith(("http://", "https://")):
        raise AgentError("OPENAI_BASE_URL must be an HTTP or HTTPS URL.")

    run_id = _required_env("RUN_ID")
    api_key = _required_env("OPENAI_API_KEY")
    model = _required_env("ARENA_MODEL")
    try:
        tool_fault = SHARED_TOOLS.load_tool_fault(os.environ.get("ARENA_TOOL_FAULT", ""))
    except SHARED_TOOLS.ToolError as error:
        raise AgentError(str(error)) from error
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task_prompt},
    ]

    for _ in range(MAX_TURNS):
        message = _request_completion(
            base_url, api_key, run_id, model, messages, agent_role,
        )
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            messages.append(message)
            messages.extend(_tool_result(workspace, call, tool_fault) for call in tool_calls)
            continue

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise AgentError("LLM returned neither tool calls nor a final response.")
        print(content)
        return 0

    raise AgentError(f"Agent exceeded the maximum of {MAX_TURNS} model turns.")


def main(
    system_prompt: str = SYSTEM_PROMPT,
    agent_role: str = AGENT_ROLE,
) -> int:
    try:
        return run_agent(system_prompt, agent_role)
    except AgentError as error:
        print(f"Agent error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
