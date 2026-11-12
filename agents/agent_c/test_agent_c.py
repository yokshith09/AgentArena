import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from mock_llm import server


class AgentCTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        (self.workspace / "test_solution.py").write_text(
            "def test_solution():\n    assert 42 == 42\n",
            encoding="utf-8",
        )

        script = self.root / "mock-script.json"
        script.write_text(json.dumps({
            "responses": [
                {"tool_calls": [{"name": "run_tests", "arguments": "{}"}]},
                {"tool_calls": [{"name": "run_tests", "arguments": "{}"}]},
                {"tool_calls": [{"name": "run_tests", "arguments": "{}"}]},
                {"text": "Completed after retrying the test tool."},
            ],
        }), encoding="utf-8")
        self.mock_script_patch = patch.dict(os.environ, {"MOCK_SCRIPT": str(script)})
        self.mock_script_patch.start()
        self.mock_server = server.serve(0)
        self.server_thread = threading.Thread(target=self.mock_server.serve_forever, daemon=True)
        self.server_thread.start()

        self.environment = os.environ.copy()
        self.environment.update({
            "TASK_PROMPT": "Run the workspace tests and report the result.",
            "WORKSPACE": str(self.workspace),
            "OPENAI_BASE_URL": (
                f"http://127.0.0.1:{self.mock_server.server_address[1]}"
                "/runs/00000000-0000-4000-8000-000000000003/v1"
            ),
            "RUN_ID": "00000000-0000-4000-8000-000000000003",
            "OPENAI_API_KEY": "test-key",
            "ARENA_MODEL": "mock-model",
            "ARENA_TOOL_FAULT": json.dumps({
                "tool": "run_tests",
                "fail_first_n": 2,
                "message": "injected test failure",
            }),
        })

    def tearDown(self) -> None:
        self.mock_server.shutdown()
        self.mock_server.server_close()
        self.server_thread.join(timeout=2)
        self.mock_script_patch.stop()
        self.temporary_directory.cleanup()

    def test_agent_c_completes_after_first_two_test_tool_calls_fail(self) -> None:
        agent_path = Path(__file__).with_name("agent.py")
        result = subprocess.run(
            [sys.executable, str(agent_path)],
            cwd=agent_path.parent,
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Completed after retrying", result.stdout)
        self.assertEqual(server.STATE["i"], 4)


if __name__ == "__main__":
    unittest.main()
