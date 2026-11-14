# 07 · Data Schema & Migrations — **authoritative for all stored data**

> Status: Draft for CP0 sign-off.
> Tags: **[plan]** field named in the plan's shared data contract (D-08) · **[P]** proposed extension, justified inline.
> Change rule: additive-only after CP0; migrations owned by Dev-A ([10](10-integration-contracts.md) §6).

## 1. Entities

| Table | Purpose | Single writer |
|---|---|---|
| `agents` | Registered agents (manifest) | Seed loader (B); API register (P1) |
| `tasks` | Index of validated task folders | Seed loader (B) |
| `benchmarks` | One launched matrix | API creates; orchestrator updates `state` |
| `runs` | One execution of (agent, task, scenario, repeat, attempt) | Orchestrator |
| `events` | Ordered trace of a run | Proxy; orchestrator for lifecycle, grading, and monitor events |

Filesystem is source of truth for tasks and agent manifests; DB rows are an index (path + hash).

## 2. Tables (DDL, proposed)

```sql
-- db/migrations/001_init.sql
CREATE TABLE agents (
  agent_id      text PRIMARY KEY,                       -- [plan] slug
  name          text NOT NULL,                          -- [plan]
  mode          text NOT NULL CHECK (mode IN ('command','http','docker')), -- [plan]; 'proxy-only' is a usage pattern, not a mode (see §6)
  entrypoint    text NOT NULL,                          -- [plan]
  model_config  jsonb NOT NULL DEFAULT '{}'::jsonb,     -- [plan]
  description   text,                                   -- [plan]
  source_path   text NOT NULL,                          -- [P] dir containing agent.yaml
  created_at    timestamptz NOT NULL DEFAULT now()      -- [P]
);

CREATE TABLE tasks (
  task_id            text PRIMARY KEY,                  -- [plan]
  category           text NOT NULL,                     -- [plan] 'coding' in P0
  prompt             text NOT NULL,                     -- [plan] copy of prompt.md
  workspace          text NOT NULL,                     -- [plan] path relative to task dir
  grader             jsonb NOT NULL,                    -- [plan] {type, config}
  reference_solution text NOT NULL,                     -- [plan] path relative to task dir
  faults_allowed     text[] NOT NULL DEFAULT '{}',      -- [plan] fault ids
  task_dir           text NOT NULL,                     -- [P]
  task_hash          text NOT NULL,                     -- [P] pinning (plan loophole 11)
  validated          boolean NOT NULL DEFAULT false,    -- [P] validator result
  weak               boolean,                           -- [P] P2 test-strength flag, NULL = not assessed
  created_at         timestamptz NOT NULL DEFAULT now() -- [P]
);

CREATE TABLE benchmarks (
  benchmark_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(), -- [P] table named in plan, fields not
  name          text NOT NULL,                              -- [P]
  config        jsonb NOT NULL,                             -- [P] see 08 §3.3 BenchmarkConfig
  state         text NOT NULL DEFAULT 'queued'
                CHECK (state IN ('queued','running','completed','halted_spend_cap','failed')), -- [P]
  error         text,                                       -- [P]
  created_at    timestamptz NOT NULL DEFAULT now(),         -- [P]
  started_at    timestamptz,                                -- [P]
  finished_at   timestamptz                                 -- [P]
);

CREATE TABLE runs (
  run_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),            -- [plan]
  agent_id        text NOT NULL REFERENCES agents(agent_id),             -- [plan]
  task_id         text NOT NULL REFERENCES tasks(task_id),               -- [plan]
  scenario        text NOT NULL DEFAULT 'baseline',                      -- [plan] 'baseline' or fault id
  model           text,                                                  -- [plan] model observed on first successful llm_call (or override, P2)
  status          text CHECK (status IN ('PASS','FAIL','INFRA_ERROR')),  -- [plan] NULL until state='done'
  passed          boolean,                                               -- [plan] status='PASS'; NULL for INFRA_ERROR
  tokens_in       integer,                                               -- [plan]
  tokens_out      integer,                                               -- [plan]
  cost            numeric(12,6),                                         -- [plan] USD
  cost_confidence text CHECK (cost_confidence IN ('verified','estimated')), -- [plan]
  duration        numeric(10,3),                                         -- [plan] seconds, agent process wall time
  steps           integer,                                               -- [plan] see §4
  env_fingerprint jsonb,                                                 -- [plan] see §4.3
  benchmark_id    uuid REFERENCES benchmarks(benchmark_id),              -- [P] NULL allowed for ad-hoc/doctor runs
  repeat_index    integer NOT NULL DEFAULT 1,                            -- [P] 1..n_runs
  attempt         integer NOT NULL DEFAULT 1,                            -- [P] INFRA_ERROR retries (max 3)
  state           text NOT NULL DEFAULT 'queued'
                  CHECK (state IN ('queued','running','done')),          -- [P] lifecycle, separate from status
  tool_calls      integer,                                               -- [P] count of tool_call events (metric listed in plan goal)
  started_at      timestamptz,                                           -- [P]
  finished_at     timestamptz,                                           -- [P]
  grader_result   jsonb,                                                 -- [P] GradeResult (10 §2.3)
  workspace_diff  text,                                                  -- [P] unified diff, truncated at 200 KB
  error           text,                                                  -- [P] orchestrator/runner error text
  CONSTRAINT status_iff_done CHECK ((state = 'done') = (status IS NOT NULL)),
  CONSTRAINT slot_unique UNIQUE (benchmark_id, agent_id, task_id, scenario, repeat_index, attempt)
);
CREATE INDEX runs_bench_idx ON runs (benchmark_id, agent_id, task_id, scenario);
CREATE INDEX runs_state_idx ON runs (state);

CREATE TABLE events (
  id          bigserial PRIMARY KEY,                                  -- [P] stable ordering
  run_id      uuid NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,-- [plan]
  ts          timestamptz NOT NULL DEFAULT now(),                     -- [plan]
  type        text NOT NULL CHECK (type IN
                ('agent_started','llm_call','tool_call','grader_result','command','file_write','net_attempt','fault_injected')), -- [plan]
  agent_role  text,                                                   -- [plan] NULL unless X-Agent-Role present
  payload     jsonb NOT NULL DEFAULT '{}'::jsonb,                     -- [plan] see §3
  latency     integer,                                                -- [plan] milliseconds
  error       text                                                    -- [plan]
);
CREATE INDEX events_run_idx ON events (run_id, ts, id);

CREATE TABLE schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now()); -- [P]
```

