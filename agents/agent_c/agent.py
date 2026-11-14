"""Agent C: Agent A's minimal loop plus resilience: code-level retry of transient LLM errors
(429/5xx/timeouts, honouring Retry-After) and a test-retry-focused prompt."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

AGENT_ROLE = "agent-c-test-retry"
LLM_RETRIES = 3  # extra attempts after the first, on 429/5xx/connection/timeout
SYSTEM_PROMPT = """\
You are Agent C, a coding agent working only in the supplied task workspace.
Use list_files to see the workspace, read_file to inspect files, write_file to make changes, and run_tests to
execute the workspace's pytest suite. Never request or modify paths outside the
workspace. If run_tests returns an error, inspect the result and retry it up to
two more times before deciding how to proceed. Transient model/network errors are
retried automatically for you.
Continue until the requested task is complete and tests have run.
"""


def _load_agent_a() -> Any:
    agent_path = Path(__file__).resolve().parents[1] / "agent_a" / "agent.py"
    spec = importlib.util.spec_from_file_location("agentarena_agent_c_loop", agent_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load Agent A loop from {agent_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AGENT_A = _load_agent_a()


def main() -> int:
    return AGENT_A.main(SYSTEM_PROMPT, AGENT_ROLE, LLM_RETRIES)


if __name__ == "__main__":
    raise SystemExit(main())
