import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

tools_spec = importlib.util.spec_from_file_location(
    "agentarena_common_tools_under_test",
    Path(__file__).with_name("tools.py"),
)
if tools_spec is None or tools_spec.loader is None:
    raise ImportError("could not load shared tools for tests")
tools_module = importlib.util.module_from_spec(tools_spec)
sys.modules[tools_spec.name] = tools_module
tools_spec.loader.exec_module(tools_module)
ToolError = tools_module.ToolError
load_tool_fault = tools_module.load_tool_fault
run_tests = tools_module.run_tests
workspace_file = tools_module.workspace_file


class SharedToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name) / "workspace"
        self.workspace.mkdir()
        (self.workspace / "test_solution.py").write_text(
            "def test_solution():\n    assert 42 == 42\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_run_tests_fault_fails_exactly_first_n_calls(self) -> None:
        fault = load_tool_fault(json.dumps({
            "tool": "run_tests",
            "fail_first_n": 2,
            "message": "injected pytest failure",
        }))

        first = run_tests(self.workspace, fault)
        second = run_tests(self.workspace, fault)
        third = run_tests(self.workspace, fault)

        self.assertEqual(first, {
            "ok": False,
            "timed_out": False,
            "injected": True,
            "error": "injected pytest failure",
        })
        self.assertEqual(second, first)
        self.assertTrue(third["ok"], third)
        self.assertEqual(third["exit_code"], 0)

    def test_fault_configuration_and_workspace_paths_are_validated(self) -> None:
        with self.assertRaises(ToolError):
            load_tool_fault("{invalid")
        with self.assertRaises(ToolError):
            load_tool_fault(json.dumps({
                "tool": "read_file",
                "fail_first_n": 2,
                "message": "injected failure",
            }))
        for fail_first_n in (-1, True):
            with self.subTest(fail_first_n=fail_first_n), self.assertRaises(ToolError):
                load_tool_fault(json.dumps({
                    "tool": "run_tests",
                    "fail_first_n": fail_first_n,
                    "message": "injected failure",
                }))

        for path in ("../outside.txt", str(self.workspace.parent / "outside.txt"), "bad\x00path"):
            with self.subTest(path=path), self.assertRaises(ToolError):
                workspace_file(self.workspace, path)


if __name__ == "__main__":
    unittest.main()
