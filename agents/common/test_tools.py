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
execute_tool = tools_module.execute_tool
keep_tail = tools_module.keep_tail
temperature_from_env = tools_module.temperature_from_env


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

    def test_list_files_lists_relative_paths_and_skips_noise(self) -> None:
        (self.workspace / "pkg").mkdir()
        (self.workspace / "pkg" / "mod.py").write_text("x = 1\n", encoding="utf-8")
        (self.workspace / "__pycache__").mkdir()
        (self.workspace / "__pycache__" / "junk.pyc").write_text("x", encoding="utf-8")
        result = json.loads(execute_tool(self.workspace, "list_files", {}))
        self.assertEqual(result["files"], ["pkg/mod.py", "test_solution.py"])
        self.assertFalse(result["truncated"])

    def test_long_output_keeps_the_tail_where_pytest_prints_failures(self) -> None:
        text = "x" * 30_000 + "FAILED test_solution.py::test_solution"
        out = keep_tail(text)
        self.assertTrue(out.endswith("FAILED test_solution.py::test_solution"))
        self.assertLess(len(out), 12_100)
        self.assertEqual(keep_tail("short"), "short")

    def test_temperature_setting(self) -> None:
        self.assertEqual(temperature_from_env(None), 0.0)
        self.assertIsNone(temperature_from_env("  "))
        self.assertEqual(temperature_from_env("0.7"), 0.7)
        for bad in ("hot", "-1", "3"):
            with self.subTest(bad=bad), self.assertRaises(ToolError):
                temperature_from_env(bad)


if __name__ == "__main__":
    unittest.main()
