# 08 · API Contracts — **authoritative for all HTTP interfaces**

> Status: Draft; **freeze at CP0** (P-06). Plan names the needs ("start a benchmark, list runs, aggregates, leaderboard data, run trace"); routes and shapes below are proposals derived from them.
> Data entities referenced here are defined in [07](07-data-schema.md); not redefined. Component I/O beyond HTTP: [10](10-integration-contracts.md).

## 1. General

### 1.1 Base and format
- Dashboard API base: `/api` (service `api`). JSON UTF-8. Timestamps ISO-8601 UTC. Money = USD number. Durations = seconds.
- Proxy base: `/runs/{run_id}/v1` (service `proxy`), OpenAI wire format (§2).
- Nulls are explicit (`null`), never omitted, for documented fields. Clients ignore unknown fields (enables additive changes).

### 1.2 Auth & ownership (P-07)
No authentication; local single-user. Everything is readable/launchable by whoever reaches the port. CORS: dashboard origin only. Ownership = none (no per-user resources). Provider credentials never leave the gateway/proxy; agents receive a dummy `OPENAI_API_KEY` and the proxy ignores any `Authorization` header from the agent. Document this on the Limitations page; do not expose ports publicly.

### 1.3 Error envelope (dashboard API)
```json
{ "error": { "code": "NOT_FOUND | VALIDATION_ERROR | CONFLICT | INTERNAL", "message": "human text", "details": {} } }
```
HTTP: 404 NOT_FOUND, 422 VALIDATION_ERROR, 409 CONFLICT, 500 INTERNAL. `details` may be `null`.

### 1.4 Pagination
List endpoints: `?limit` (default 50, max 200), `?offset` (default 0). Response `{ "items": [...], "total": int }`.

## 2. Proxy API (agent-facing) — F-01

| Method | Path | Purpose |
|---|---|---|
| POST | `/runs/{run_id}/v1/chat/completions` | OpenAI chat completions; streaming and non-streaming |
| GET | `/health` | `{ "status": "ok" }` |

- `run_id` must be an existing `runs.run_id` with `state='running'` [P-02].
- Optional request header `X-Agent-Role: <string>` → stored as `events.agent_role`.
- Request/response bodies are forwarded as-is to Bifrost, except: (a) `stream_options.include_usage=true` is added for streaming requests if absent (A-02); (b) P2 model override rewrites `model`.
- Proxy-generated errors use OpenAI error shape:

| Case | HTTP | Body `error.type` / `error.code` | Notes |
|---|---|---|---|
| unknown / not-running run | 404 | `invalid_request_error` / `run_not_found` | |
| injected outage | 503 | `server_error` / `injected_fault` | `fault_injected` + `llm_call(error=injected)` events |
| injected rate limit | 429 | `rate_limit_error` / `injected_fault` | header `Retry-After: 1` |
| upstream failure (real) | upstream's status | passed through | `llm_call.error='upstream'` |

Other OpenAI endpoints are forwarded under the same prefix if the gateway supports them and logged as `llm_call` with `payload.endpoint`.

## 3. Dashboard REST API — F-08

### 3.1 Catalog & health

| Method | Path | Response |
|---|---|---|
| GET | `/api/health` | `{ "status": "ok", "db": "ok" \| "down" }` |
| GET | `/api/agents` | `{items: Agent[], total}` |
| GET | `/api/agents/{agent_id}` | `Agent` |
| GET | `/api/tasks?category=` | `{items: TaskSummary[], total}` |
| GET | `/api/scenarios` | `{items: Scenario[], total}` (always includes `baseline`) |

```
Agent        = { agent_id, name, mode, entrypoint, model_config, description }       // 07 agents
TaskSummary  = { task_id, category, prompt, grader_type, faults_allowed[], validated, weak|null }
Scenario     = { id, group: "baseline"|"provider"|"tool"|"instruction"|"environment", layer: "none"|"proxy"|"agent_env"|"runner", description }
```

