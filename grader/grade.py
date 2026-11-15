"""Grader (B3, F-04). Contract: docs/10 section 2.3, task format: docs/07 section 5.

grade(task_dir, workspace_dir) -> GradeResult. The agent's workspace is NEVER trusted:
  1. copy it to a clean temp dir (caches dropped);
  2. restore every protected file/dir (the visible tests) from the original task workspace, and flag
     tampering if the agent changed or deleted a protected file or planted pytest config
     (conftest.py, pytest.ini, ...) that the task did not ship;
  3. run the visible and hidden suites separately with pytest in that clean copy.
passed = every suite passed AND no tampering. Hidden tests never exist in the agent's workspace.

Infrastructure problems (cannot create dirs, pytest cannot start, bad task files) raise
GraderInfraError so the orchestrator can classify the run INFRA_ERROR instead of FAIL (CLI exit 2).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

CACHE_NAMES = {"__pycache__", ".pytest_cache", ".git", ".hypothesis"}
# Files that change how pytest collects/behaves. The agent may not introduce or alter them.
PYTEST_CONFIG_FILES = {"conftest.py", "pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml"}
DEFAULT_TIMEOUT_S = 120


class GraderInfraError(Exception):
    """The grader itself failed (not the agent's work)."""


def load_grader_config(task_dir: Path) -> dict:
    path = Path(task_dir) / "grader.yaml"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise GraderInfraError(f"cannot read {path}: {error}") from error
    if not isinstance(doc, dict) or doc.get("type") != "pytest" or not isinstance(doc.get("config"), dict):
        raise GraderInfraError(f"{path}: expected `type: pytest` and a `config:` mapping")
    cfg = doc["config"]
    for key in ("visible_tests", "protected_files"):
        if not isinstance(cfg.get(key), list) or not cfg[key]:
            raise GraderInfraError(f"{path}: config.{key} must be a non-empty list")
    cfg.setdefault("hidden_tests", [])
    cfg.setdefault("timeout_s", DEFAULT_TIMEOUT_S)
    return cfg


def _files(root: Path, rel: str) -> list[Path]:
    """All files under root/rel (a file or a directory), relative to root, caches skipped."""
    base = root / rel
    if base.is_file():
        return [Path(rel)]
    out = []
    for current, dirs, names in os.walk(base):
        dirs[:] = [d for d in dirs if d not in CACHE_NAMES]
        for name in names:
            out.append((Path(current) / name).relative_to(root))
    return out


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_clean(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*CACHE_NAMES, "*.pyc"))


def detect_tamper(original: Path, workspace: Path, protected: list[str]) -> list[str]:
    """Human-readable reasons; empty list = no tampering."""
    reasons = []
    for rel in protected:
        for f in _files(original, rel):
            mine = workspace / f
            if not mine.is_file():
                reasons.append(f"protected file deleted: {f.as_posix()}")
            elif _digest(mine) != _digest(original / f):
                reasons.append(f"protected file modified: {f.as_posix()}")
    for current, dirs, names in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in CACHE_NAMES]
        for name in names:
            if name in PYTEST_CONFIG_FILES:
                rel = (Path(current) / name).relative_to(workspace)
                orig = original / rel
                if not orig.is_file() or _digest(orig) != _digest(workspace / rel):
                    reasons.append(f"pytest config added or changed: {rel.as_posix()}")
    return reasons


