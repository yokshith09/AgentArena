# Orchestrator + seed loader (B5/B6, A-1; owner Dev-A since 2026-11-15)

Runs queued benchmarks (docs/03 F-06) and is the **only writer of `runs`**. Contracts:
runner/grader [docs/10 §2.1, §2.3](../docs/10-integration-contracts.md), ordering §2.5,
metrics [docs/07 §4](../docs/07-data-schema.md).

## Run

The orchestrator runs on the host (the runner starts agents as subprocesses there). It needs the
compose `postgres` + `migrate`, and the `proxy` for real runs.

```powershell
docker compose up -d migrate proxy            # + bifrost (Groq) or --profile mock mock_llm
$env:DATABASE_URL = "postgresql://arena:arena@localhost:5433/arena"
python -m orchestrator.seed                   # index agents/* and validated tasks/* into the DB
python -m orchestrator                        # poll for queued benchmarks (Ctrl+C to stop)
```

| Option | Default | Meaning |
|---|---|---|
| `--once` | off | process queued/running benchmarks, then exit |
| `--stub` | off | stand-in runner/grader from `stubs.py` (until Dev-C's land). **Not benchmark data.** |
| `--parallel N` / `ORCH_PARALLEL` | 2 | runs at once (watch provider rate limits) |
| `--proxy URL` / `PROXY_BASE_URL` | `http://localhost:8001` | given to the runner as `proxy_base_url` |
| `--timeout S` / `RUN_TIMEOUT_S` | 300 | agent wall-clock limit passed to the runner |
| `--min-interval S` / `ORCH_MIN_INTERVAL_S` | 0 | minimum seconds between run starts; ~35 for Groq's free tier (8K tokens/min, ~4K tokens per run) |

Seed loader: tasks load **only if** `grader.validate.validate(task_dir)` says ok. Until the validator
exists, `python -m orchestrator.seed --trust` loads them unvalidated (development only, warned).

## What it does per benchmark

1. Claims a `queued` benchmark (or resumes a `running` one) → `running`. Unknown agent/task/scenario
   ids → `failed` with `error`.
2. Inserts one `runs` row per agent × task × scenario × repeat (attempt 1, idempotent).
3. Runs them with bounded parallelism. Per run: `state='running'` **before** the agent starts (the
   proxy 404s otherwise) → `agent_started` event → (runner/agent_env fault: `fault_injected` event,
   fault passed in `RunSpec.fault`) → `run_agent(spec)` → `grade(task_dir, workspace_dir)` →
   `grader_result` event → `runner.run.cleanup(result)` → wait `settle_s` (1.5 s) for proxy writes →
   metrics from events → classification → row `done`.
4. **Classification** (F-06 step 5): INFRA_ERROR if the runner reports `sandbox_error` or raises,
   the grader raises, or a real upstream failure (`error='upstream'`) is not
   followed by a successful call. Otherwise FAIL on timeout, tamper, failing tests, or non-zero
   exit with no diff; else PASS. Injected faults (`error='injected'`) never cause INFRA_ERROR.
5. INFRA_ERROR → new attempt; after attempt 3 the slot is `excluded`.
6. After each run, if the benchmark's spend ≥ `spend_cap_usd`: no new runs, in-flight runs finish
   (overshoot possible), state `halted_spend_cap`. Otherwise `completed` when all slots resolve.

## Decisions the contract left open

- **Restart:** a run left `running` by a dead orchestrator is marked INFRA_ERROR ("orchestrator
  restarted") and gets a new attempt, instead of being reset to `queued` (F-06 step 8 wording). Its
  real spend and partial trace are kept; reusing the run_id would mix two traces.
- **Workspace release:** after grading the orchestrator calls `runner.run.cleanup(result)` (deletes the
  run's whole temp dir); without it, it deletes `RunResult.workspace_dir`.
- **Grader failures:** the grader *raising* (e.g. `GraderInfraError`, CLI exit 2) = INFRA_ERROR.
  `GradeResult.error` holds agent-caused test problems (suite timed out, collected no tests): FAIL,
  with the message kept in `runs.error`.
- **Runner/agent_env faults:** the orchestrator writes their `fault_injected` event when it hands the
  fault to the runner; the proxy writes the proxy-layer ones.
- Runner and grader may return dataclasses (`orchestrator/types.py`), other objects or plain dicts.
- One orchestrator instance at a time (it resumes any `running` benchmark it finds).

## Tests

`python -m pytest tests/orchestrator -q`. Pure tests need nothing; DB tests create, migrate and drop
their own throwaway database (needs the compose Postgres).