### 3.2 Benchmarks

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/api/benchmarks` | `BenchmarkConfig` | **202** `Benchmark` (state `queued`) |
| GET | `/api/benchmarks` | pagination | `{items: Benchmark[], total}` newest first |
| GET | `/api/benchmarks/{benchmark_id}` | — | `Benchmark` |

Launch validation (422 with `details.fields`): unknown agent/task/scenario id; any task not `validated`; scenario not in every selected task's `faults_allowed` (except `baseline`); `n_runs` outside 1..10; `spend_cap_usd` ≤ 0.

```
Benchmark = {
  benchmark_id, name,
  state: "queued"|"running"|"completed"|"halted_spend_cap"|"failed",
  config: BenchmarkConfig,
  progress: { total, queued, running, done, infra_error, excluded },   // counts of slots; excluded = slot failed 3 attempts
  spend_usd,                                                            // sum of run costs incl. INFRA_ERROR attempts
  error: string|null, created_at, started_at|null, finished_at|null
}
```

### 3.3 `BenchmarkConfig`
```json
{
  "name": "string, 1..80 chars",
  "agent_ids": ["agent-a-plain"],
  "task_ids": ["fix-off-by-one"],
  "scenarios": ["baseline"],
  "n_runs": 3,
  "spend_cap_usd": 5.0
}
```
`scenarios` default `["baseline"]`. (P2 adds optional `models: string[]` for the matrix; reserved, not accepted in P0 → 422.)

### 3.4 Runs & events

| Method | Path | Notes |
|---|---|---|
| GET | `/api/runs` | filters: `benchmark_id`, `agent_id`, `task_id`, `scenario`, `status`, `state`; pagination; newest first. Items = `Run` |
| GET | `/api/runs/{run_id}` | `RunDetail` |
| GET | `/api/runs/{run_id}/events` | `{items: Event[], total}` ordered by `ts, id`; pagination (default limit 200, max 1000) |

```
Run = { run_id, benchmark_id|null, agent_id, task_id, scenario, repeat_index, attempt, state, status|null,
        passed|null, model|null, tokens_in|null, tokens_out|null, cost|null, cost_confidence|null,
        duration|null, steps|null, tool_calls|null, started_at|null, finished_at|null, error|null }
RunDetail = Run + { env_fingerprint: object|null, grader_result: GradeResult|null, workspace_diff: string|null }
Event = { id, run_id, ts, type, agent_role|null, payload: object, latency|null, error|null }   // 07 §3
GradeResult = see 10 §2.3
```

### 3.5 Results (leaderboard & compare share one endpoint)

`GET /api/benchmarks/{benchmark_id}/results?group_by=agent|agent_task&scenario=baseline&agent_ids=a,b&category=`

- `group_by=agent` → leaderboard (pooled over all that agent's counted runs; `task_id: null`).
- `group_by=agent_task` → compare grid (one row per agent × task).
- `scenario` default `baseline`. `agent_ids` optional filter. `category` optional (P2 UI). Sorted: pass rate desc, then cost mean asc.
- Stats follow [07](07-data-schema.md) §4 and [03](03-feature-specs.md) F-07.

```
ResultRow = {
  agent_id, task_id|null, scenario,
  runs_counted,            // PASS + FAIL
  infra_excluded,          // INFRA_ERROR rows excluded
  pass_rate: PassRate,
  cost: Stat, steps: Stat, tool_calls: Stat, duration: Stat,
  cost_confidence: { verified: int, estimated: int }
}
PassRate = { passed, n, value|null, ci_low|null, ci_high|null }          // Wilson 95%
Stat     = { n, mean|null, median|null, std|null, ci_low|null, ci_high|null }   // bootstrap 95% CI of mean
```
Response: `{ "items": ResultRow[], "benchmark_id": "...", "generated_at": "..." }`.

### 3.6 Resilience (F-10)

`GET /api/benchmarks/{benchmark_id}/resilience` → `{ items: ResilienceRow[] }`
```
ResilienceRow = { agent_id, scenario, baseline_pass_rate: PassRate, scenario_pass_rate: PassRate,
                  resilience_score: number|null }      // scenario ÷ baseline; null if baseline value is 0/null
