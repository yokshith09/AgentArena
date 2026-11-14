"""T-08 / T-09: the runner executes an agent as a black box with the documented env, a timeout and a diff."""
import json
import os
import subprocess
import textwrap
import threading
import time
from pathlib import Path

import pytest

from grader.grade import grade
from mock_llm import server
from runner.run import RunSpec, cleanup, load_fault, run_agent

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tasks" / "fix-off-by-one"
RUN_ID = "00000000-0000-4000-8000-0000000000aa"


def make_agent(tmp_path, code, name="agent"):
    d = tmp_path / name
    d.mkdir()
    (d / "agent.py").write_text(textwrap.dedent(code), encoding="utf-8")
    return {"mode": "command", "entrypoint": "python agent.py", "source_path": str(d),
            "model_config": {"model": "test-model"}}


def spec(agent, **kw):
    return RunSpec(run_id=RUN_ID, agent=agent, task_dir=TASK, proxy_base_url="http://proxy.example:8001/", **kw)


@pytest.fixture(autouse=True)
def _cleanup():
    results = []
    yield results
    for r in results:
        cleanup(r)


def run(agent, results, **kw):
    r = run_agent(spec(agent, **kw))
    results.append(r)
    return r


def pid_alive(pid):
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, check=False).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def test_agent_gets_the_documented_environment_and_no_secrets(tmp_path, monkeypatch, _cleanup):
    monkeypatch.setenv("GROQ_API_KEY", "super-secret-provider-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:pw@h/db")
    agent = make_agent(tmp_path, """
        import json, os, pathlib
        keys = ["TASK_PROMPT", "WORKSPACE", "OPENAI_BASE_URL", "RUN_ID", "OPENAI_API_KEY", "ARENA_MODEL", "ARENA_TOOL_FAULT"]
        env = {k: os.environ.get(k) for k in keys}
        env["leaked"] = [k for k in os.environ if k in ("GROQ_API_KEY", "DATABASE_URL")]
        env["cwd"] = os.getcwd()
        pathlib.Path(os.environ["WORKSPACE"], "_env.json").write_text(json.dumps(env))
    """)
    r = run(agent, _cleanup)
    assert r.sandbox_error is None and r.exit_code == 0 and not r.timed_out
    env = json.loads((Path(r.workspace_dir) / "_env.json").read_text())
    assert env["TASK_PROMPT"] == (TASK / "prompt.md").read_text(encoding="utf-8").strip()
    assert env["WORKSPACE"] == r.workspace_dir and Path(env["WORKSPACE"]).is_absolute()
    assert env["OPENAI_BASE_URL"] == f"http://proxy.example:8001/runs/{RUN_ID}/v1"
    assert env["RUN_ID"] == RUN_ID and env["ARENA_MODEL"] == "test-model"
    assert env["OPENAI_API_KEY"] == "arena-dummy-key" and env["ARENA_TOOL_FAULT"] == ""
    assert env["leaked"] == []  # provider/DB secrets never reach the agent
    assert Path(env["cwd"]) == Path(agent["source_path"])


def test_diff_contains_only_the_agents_edits(tmp_path, _cleanup):
    agent = make_agent(tmp_path, """
        import os, pathlib
        ws = pathlib.Path(os.environ["WORKSPACE"])
        (ws / "solution.py").write_text("def sum_range(a, b):\\n    return 1\\n")
        (ws / "notes.txt").write_text("hello\\n")
    """)
    r = run(agent, _cleanup)
    assert "+++ b/solution.py" in r.diff and "+++ b/notes.txt" in r.diff
    assert "tests/test_solution.py" not in r.diff
    assert not (TASK / "workspace" / "notes.txt").exists()  # the task template is never modified


def test_nonzero_exit_and_stderr_are_captured(tmp_path, _cleanup):
    agent = make_agent(tmp_path, """
        import sys
        print("boom on purpose", file=sys.stderr)
        sys.exit(3)
    """)
    r = run(agent, _cleanup)
    assert r.exit_code == 3 and not r.timed_out and "boom on purpose" in r.stderr_tail
    assert r.sandbox_error is None and r.started_at and r.finished_at


