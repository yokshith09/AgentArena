# 10 · Integration Contracts

> Status: Draft; **contract version 0 → becomes 1 at CP0 sign-off.** Authoritative for: in-process/CLI/env interfaces (§2), mocks (§4), repo ownership (§5), change rules (§6). Data → [07](07-data-schema.md); HTTP → [08](08-api-contracts.md). Nothing here restates those.

## 1. Component contract table

| Component | Owner | Input | Output | Depends on | Mock available | Verification |
|---|---|---|---|---|---|---|
| DB + migrations | A | SQL files | Tables per 07 | Postgres | `db/fixtures` fake benchmark | T-30 |
| `mock_llm` | A | scripted JSON | OpenAI-shaped responses with `usage` | — | is the mock | T-01 |
| PX proxy | A | 08 §2 request | passthrough response + `events` rows | DB, Bifrost or `mock_llm`, `pricing.yaml`, `faults/` | `mock_llm` upstream | T-01…T-05, T-20 |
| API + stats | A | DB rows | 08 §3 responses | DB | fixtures (`db/fixtures`) | T-15, T-16 |
| Seed loader | B | `tasks/`, `agents/` dirs | `tasks`, `agents` rows | DB, validator | task fixtures | T-06 |
| Validator | B | task dir | `{ok, checks[]}` (§2.4) | Grader | good/bad task fixtures | T-06 |
| Grader | B | task dir + workspace dir | `GradeResult` (§2.3) | pytest | reference solution as input | T-07, T-10 |
| Runner | B | `RunSpec` (§2.1) | `RunResult` | agent, proxy URL | `agents/dummy` + `mock_llm` | T-08, T-09 |
| Orchestrator | B | DB `benchmarks` queued | `runs` finalised, benchmark state | DB, Runner, Grader | stubbed Runner returning canned `RunResult` | T-13, T-14 |
| Reference agents | C | env contract (§2.2) | edited workspace, exit code | proxy URL | `mock_llm` | T-11, T-12 |
| Tasks | B (hand-written) / A (generated) | — | task folders | validator | — | T-06 |
| Dashboard | C | 08 §3 JSON | UI | API | `frontend/mocks/*.json` (mock mode) | T-17…T-19, T-30 |
| Registry CLI + doctor (P1) | B | path/URL | `agents` row + Doctor | Runner, `mock_llm` | trivial built-in task | T-22 |

## 2. Interface definitions

### 2.1 Runner (Python call; shape, not code)
`run_agent(spec: RunSpec) -> RunResult`

| RunSpec field | Type | Meaning |
|---|---|---|
| `run_id` | uuid | from `runs` |
| `agent` | `{mode, entrypoint, source_path, model_config}` | from 07 agents |
| `task_dir` | path | task folder (07 §5) |
| `fault` | fault definition or null | scenario's fault if layer `runner`/`agent_env`; proxy-layer faults are read by the proxy itself |
| `proxy_base_url` | string | e.g. `http://proxy:PORT` (no trailing slash) |
| `timeout_s` | int | wall-clock limit (default 300) |

| RunResult field | Type | Meaning |
|---|---|---|
| `exit_code` | int\|null | null if killed |
| `timed_out` | bool | |
| `workspace_dir` | path | post-run workspace, input to the grader (runner deletes it only after orchestrator releases it) |
| `diff` | string | unified diff vs original workspace |
| `stdout_tail`, `stderr_tail` | string | last ≤ 4 KB each |
| `started_at`, `finished_at` | ISO ts | agent process window → `duration` |
| `sandbox_error` | string\|null | non-null ⇒ orchestrator classifies INFRA_ERROR |

### 2.2 Agent environment contract (runner → agent)