```
`scenario` here is never `baseline`. Benchmarks without baseline runs return `resilience_score: null`.

### 3.7 Later endpoints (reserved, specified when scheduled)

| Pri | Endpoint | Shape |
|---|---|---|
| P1 | `POST /api/agents/register` `{ "source": "path-or-git-url" }` | 201 `{ agent: Agent, doctor: Doctor }`; 422 with `details = Doctor` when checks fail (nothing inserted). `Doctor = { ok, checks: [{ name, ok, message }] }` |
| P1 | `GET /api/benchmarks/{id}/security` | `{ items: [{ agent_id, security_score|null, tasks_run, violations: [{ run_id, kind: "canary_leak"\|"outside_write"\|"destructive_command"\|"net_attempt" }] }] }` |
| P2 | `POST /api/runs/{run_id}/replay`; `GET .../results?group_by=agent_role` | not specified yet |

## 4. Canonical mock payloads

> **Fabricated sample values for UI development only. Not results. Must not appear in the demo as data.** Machine-readable copies live in `frontend/mocks/` and are validated against live models in T-16/T-30.

`GET /api/benchmarks/{id}/results?group_by=agent`
```json
{ "benchmark_id": "11111111-1111-4111-8111-111111111111", "generated_at": "2026-01-01T00:00:00Z",
  "items": [
    { "agent_id": "agent-a-plain", "task_id": null, "scenario": "baseline", "runs_counted": 15, "infra_excluded": 1,
      "pass_rate": { "passed": 11, "n": 15, "value": 0.733, "ci_low": 0.48, "ci_high": 0.89 },
      "cost":       { "n": 15, "mean": 0.021, "median": 0.019, "std": 0.008, "ci_low": 0.017, "ci_high": 0.025 },
      "steps":      { "n": 15, "mean": 7.2, "median": 7, "std": 2.1, "ci_low": 6.1, "ci_high": 8.3 },
      "tool_calls": { "n": 15, "mean": 9.0, "median": 8, "std": 3.0, "ci_low": 7.5, "ci_high": 10.6 },
      "duration":   { "n": 15, "mean": 41.0, "median": 38.0, "std": 12.0, "ci_low": 35.0, "ci_high": 47.5 },
      "cost_confidence": { "verified": 15, "estimated": 0 } }
  ] }
```
`GET /api/runs/{run_id}`
```json
{ "run_id": "22222222-2222-4222-8222-222222222222", "benchmark_id": "11111111-1111-4111-8111-111111111111",
  "agent_id": "agent-a-plain", "task_id": "fix-off-by-one", "scenario": "provider_503_outage",
  "repeat_index": 1, "attempt": 1, "state": "done", "status": "PASS", "passed": true,
  "model": "mock-model", "tokens_in": 1200, "tokens_out": 300, "cost": 0.0042, "cost_confidence": "verified",
  "duration": 37.5, "steps": 6, "tool_calls": 8, "started_at": "2026-01-01T00:00:00Z", "finished_at": "2026-01-01T00:00:40Z", "error": null,
  "env_fingerprint": { "model": "mock-model", "date": "2026-01-01", "task_hash": "abc", "pricing_version": "2026-11-11", "agent_source_hash": null, "python": "3.x", "image_digest": null },
  "grader_result": { "passed": true, "tamper_detected": false, "suites": [], "summary": "mock" },
  "workspace_diff": "--- a/x.py\n+++ b/x.py\n@@ ...\n" }
```
`GET /api/runs/{run_id}/events` (items)
```json
[ { "id": 1, "run_id": "2222...", "ts": "2026-01-01T00:00:01Z", "type": "fault_injected", "agent_role": null,
    "payload": { "fault_id": "provider_503_outage", "group": "provider", "detail": "call 1 of 3" }, "latency": null, "error": null },
  { "id": 2, "run_id": "2222...", "ts": "2026-01-01T00:00:01Z", "type": "llm_call", "agent_role": null,
    "payload": { "endpoint": "/chat/completions", "status_code": 503, "model": "mock-model", "tokens_in": null, "tokens_out": null, "cost": 0, "cost_confidence": "verified", "stream": false },
    "latency": 4, "error": "injected" },
  { "id": 3, "run_id": "2222...", "ts": "2026-01-01T00:00:08Z", "type": "llm_call", "agent_role": null,
    "payload": { "endpoint": "/chat/completions", "status_code": 200, "model": "mock-model", "tokens_in": 400, "tokens_out": 90, "cost": 0.0012, "cost_confidence": "verified", "finish_reason": "tool_calls", "stream": false },
    "latency": 2100, "error": null },
  { "id": 4, "run_id": "2222...", "ts": "2026-01-01T00:00:08Z", "type": "tool_call", "agent_role": null,
    "payload": { "name": "run_tests", "arguments_preview": "{}", "call_id": "c1" }, "latency": null, "error": null } ]
```
`GET /api/benchmarks/{id}/resilience` (items)
```json
[ { "agent_id": "agent-a-plain", "scenario": "provider_503_outage",
    "baseline_pass_rate": { "passed": 11, "n": 15, "value": 0.733, "ci_low": 0.48, "ci_high": 0.89 },
    "scenario_pass_rate": { "passed": 4, "n": 15, "value": 0.267, "ci_low": 0.11, "ci_high": 0.52 },
    "resilience_score": 0.364 } ]
```
