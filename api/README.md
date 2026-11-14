# Dashboard API + stats engine (A5)

REST API over the database for the dashboard. Contract: [docs/08 §3](../docs/08-api-contracts.md);
stats definitions: [docs/03 F-07](../docs/03-feature-specs.md) and [docs/07 §4](../docs/07-data-schema.md).
OpenAPI is served at `/docs`. Statistics are computed here only, never in the UI.

## Run

```bash
docker compose up -d --build api      # http://localhost:8000/api/health, /docs
```
Local without Docker: `uvicorn api.app:app --port 8000` with `DATABASE_URL` (as in your `.env`) or the
`PG*` variables set.

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | empty → libpq `PG*` variables | Compose sets `PGHOST`/`PGUSER`/`PGPASSWORD`/`PGDATABASE` |
| `FAULTS_DIR` | `<repo>/faults` | Scenario catalog: `baseline` + one per `faults/*.yaml` (docs/07 §7) |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated dashboard origins |

## Endpoints (P0)

`GET /api/health`, `/api/agents`, `/api/agents/{id}`, `/api/tasks?category=`, `/api/scenarios`,
`POST|GET /api/benchmarks`, `GET /api/benchmarks/{id}`, `/api/benchmarks/{id}/results`,
`/api/benchmarks/{id}/resilience`, `GET /api/runs`, `/api/runs/{id}`, `/api/runs/{id}/events`.
Errors always use the envelope `{"error": {"code", "message", "details"}}`; validation errors put
per-field messages in `details.fields`.

## Stats definitions (state these on the Limitations page)

- Only runs with `state='done'` count. Pass rate = PASS / (PASS + FAIL), **Wilson 95%** interval.
  INFRA_ERROR rows are excluded and reported as `infra_excluded`.
- cost / steps / tool_calls / duration: mean, median, **sample** std (n−1), **95% percentile
  bootstrap CI of the mean** with 1000 resamples and fixed seed 0 (reproducible). Null values
  (e.g. unpriced cost) are skipped, so `n` can be lower than `runs_counted`.
- n = 0 → all nulls (never 0%); n = 1 → std and CI null. Values rounded to 6 decimals.
- Leaderboard sort: pass rate desc, then mean cost asc, nulls last.
- Resilience = scenario pass rate ÷ baseline pass rate per agent; null when the baseline is 0 or absent.

## Decisions the contract left open

- `Benchmark.progress` counts slots (agent × task × scenario × repeat) from the config, using each
  slot's latest attempt: `running`, `done` (PASS/FAIL), `infra_error` (INFRA_ERROR, retry pending,
  attempt < 3), `excluded` (INFRA_ERROR at attempt 3); `queued` = the rest, including slots with no row
  yet. If the config lacks the matrix keys, `total` = slots that have rows.
- `spend_usd` sums cost over all attempts, INFRA_ERROR included.
- `Benchmark.config` is returned as stored (object), so older or partial configs still load.
- `GET /api/runs` "newest first" = `started_at` desc with not-yet-started runs first.
- Unknown or malformed IDs in paths → 404; a malformed `benchmark_id` query filter → 422.

## Tests

```bash
python -m pytest tests/stats tests/api -q     # T-15 (no DB) and T-16 (needs compose Postgres)
```