Notes: `gen_random_uuid()` requires the Postgres version/extension available (verify at CP0). `NULL` `unique` semantics: ad-hoc runs with `benchmark_id NULL` are not covered by `slot_unique` (acceptable).

## 3. Event payloads (proposed; additive)

Every payload may include `"truncated": true` when bodies exceed 8 KB (stored text cut, not dropped).

| type | `payload` keys | `latency` | `error` |
|---|---|---|---|
| `agent_started` | `task_id` | null | null |
| `llm_call` | `endpoint`, `model`, `status_code`, `tokens_in`, `tokens_out`, `cost`, `cost_confidence`, `finish_reason`, `stream`(bool), `request_preview`, `response_preview` | ms to completion | `upstream` (non-injected upstream failure), `injected` (fault), or free text |
| `tool_call` | `name`, `arguments_preview`, `call_id` | null | null |
| `grader_result` | `passed`, `suite_count` | null | null |
| `fault_injected` | `fault_id`, `group`, `detail` | null | null |
| `command` | `argv`, `cwd`, `exit_code` | ms | null |
| `file_write` | `path`, `outside_workspace`(bool) | null | null |
| `net_attempt` | `host`, `port`, `allowed`(bool) | null | null |

## 4. Metric definitions (P-05) — one place only

1. `steps` = number of `llm_call` events with `status_code` 2xx for the run.
2. `tool_calls` = number of `tool_call` events (calls the model requested; executed results are not observable in black-box mode).
3. `duration` = agent process start→exit in seconds; grading time excluded.
4. `tokens_in/out` = sum over `llm_call` payloads; `cost` = sum of the non-null `payload.cost` values (a call with unknown usage or price has `null` cost and makes the run `estimated`, so the sum is a lower bound; null is never treated as 0).
5. `cost_confidence` for a run = `estimated` if **any** `llm_call` was `estimated`, else `verified`.
6. Statistics exclude rows with `status='INFRA_ERROR'` (D-03) and rows in `state<>'done'`.

