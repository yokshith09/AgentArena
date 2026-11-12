"""Framework-free Agent A using the OpenAI-compatible chat-completions API."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MAX_TURNS = 12
MAX_TOOL_OUTPUT = 12_000
REQUEST_TIMEOUT_SECONDS = 30
TEST_TIMEOUT_SECONDS = 60

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
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as error:
        raise ToolError("path must stay inside the workspace") from error
    if target == root:
        raise ToolError("path must name a file inside the workspace")
    return target


def read_file(workspace: Path, relative_path: str) -> str:
    target = _workspace_file(workspace, relative_path)
    try:
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ToolError(f"could not read {relative_path}: {error}") from error
    if len(content) > MAX_TOOL_OUTPUT:
        return content[:MAX_TOOL_OUTPUT] + "\n[truncated]"
    return content


def write_file(workspace: Path, relative_path: str, content: str) -> dict[str, Any]:
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


def run_tests(workspace: Path) -> dict[str, Any]:
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


def _execute_tool(workspace: Path, name: str, arguments: Any) -> str:
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
        if name == "run_tests":
            return json.dumps(run_tests(workspace))
        return json.dumps({"ok": False, "error": f"unsupported tool: {name}"})
    except ToolError as error:
        return json.dumps({"ok": False, "error": str(error)})


def _request_completion(
    base_url: str,
    api_key: str,
    run_id: str,
    model: str,
    messages: list[dict[str, Any]],
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
            "X-Agent-Role": "agent-a-plain",
            "User-Agent": f"AgentArena/agent-a-plain ({run_id})",
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


def _tool_result(workspace: Path, call: Any) -> dict[str, str]:
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
        content = _execute_tool(workspace, name, arguments)
    return {"role": "tool", "tool_call_id": call_id, "content": content}


def run_agent() -> int:
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
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task_prompt},
    ]

    for _ in range(MAX_TURNS):
        message = _request_completion(
            base_url, api_key, run_id, model, messages,
        )
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            messages.append(message)
            messages.extend(_tool_result(workspace, call) for call in tool_calls)
            continue

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise AgentError("LLM returned neither tool calls nor a final response.")
        print(content)
        return 0

    raise AgentError(f"Agent exceeded the maximum of {MAX_TURNS} model turns.")


def main() -> int:
    try:
        return run_agent()
    except AgentError as error:
        print(f"Agent error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