| Var | Origin | Meaning |
|---|---|---|
| `TASK_PROMPT` | plan | task prompt text |
| `WORKSPACE` | plan | absolute path of the writable workspace |
| `OPENAI_BASE_URL` | plan | `{proxy_base_url}/runs/{run_id}/v1` [P-02] |
| `RUN_ID` | plan | uuid |
| `OPENAI_API_KEY` | P-17 | dummy constant; proxy ignores it |
| `ARENA_MODEL` | P-17 | `agent.model_config.model`; reference agents use it, others may ignore |
| `ARENA_TOOL_FAULT` | P-17 | JSON of the tool-fault `params` or empty string; honoured by `agents/common/tools.py` |

Agent obligations: modify files only under `WORKSPACE`; exit 0 when done; do not read other env for credentials. cwd = agent source dir.

### 2.3 Grader
`grade(task_dir, workspace_dir) -> GradeResult`; CLI prints the same JSON to stdout.
```
GradeResult = { passed: bool, tamper_detected: bool,
                suites: [{ name: "visible"|"hidden", passed: bool, tests_total: int, tests_failed: int }],
                summary: string, error: string|null }
```
Exit codes (CLI): 0 = graded (pass or fail), 2 = grader infrastructure failure (⇒ INFRA_ERROR). `passed` = all suites pass ∧ ¬`tamper_detected`.

### 2.4 Validator
`validate(task_dir) -> { ok: bool, checks: [{ name, ok, message }] }` with checks: `grader_config_parses`, `protected_files_exist`, `broken_state_fails`, `reference_solution_passes`, `deterministic` (graded twice, same outcome).

### 2.5 Proxy ↔ orchestrator ordering contract
1. Orchestrator sets run `state='running'` **before** spawning the agent (proxy 404s otherwise).
2. After agent exit, orchestrator waits ≤ 2 s for in-flight event writes, then aggregates events (07 §4) and sets `state='done'`.
3. Classification input: `events` where `type='llm_call'` and `error='upstream'` (real failures) vs `error='injected'` (ignored for INFRA).
4. Proxy never updates `runs`; orchestrator never writes `llm_call` events.

### 2.6 `mock_llm` (A)
HTTP server answering `POST /v1/chat/completions` (and the proxy-shaped `POST /runs/{run_id}/v1/chat/completions` for agent development before the proxy exists). Behaviour driven by a JSON script file: ordered list of responses, each either `{text}` or `{tool_calls:[{name, arguments}]}`, always with a `usage` block; optional `fail_next: {n, status}` to emulate upstream errors; supports `stream=true`. Proxy reads upstream base URL from `UPSTREAM_BASE_URL` [P]. Script format (implemented): see the docstring of `mock_llm/server.py`; admin endpoint `POST /_admin/fail {"n","status"}`.

## 3. Shared types & conventions

### 3.1 Authority map (one definition each)

| Thing | Authority |
|---|---|
| Tables, enums, metric definitions, event payloads, task/agent/fault/pricing file formats | [07](07-data-schema.md) |
| HTTP routes, errors, response types (`ResultRow`, `Stat`, …), mock payloads | [08](08-api-contracts.md) |
| Stats formulas | [03](03-feature-specs.md) F-07 |
| `RunSpec`, `RunResult`, env vars, `GradeResult`, validator, ordering, `mock_llm` | this file §2 |
| Decisions / assumptions / open questions | [01](01-hackathon-strategy.md) |
| Scope tiers | [02](02-prd.md) |

### 3.2 Conventions
`snake_case` JSON keys; ids are lowercase slugs (`[a-z0-9-]+`) except uuids (`run_id`, `benchmark_id`); scenario id == fault id (or `baseline`); unknown JSON fields ignored by readers; enums only grow.

### 3.3 Frontend ↔ backend type sharing
Types are **copied, not generated**, from 08 into `frontend/src/api/types.ts` (C owns). Drift is caught by T-16/T-30 (fixtures validated against live response models).

### 3.4 Task author checklist (C writes, B reviews)
- Folder name == `task_id`; `task.yaml`, `prompt.md`, `workspace/`, `hidden_tests/`, `grader.yaml`, `reference_solution/` present.
- Visible tests in workspace fail on the broken state; hidden tests cover behaviour the visible ones do not.
- No network, no randomness, runtime < 10 s.
- Validator passes locally before PR.