def test_timeout_kills_the_whole_process_tree(tmp_path, _cleanup):
    agent = make_agent(tmp_path, """
        import subprocess, sys, time, pathlib, os
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        pathlib.Path(os.environ["WORKSPACE"], "child.pid").write_text(str(child.pid))
        time.sleep(60)
    """)
    t0 = time.time()
    r = run(agent, _cleanup, timeout_s=3)
    assert r.timed_out and r.exit_code is None and time.time() - t0 < 30
    pid = int((Path(r.workspace_dir) / "child.pid").read_text())
    deadline = time.time() + 10
    while pid_alive(pid) and time.time() < deadline:
        time.sleep(0.2)
    assert not pid_alive(pid), "child process survived the timeout"


def test_instruction_fault_is_baseline_not_part_of_the_agents_diff(tmp_path, _cleanup):
    agent = make_agent(tmp_path, """
        import os, pathlib
        text = pathlib.Path(os.environ["WORKSPACE"], "solution.py").read_text()
        pathlib.Path(os.environ["WORKSPACE"], "_seen.txt").write_text(text)
    """)
    r = run(agent, _cleanup, fault=load_fault("instruction_misleading_hint"))
    seen = (Path(r.workspace_dir) / "_seen.txt").read_text()
    assert seen.startswith("# MAINTAINER NOTE")  # the agent really saw the misleading note
    assert "b/solution.py" not in r.diff  # solution.py (with the injected note) is the baseline, unchanged by the agent


def test_tool_fault_is_passed_through_env(tmp_path, _cleanup):
    agent = make_agent(tmp_path, """
        import os, pathlib
        pathlib.Path(os.environ["WORKSPACE"], "_fault.txt").write_text(os.environ["ARENA_TOOL_FAULT"])
    """)
    r = run(agent, _cleanup, fault=load_fault("tool_run_tests_error"))
    params = json.loads((Path(r.workspace_dir) / "_fault.txt").read_text())
    assert params["tool"] == "run_tests" and params["fail_first_n"] == 2


def test_setup_problems_become_sandbox_errors_not_exceptions(tmp_path):
    good = make_agent(tmp_path, "pass\n")
    assert "unsupported agent mode" in run_agent(spec({**good, "mode": "docker"})).sandbox_error
    assert "source_path" in run_agent(spec({**good, "source_path": str(tmp_path / "nope")})).sandbox_error
    bad_task = RunSpec(RUN_ID, good, tmp_path / "no-task", "http://x")
    assert "task folder" in run_agent(bad_task).sandbox_error
    assert "could not start" in run_agent(spec({**good, "entrypoint": "definitely-not-a-program-xyz"})).sandbox_error


def test_cleanup_removes_the_temp_dir(tmp_path):
    r = run_agent(spec(make_agent(tmp_path, "pass\n")))
    work = Path(r.workspace_dir).parent
    assert work.is_dir()
    cleanup(r)
    assert not work.exists()


def test_real_agent_a_solves_a_task_through_runner_then_grader(tmp_path, monkeypatch, _cleanup):
    """Chain check without proxy/DB: runner -> Agent A (scripted by mock_llm) -> workspace -> grader PASS."""
    fixed = (TASK / "reference_solution" / "solution.py").read_text(encoding="utf-8")
    script = tmp_path / "script.json"
    script.write_text(json.dumps({"responses": [
        {"tool_calls": [{"name": "write_file", "arguments": json.dumps({"path": "solution.py", "content": fixed})}]},
        {"tool_calls": [{"name": "run_tests", "arguments": "{}"}]},
        {"text": "Fixed sum_range and ran the tests."},
    ]}))
    monkeypatch.setenv("MOCK_SCRIPT", str(script))
    mock = server.serve(0)
    threading.Thread(target=mock.serve_forever, daemon=True).start()
    try:
        agent = {"mode": "command", "entrypoint": "python agent.py", "source_path": "agents/agent_a",
                 "model_config": {"model": "mock-model"}}
        r = run_agent(RunSpec(RUN_ID, agent, TASK, f"http://127.0.0.1:{mock.server_address[1]}", timeout_s=120))
        _cleanup.append(r)
        assert r.sandbox_error is None and r.exit_code == 0, r.stderr_tail
        assert "+def" not in r.diff and "range(start, end + 1)" in r.diff
        graded = grade(TASK, r.workspace_dir)
        assert graded["passed"] and not graded["tamper_detected"], graded
    finally:
        mock.shutdown()
        mock.server_close()
