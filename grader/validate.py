"""Task validator (B1, F-02). Contract: docs/10 section 2.4, task format: docs/07 section 5.

A task is accepted only if: its files and metadata are well-formed, the BROKEN workspace fails the
grader, the workspace with the reference solution overlaid PASSES, and grading is deterministic.

    python -m grader.validate                 # every tasks/*/ folder
    python -m grader.validate tasks/some-task # one task
Exit code 0 = all accepted, 1 = at least one rejected.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

from .grade import GraderInfraError, grade, load_grader_config

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("task.yaml", "prompt.md", "workspace", "hidden_tests", "grader.yaml", "reference_solution")


def _check(checks: list[dict], name: str, ok: bool, message: str = "") -> bool:
    checks.append({"name": name, "ok": bool(ok), "message": message})
    return bool(ok)


def validate(task_dir: str | Path) -> dict:
    """{ok, checks:[{name, ok, message}]} (docs/10 section 2.4)."""
    task = Path(task_dir)
    checks: list[dict] = []

    missing = [r for r in REQUIRED if not (task / r).exists()]
    if not _check(checks, "files_present", not missing, "missing: " + ", ".join(missing) if missing else ""):
        return {"ok": False, "checks": checks}

    try:
        meta = yaml.safe_load((task / "task.yaml").read_text(encoding="utf-8")) or {}
        meta_ok = (meta.get("task_id") == task.name and isinstance(meta.get("category"), str)
                   and isinstance(meta.get("faults_allowed"), list))
        _check(checks, "task_yaml", meta_ok, "" if meta_ok else
               "task.yaml needs task_id == folder name, category, faults_allowed (list)")
    except (OSError, yaml.YAMLError) as error:
        _check(checks, "task_yaml", False, str(error))

    try:
        cfg = load_grader_config(task)
        _check(checks, "grader_config_parses", True)
    except GraderInfraError as error:
        _check(checks, "grader_config_parses", False, str(error))
        return {"ok": False, "checks": checks}

    absent = [p for p in cfg["protected_files"] if not (task / "workspace" / p).exists()]
    _check(checks, "protected_files_exist", not absent, "missing in workspace: " + ", ".join(absent) if absent else "")
    absent = [p for p in cfg["hidden_tests"] if not (task / p).exists()]
    _check(checks, "hidden_tests_exist", not absent, "missing in task: " + ", ".join(absent) if absent else "")
    if not all(c["ok"] for c in checks):
        return {"ok": False, "checks": checks}

    try:
        broken = grade(task, task / "workspace")
        _check(checks, "broken_state_fails", not broken["passed"],
               "" if not broken["passed"] else "the unsolved workspace already passes: " + broken["summary"])

        with tempfile.TemporaryDirectory(prefix="arena-validate-") as tmp:
            solved = Path(tmp) / "ws"
            shutil.copytree(task / "workspace", solved, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
            shutil.copytree(task / "reference_solution", solved, dirs_exist_ok=True)
            first = grade(task, solved)
            second = grade(task, solved)
        _check(checks, "reference_solution_passes", first["passed"],
               "" if first["passed"] else "reference solution fails: " + first["summary"])
        _check(checks, "deterministic", first["passed"] == second["passed"] and first["suites"] == second["suites"],
               "" if first == second else "two gradings of the same workspace differ")
    except GraderInfraError as error:
        _check(checks, "grader_runs", False, str(error))
    return {"ok": all(c["ok"] for c in checks), "checks": checks}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    dirs = [Path(a) for a in argv] or sorted(p for p in (ROOT / "tasks").iterdir() if p.is_dir())
    rejected = 0
    for d in dirs:
        result = validate(d)
        print(f"{'ACCEPT' if result['ok'] else 'REJECT'}  {d.name}")
        for c in result["checks"]:
            if not c["ok"]:
                print(f"    x {c['name']}: {c['message']}")
        rejected += not result["ok"]
    print(json.dumps({"tasks": len(dirs), "rejected": rejected}))
    return 1 if rejected else 0


if __name__ == "__main__":
    raise SystemExit(main())