## 4. Mocks & testing components independently

| Component | Develop & test alone using | Notes |
|---|---|---|
| UI (C) | `frontend/mocks/*.json` + mock-mode flag + "MOCK DATA" ribbon | Fixtures = 08 §4 payloads extended; must include INFRA, fault, partial, halted, empty cases |
| Agents (C) | `mock_llm` path `/runs/{id}/v1` + a temp workspace | No proxy/DB needed |
| Runner (B) | `agents/dummy` (makes one LLM call, edits a file, exits) + `mock_llm` | Env contract §2.2 asserted by the dummy |
| Grader/validator (B) | task fixtures + reference solutions | CLI form |
| Orchestrator (B) | stub Runner/Grader returning canned results + DB fixtures | Kill/resume testable without LLM |
| Proxy (A) | `mock_llm` upstream + DB | Fault catalog exercised without provider |
| API/stats (A) | `db/fixtures` | Golden numbers in T-15 |
| Whole system | `mock_llm` as upstream for the proxy → E2E smoke at zero cost (T-29) | Real-provider runs only for final benchmark |

Run commands live in each component's own README (written by owner); not specified here to avoid duplicate definitions.

## 5. Repo layout, ownership, conflict areas (P-10)

```
docker-compose.yml  .env.example  pricing.yaml  README.md  HACKATHON_PLAN.md
db/{migrations,fixtures}/   proxy/   api/(incl. stats)   mock_llm/        -> Dev-A
orchestrator/   runner/   grader/(incl. validator, seed loader)           -> Dev-B
agents/(incl. common/tools.py)   frontend/(incl. mocks/)                  -> Dev-C
tasks/   (hand-written Dev-B, generated Dev-A)    agents/dummy/    -> Dev-B
faults/   (one YAML per fault; owner by group: provider A, instruction B, tool C)
docs/     (all contribute; Dev-C stewards)
```

| Shared / high-conflict file | Risk | Rule |
|---|---|---|
| `docker-compose.yml` | Everyone adds a service | A owns; others edit only their own service block via small PR; no reformatting |
| `.env.example` | Concurrent var additions | Append-only, alphabetical, A merges |
| `db/migrations/*` | Schema races | A only; new file per change; never edit applied file |
| `pricing.yaml` | Cost numbers | A only |
| `docs/07`, `docs/08`, `docs/10` | Contract drift | Change only via §6 protocol |
| `frontend/mocks/*`, `frontend/src/api/types.ts` | Must match 08 | C only; A reviews against 08 |
| `faults/*.yaml` | Format drift | Format per 07 §7; owner by group; A reviews format |
| `agents/common/tools.py` | Used by all reference agents | C owns; B reviews fault hook |
| `README.md`, `HACKATHON_PLAN.md` | Last-minute edits | C only in final day; others send text |
| Dependency manifests (Python/JS) | Version conflicts | One shared Python env spec (A creates), additions via PR |

## 6. Compatibility & change rules (NFR-01)

1. After CP0: **additive only** (new optional fields, new enum values, new endpoints). Readers ignore unknown fields; UI renders unknown enum values as neutral "unknown".
2. Breaking change protocol: PR labelled `contract` that (a) edits the authoritative doc, (b) updates fixtures and mocks, (c) updates affected tests, (d) has explicit ack from the **other two** owners. Merge only when T-16/T-30 pass.
3. Never silently reinterpret a field (e.g. change units); add a new field instead.
4. Anything not in an authoritative doc is not a contract; do not depend on it.

### Changelog
| Date | Version | Change | Ack |
|---|---|---|---|
| 2026-11-11 | 0 | Draft pack created | — |
| 2026-11-12 | 0 | DEV-A (Akhil) reviewed and accepted the current drafts and P-02…P-17; version 1 remains pending team sign-off and open-question disposition | DEV-A only; Dev-B/Dev-C pending |
| 2026-11-12 | 0 | DEV-A confirmed the canonical T-30 fixture scope from docs 07/10; other-owner agreement is not yet confirmed | DEV-A only |
