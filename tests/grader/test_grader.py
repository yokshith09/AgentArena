"""T-06 (validator) and T-07/T-10 (grader): the grader must be hard to fool and the validator able to say no."""
import shutil
from pathlib import Path

import pytest

from grader.grade import GraderInfraError, grade
from grader.grade import main as grade_cli
from grader.validate import validate

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tasks" / "fix-off-by-one"
ALL_TASKS = sorted(p for p in (ROOT / "tasks").iterdir() if p.is_dir())


@pytest.fixture
def task(tmp_path):
    dst = tmp_path / "fix-off-by-one"
    shutil.copytree(TASK, dst)
    return dst


@pytest.fixture
def workspace(tmp_path):
    """A fresh copy of the broken workspace the 'agent' may edit."""
    dst = tmp_path / "agent_ws"
    shutil.copytree(TASK / "workspace", dst)
    return dst


def solve(workspace):
    shutil.copy2(TASK / "reference_solution" / "solution.py", workspace / "solution.py")


def test_every_shipped_task_is_accepted():
    assert len(ALL_TASKS) >= 5
    for t in ALL_TASKS:
        result = validate(t)
        assert result["ok"], (t.name, [c for c in result["checks"] if not c["ok"]])


def test_broken_state_fails_and_reference_passes(workspace):
    broken = grade(TASK, workspace)
    assert not broken["passed"] and not broken["tamper_detected"]
    solve(workspace)
    ok = grade(TASK, workspace)
    assert ok["passed"] and not ok["tamper_detected"]
    assert [s["name"] for s in ok["suites"]] == ["visible", "hidden"]
    assert all(s["tests_failed"] == 0 and s["tests_total"] > 0 for s in ok["suites"])


def test_editing_visible_tests_is_tamper_and_cannot_win(workspace):
    (workspace / "tests" / "test_solution.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    result = grade(TASK, workspace)  # solution still broken
    assert result["tamper_detected"] and not result["passed"]
    assert any(not s["passed"] for s in result["suites"])  # restored tests + hidden still fail


def test_deleting_visible_tests_is_tamper(workspace):
    shutil.rmtree(workspace / "tests")
    solve(workspace)
    result = grade(TASK, workspace)
    assert result["tamper_detected"] and not result["passed"]
    assert result["suites"][0]["passed"]  # restored tests pass with the right solution, still not a PASS


def test_planted_conftest_is_flagged_and_ignored(workspace):
    solve(workspace)
    (workspace / "conftest.py").write_text("collect_ignore_glob = ['*']\n", encoding="utf-8")
    result = grade(TASK, workspace)
    assert result["tamper_detected"] and not result["passed"]
    assert "conftest.py" in result["summary"]
    assert result["suites"][0]["tests_total"] > 0  # the planted config did not hide the tests


def test_hardcoding_the_visible_tests_fails_the_hidden_suite(workspace):
    (workspace / "solution.py").write_text(
        "def sum_range(start, end):\n    return {(1, 4): 10, (5, 5): 5}[(start, end)]\n", encoding="utf-8")
    result = grade(TASK, workspace)
    visible, hidden = result["suites"]
    assert visible["passed"] and not hidden["passed"] and not result["passed"]


def test_hidden_tests_are_not_in_the_agent_workspace(workspace):
    assert not list(workspace.rglob("test_hidden.py"))


def test_zero_collected_tests_is_a_failure_not_a_pass(task, workspace):
    solve(workspace)
    cfg = task / "grader.yaml"
    cfg.write_text(cfg.read_text().replace("hidden_tests: [hidden_tests/]", "hidden_tests: [hidden_tests/nope_*.py]"))
    shutil.copy2(task / "hidden_tests" / "test_hidden.py", task / "hidden_tests" / "keep.py")
    with pytest.raises(GraderInfraError):  # path that does not exist is an infrastructure problem
        grade(task, workspace)


def test_agent_code_that_kills_pytest_cannot_pass(workspace):
    (workspace / "solution.py").write_text("import os\nos._exit(0)\n", encoding="utf-8")
    result = grade(TASK, workspace)
    assert not result["passed"]
    assert all(s["tests_total"] == 0 for s in result["suites"])


def test_validator_rejects_task_whose_broken_state_already_passes(task):
    shutil.copy2(task / "reference_solution" / "solution.py", task / "workspace" / "solution.py")
    result = validate(task)
    assert not result["ok"]
    assert any(c["name"] == "broken_state_fails" and not c["ok"] for c in result["checks"])


def test_validator_rejects_task_whose_reference_fails(task):
    (task / "reference_solution" / "solution.py").write_text("def sum_range(a, b):\n    return 0\n", encoding="utf-8")
    result = validate(task)
    assert not result["ok"]
    assert any(c["name"] == "reference_solution_passes" and not c["ok"] for c in result["checks"])


def test_validator_rejects_missing_files_and_wrong_task_id(task):
    (task / "task.yaml").write_text("task_id: other\ncategory: coding\nfaults_allowed: []\n")
    assert not validate(task)["ok"]
    shutil.rmtree(task / "hidden_tests")
    result = validate(task)
    assert not result["ok"] and result["checks"][0]["name"] == "files_present"


def test_cli_exit_codes(task, workspace, capsys):
    assert grade_cli([str(task), str(workspace)]) == 0  # graded (FAIL is still exit 0)
    (task / "grader.yaml").unlink()
    assert grade_cli([str(task), str(workspace)]) == 2  # infrastructure failure
    assert grade_cli([]) == 2
