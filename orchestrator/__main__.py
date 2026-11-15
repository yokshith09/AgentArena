"""python -m orchestrator [--once] [--stub] [--parallel N] [--proxy URL] [--timeout S]

Runs queued benchmarks (docs/03 F-06). Uses Dev-C's runner.run.run_agent and grader.grade.grade;
--stub uses the stand-ins in orchestrator/stubs.py instead (results are not benchmark data).
Connection: DATABASE_URL, or libpq PG* variables when unset.
"""
from __future__ import annotations

import argparse
import importlib
import logging
import os
import signal
import sys

from .core import Config, Orchestrator


def load_callables(stub: bool):
    if stub:
        from . import stubs
        return stubs.run_agent, stubs.grade
    try:
        run_agent = importlib.import_module("runner.run").run_agent
        grade = importlib.import_module("grader.grade").grade
    except (ImportError, AttributeError) as e:
        raise SystemExit(f"runner/grader not available ({e}); use --stub until they land") from e
    return run_agent, grade


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run queued AgentArena benchmarks.")
    ap.add_argument("--once", action="store_true", help="process queued benchmarks, then exit")
    ap.add_argument("--stub", action="store_true", help="use the stand-in runner and grader")
    ap.add_argument("--parallel", type=int, default=int(os.environ.get("ORCH_PARALLEL", "2")))
    ap.add_argument("--proxy", default=os.environ.get("PROXY_BASE_URL", "http://localhost:8001"))
    ap.add_argument("--timeout", type=int, default=int(os.environ.get("RUN_TIMEOUT_S", "300")))
    ap.add_argument("--poll", type=float, default=2.0)
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run_agent, grade = load_callables(args.stub)
    orch = Orchestrator(Config(dsn=os.environ.get("DATABASE_URL", ""), proxy_base_url=args.proxy,
                               parallel=max(1, args.parallel), timeout_s=args.timeout, poll_s=args.poll),
                        run_agent, grade)
    signal.signal(signal.SIGINT, lambda *_: orch.stop())
    if args.once:
        orch.run_once()
    else:
        orch.serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
