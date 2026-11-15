"""Seed loader (A-1; docs/07 sections 5-6). Indexes agent and task folders into the DB.

The filesystem is the source of truth; rows are an index (path + hash). Agents: every
`agents/*/agent.yaml`. Tasks: every `tasks/*/task.yaml`, loaded **only if validated** by
`grader.validate.validate(task_dir)` (Dev-C). Until that exists, `--trust` loads tasks as
validated without checking and says so loudly; never use it for benchmark data.

Usage: python -m orchestrator.seed [--agents agents] [--tasks tasks] [--trust]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import logging
import os
import sys
from pathlib import Path

import psycopg
import yaml
from psycopg.types.json import Jsonb

log = logging.getLogger("orchestrator.seed")
ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"__pycache__", ".pytest_cache", "node_modules", ".venv"}


def dir_hash(path: Path) -> str:
    """sha256 over relative paths and contents, so any change to the folder changes the hash."""
    h = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        if p.is_file() and not (set(p.relative_to(path).parts) & SKIP_DIRS):
            h.update(p.relative_to(path).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_agents(agents_dir: Path) -> list[dict]:
    out = []
    for manifest in sorted(agents_dir.glob("*/agent.yaml")):
        doc = yaml.safe_load(manifest.read_text(encoding="utf8")) or {}
        missing = [k for k in ("name", "mode", "entrypoint") if not doc.get(k)]
        if missing:
            raise ValueError(f"{manifest}: missing {', '.join(missing)}")
        if doc["mode"] not in ("command", "http", "docker"):
            raise ValueError(f"{manifest}: mode must be command, http or docker")
        out.append({"agent_id": doc["name"], "name": doc["name"], "mode": doc["mode"],
                    "entrypoint": doc["entrypoint"], "model_config": doc.get("model_config") or {},
                    "description": doc.get("description"), "source_path": _rel(manifest.parent)})
    return out


def _validator():
    try:
        return importlib.import_module("grader.validate").validate
    except (ImportError, AttributeError):
        return None


def read_tasks(tasks_dir: Path, trust: bool = False) -> tuple[list[dict], list[str]]:
    """(rows to load, rejection messages)."""
    validate = _validator()
    if validate is None and not trust:
        raise RuntimeError("grader.validate.validate is not available; pass --trust to load tasks "
                           "unvalidated (development only)")
    rows, rejected = [], []
    for meta in sorted(tasks_dir.glob("*/task.yaml")):
        task_dir = meta.parent
        doc = yaml.safe_load(meta.read_text(encoding="utf8")) or {}
        if doc.get("task_id") != task_dir.name:
            rejected.append(f"{task_dir.name}: task_id {doc.get('task_id')!r} must equal the folder name")
            continue
        if validate is not None:
            result = validate(str(task_dir))
            ok = result.get("ok") if isinstance(result, dict) else getattr(result, "ok", False)
            if not ok:
                checks = result.get("checks") if isinstance(result, dict) else getattr(result, "checks", [])
                failed = [c.get("name") if isinstance(c, dict) else getattr(c, "name", "?")
                          for c in checks or []
                          if not (c.get("ok") if isinstance(c, dict) else getattr(c, "ok", False))]
                rejected.append(f"{task_dir.name}: validator failed ({', '.join(map(str, failed)) or 'no detail'})")
                continue
        grader_doc = yaml.safe_load((task_dir / "grader.yaml").read_text(encoding="utf8")) \
            if (task_dir / "grader.yaml").exists() else {}
        prompt = (task_dir / "prompt.md").read_text(encoding="utf8") if (task_dir / "prompt.md").exists() else ""
        rows.append({"task_id": task_dir.name, "category": doc.get("category", "coding"), "prompt": prompt,
                     "workspace": "workspace", "grader": {"type": (grader_doc or {}).get("type"),
                                                          "config": (grader_doc or {}).get("config") or {}},
                     "reference_solution": "reference_solution",
                     "faults_allowed": list(doc.get("faults_allowed") or []),
                     "task_dir": _rel(task_dir), "task_hash": dir_hash(task_dir), "validated": True})
    return rows, rejected


def load(conn: psycopg.Connection, agents: list[dict], tasks: list[dict]) -> None:
    with conn.transaction():
        for a in agents:
            conn.execute(
                "INSERT INTO agents (agent_id, name, mode, entrypoint, model_config, description, source_path)"
                " VALUES (%(agent_id)s, %(name)s, %(mode)s, %(entrypoint)s, %(mc)s, %(description)s, %(source_path)s)"
                " ON CONFLICT (agent_id) DO UPDATE SET name = EXCLUDED.name, mode = EXCLUDED.mode,"
                " entrypoint = EXCLUDED.entrypoint, model_config = EXCLUDED.model_config,"
                " description = EXCLUDED.description, source_path = EXCLUDED.source_path",
                {**a, "mc": Jsonb(a["model_config"])})
        for t in tasks:
            conn.execute(
                "INSERT INTO tasks (task_id, category, prompt, workspace, grader, reference_solution,"
                " faults_allowed, task_dir, task_hash, validated) VALUES (%(task_id)s, %(category)s,"
                " %(prompt)s, %(workspace)s, %(g)s, %(reference_solution)s, %(faults_allowed)s, %(task_dir)s,"
                " %(task_hash)s, %(validated)s) ON CONFLICT (task_id) DO UPDATE SET category = EXCLUDED.category,"
                " prompt = EXCLUDED.prompt, grader = EXCLUDED.grader, faults_allowed = EXCLUDED.faults_allowed,"
                " task_dir = EXCLUDED.task_dir, task_hash = EXCLUDED.task_hash, validated = EXCLUDED.validated",
                {**t, "g": Jsonb(t["grader"])})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Index agent and task folders into the database.")
    ap.add_argument("--agents", type=Path, default=ROOT / "agents")
    ap.add_argument("--tasks", type=Path, default=ROOT / "tasks")
    ap.add_argument("--trust", action="store_true", help="load tasks without the validator (dev only)")
    args = ap.parse_args(argv)
    logging.basicConfig(level="INFO", format="%(levelname)s %(message)s")
    agents = read_agents(args.agents)
    try:
        tasks, rejected = read_tasks(args.tasks, trust=args.trust)
    except RuntimeError as e:
        log.error("%s", e)
        return 2
    if args.trust and _validator() is None:
        log.warning("--trust: %d task(s) loaded WITHOUT validation; not valid for benchmark results", len(tasks))
    with psycopg.connect(os.environ.get("DATABASE_URL", ""), autocommit=True) as conn:
        load(conn, agents, tasks)
    log.info("loaded %d agent(s): %s", len(agents), ", ".join(a["agent_id"] for a in agents) or "-")
    log.info("loaded %d task(s): %s", len(tasks), ", ".join(t["task_id"] for t in tasks) or "-")
    for r in rejected:
        log.warning("rejected %s", r)
    return 1 if rejected else 0


if __name__ == "__main__":
    sys.exit(main())
