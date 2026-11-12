import importlib.util
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

agent_spec = importlib.util.spec_from_file_location(
    "agent_a_under_test",
    Path(__file__).with_name("agent.py"),
)
if agent_spec is None or agent_spec.loader is None:
    raise ImportError("could not load Agent A source for tests")
agent_module = importlib.util.module_from_spec(agent_spec)
sys.modules[agent_spec.name] = agent_module
agent_spec.loader.exec_module(agent_module)
ToolError = agent_module.ToolError
_workspace_file = agent_module._workspace_file
run_tests = agent_module.run_tests


class AgentATests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        (self.workspace / "solution.py").write_text(
            "def solve():\n    return 42\n",
            encoding="utf-8",
        )
        (self.workspace / "test_solution.py").write_text(
            "from solution import solve\n\n\ndef test_solve():\n    assert solve() == 42\n",
            encoding="utf-8",
        )

        script = self.root / "mock-script.json"
        script.write_text(json.dumps({
            "responses": [
                {
                    "tool_calls": [
                        {
                            "name": "write_file",
                            "arguments": json.dumps({
                                "path": "solution.py",
                                "content": "def solve():\n    return 42\n",
                            }),
                        },
                    ],
                },
                {"tool_calls": [{"name": "run_tests", "arguments": "{}"}]},
                {"text": "Completed the task and ran the tests."},
            ],
        }), encoding="utf-8")
        self.mock_script_patch = patch.dict(os.environ, {"MOCK_SCRIPT": str(script)})
        self.mock_script_patch.start()
        self.mock_server = server.serve(0)
        self.server_thread = threading.Thread(target=self.mock_server.serve_forever, daemon=True)
        self.server_thread.start()

        self.environment = os.environ.copy()
        self.environment.update({
            "TASK_PROMPT": "Implement solve() in solution.py so the test passes.",
            "WORKSPACE": str(self.workspace),
            "OPENAI_BASE_URL": (
                f"http://127.0.0.1:{self.mock_server.server_address[1]}"
                "/runs/00000000-0000-4000-8000-000000000001/v1"
            ),
            "RUN_ID": "00000000-0000-4000-8000-000000000001",
            "OPENAI_API_KEY": "test-key",
            "ARENA_MODEL": "mock-model",
        })

    def tearDown(self) -> None:
        self.mock_server.shutdown()
        self.mock_server.server_close()
        self.server_thread.join(timeout=2)
        self.mock_script_patch.stop()
        self.temporary_directory.cleanup()

    def test_scripted_task_completes_through_mock_llm(self) -> None:
        agent_path = Path(__file__).with_name("agent.py")
        result = subprocess.run(
            [sys.executable, str(agent_path)],
            cwd=agent_path.parent,
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Completed the task", result.stdout)
        self.assertEqual(server.STATE["i"], 3)
        self.assertIn("return 42", (self.workspace / "solution.py").read_text(encoding="utf-8"))

    def test_run_tests_executes_pytest_in_the_workspace(self) -> None:
        result = run_tests(self.workspace)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("1 passed", result["stdout"])

    def test_workspace_file_resolution_rejects_parent_paths(self) -> None:
        for path in ("../outside.txt", str(self.root / "outside.txt"), "bad\x00path"):
            with self.subTest(path=path), self.assertRaises(ToolError):
                _workspace_file(self.workspace, path)


if __name__ == "__main__":
    unittest.main()
