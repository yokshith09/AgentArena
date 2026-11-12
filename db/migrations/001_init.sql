-- 001_init.sql: generated from docs/07-data-schema.md section 2 (docs are authoritative)
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
                ('llm_call','tool_call','command','file_write','net_attempt','fault_injected')), -- [plan]
  agent_role  text,                                                   -- [plan] NULL unless X-Agent-Role present
  payload     jsonb NOT NULL DEFAULT '{}'::jsonb,                     -- [plan] see §3
  latency     integer,                                                -- [plan] milliseconds
  error       text                                                    -- [plan]
);
CREATE INDEX events_run_idx ON events (run_id, ts, id);

CREATE TABLE schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now()); -- [P]
INSERT INTO schema_migrations(version) VALUES ('001_init') ON CONFLICT DO NOTHING;