def _run_suite(name: str, clean: Path, paths: list[str], timeout_s: int) -> dict:
    junit = clean / f".junit_{name}.xml"
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={junit}", *paths]
    # Autoloaded third-party pytest plugins (anyio, hypothesis, ...) slow startup several-fold and could
    # alter results; grading uses plain pytest only.
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    for secret in ("OPENAI_API_KEY", "GROQ_API_KEY", "BIFROST_API_KEY"):
        env.pop(secret, None)
    try:
        proc = subprocess.run(cmd, cwd=clean, capture_output=True, text=True, timeout=timeout_s,
                              env=env, check=False)
    except subprocess.TimeoutExpired:
        return {"name": name, "passed": False, "tests_total": 0, "tests_failed": 0,
                "error": f"{name} suite timed out after {timeout_s}s"}
    except OSError as error:
        raise GraderInfraError(f"cannot start pytest: {error}") from error
    total = failed = 0
    if junit.is_file():
        try:
            raw = junit.read_bytes()
            if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:  # never expand entities from a file the tests could touch
                raise GraderInfraError(f"unexpected DOCTYPE/ENTITY in pytest results for {name}")
            root = ET.fromstring(raw)
            suite = root if root.tag == "testsuite" else root.find("testsuite")
            if suite is not None:
                total = int(suite.get("tests", 0))
                failed = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
        except (ET.ParseError, ValueError, OSError) as error:
            raise GraderInfraError(f"cannot parse pytest results for {name}: {error}") from error
    result = {"name": name, "tests_total": total, "tests_failed": failed}
    # A suite that ran zero tests (collection error, wrong path) is a failure, never a pass.
    result["passed"] = proc.returncode == 0 and total > 0 and failed == 0
    if total == 0:
        result["error"] = f"{name} suite collected no tests"
    return result


def grade(task_dir: str | Path, workspace_dir: str | Path) -> dict:
    """GradeResult dict (docs/10 section 2.3)."""
    task_dir, workspace_dir = Path(task_dir), Path(workspace_dir)
    cfg = load_grader_config(task_dir)
    original = task_dir / "workspace"
    if not original.is_dir() or not workspace_dir.is_dir():
        raise GraderInfraError("task workspace or agent workspace directory is missing")

    tamper = detect_tamper(original, workspace_dir, cfg["protected_files"])
    try:
        with tempfile.TemporaryDirectory(prefix="arena-grade-") as tmp:
            clean = Path(tmp) / "ws"
            _copy_clean(workspace_dir, clean)
            # Restore protected files from the pristine task copy (removes planted extras too).
            for rel in cfg["protected_files"]:
                target = clean / rel
                if target.is_dir():
                    shutil.rmtree(target)
                elif target.exists():
                    target.unlink()
                src = original / rel
                if src.is_dir():
                    shutil.copytree(src, target, ignore=shutil.ignore_patterns(*CACHE_NAMES, "*.pyc"))
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, target)
            # Drop any pytest config the task did not ship, so it cannot influence grading.
            for current, dirs, names in os.walk(clean):
                dirs[:] = [d for d in dirs if d not in CACHE_NAMES]
                for name in names:
                    rel = (Path(current) / name).relative_to(clean)
                    if name in PYTEST_CONFIG_FILES and not (original / rel).is_file():
                        (clean / rel).unlink()
            suites = [_run_suite("visible", clean, cfg["visible_tests"], cfg["timeout_s"])]
            hidden = cfg["hidden_tests"]
            if hidden:
                for rel in hidden:
                    src = task_dir / rel
                    dst = clean / rel
                    if src.is_dir():
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    elif src.is_file():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                    else:
                        raise GraderInfraError(f"hidden test path missing in task: {rel}")
                suites.append(_run_suite("hidden", clean, hidden, cfg["timeout_s"]))
    except OSError as error:
        raise GraderInfraError(f"grader file operation failed: {error}") from error

    passed = all(s["passed"] for s in suites) and not tamper
    bits = [f"{s['name']}: {s['tests_total'] - s['tests_failed']}/{s['tests_total']} passed" for s in suites]
    if tamper:
        bits.append("TAMPERING: " + "; ".join(tamper))
    errors = [s["error"] for s in suites if s.get("error")]
    return {
        "passed": passed,
        "tamper_detected": bool(tamper),
        "suites": [{k: s[k] for k in ("name", "passed", "tests_total", "tests_failed")} for s in suites],
        "summary": " | ".join(bits),
        "error": "; ".join(errors) or None,
    }


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: python -m grader.grade <task_dir> <workspace_dir>", file=sys.stderr)
        return 2
    try:
        print(json.dumps(grade(*argv), indent=2))
        return 0
    except GraderInfraError as error:
        print(f"grader infrastructure failure: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