### 4.3 `env_fingerprint` (proposed keys)
`{ "model": str|null, "date": ISO date, "task_hash": str, "pricing_version": str, "agent_source_hash": str|null, "python": str, "image_digest": str|null }`. `image_digest` null in P0 (no containers).

## 5. Task folder (authoritative file formats)

```
tasks/<task_id>/
  task.yaml        [P-13]  task_id, category, faults_allowed[]
  prompt.md        [plan]
  workspace/       [plan]  what the agent sees (includes VISIBLE tests)
  hidden_tests/    [P-13]  NOT copied into the agent workspace
  grader.yaml      [plan]  type + config
  reference_solution/ [plan]  files overlaid on workspace to form the solved state
```

### 5.1 `task.yaml`
```yaml
task_id: fix-off-by-one        # == folder name
category: coding
faults_allowed: [provider_503_outage, provider_429_ratelimit, tool_run_tests_error, instruction_misleading_hint]
```

### 5.2 `grader.yaml` (type `pytest`)
```yaml
type: pytest
config:
  visible_tests: [tests/]         # paths inside workspace
  hidden_tests: [hidden_tests/]   # paths inside task dir
  protected_files: [tests/]       # restored from original before grading; hash-compared for tamper
  timeout_s: 120
```

## 6. Agent manifest `agent.yaml` [plan: name, mode, entrypoint, model_config, description]

```yaml
name: agent-a-plain
mode: command                 # command | http | docker  (plan connection modes; 'proxy-only' = any agent honouring a base URL, run via command/docker)
entrypoint: python agent.py   # command string, run with cwd = agent dir
model_config: { model: "<model-name-from-OQ-05>" }
description: Minimal loop, no framework
```
`agent_id` = slug of `name`. `http`, `docker` and `proxy-only` modes arrive with Stage 9 (F-11, P1); P0 reference agents use `command`.

## 7. Fault definition `faults/<fault_id>.yaml` [P]

```yaml
id: provider_503_outage
group: provider            # provider | tool | instruction | environment   (plan groups)
layer: proxy               # proxy | agent_env | runner
description: First 3 requests get 503
params: { first_n: 3, status: 503 }          # provider faults
# instruction fault: params: { file: README.md, append: "..." }
# tool fault:        params: { tool: run_tests, fail_first_n: 2, message: "..." }
```
Loader validates required keys; seed = hash(`run_id`) where randomness is needed. Catalog (P-12) in [03](03-feature-specs.md) F-10.

## 8. `pricing.yaml` [plan: versioned with effective dates; shape P]

```yaml
version: "2026-11-11"
currency: USD
models:
  "<model-name>":
    effective_from: "2026-11-01"
    input_per_1m_tokens: 0.00     # fill from V-06 — values NOT supplied by this doc
    output_per_1m_tokens: 0.00
```

## 9. Migrations

- Files `db/migrations/NNN_description.sql`, forward-only, applied in order by a one-shot step at startup; applied versions recorded in `schema_migrations`.
- `001_init.sql` = §2. Owner A only. Any column add = new file, never edit applied files (after CP0).
- Seed/fixture: `db/fixtures/` holds a small fake benchmark (2 agents × 2 tasks × 3 runs, incl. one INFRA_ERROR and one `fault_injected` run) used by T-16/T-30. **Fixture values are fabricated test data and must never be presented as results.**
