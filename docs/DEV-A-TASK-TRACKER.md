# DEV-A Personal Task Tracker

**Purpose:** The working checklist for DEV-A. Start each DEV-A task here, record progress here, and keep the shared [task board](14-task-board.md) and [test catalog](09-testing-and-demo.md) in sync. This file tracks ownership and completion; interface details remain authoritative in docs 07, 08, and 10.

**Role:** DEV-A — Platform.
**Last updated:** 2026-11-12.
**Role:** DEV-A — Platform.  
**Last updated:** 2026-11-14.
**Project state at tracker creation:** The Git repository is initialized on `main` with a clean worktree and `.env` is ignored. The application/source skeleton, `.env.example`, and dependency manifests are not present. The project is still at the documentation/foundation stage; no implementation tasks are considered done based on documentation alone.

## Status rules

- **Planned** — not started.
- **In progress** — active work; note exactly what is complete and what remains.
- **Blocked** — cannot proceed; name the blocker and the next action.
- **Done** — acceptance criteria met, required tests pass, evidence recorded, and the change is integrated. Update the shared task board and test result at the same time.

Do not mark a task done just because code was written. Record test/evidence links or command results in its entry. Update the **Last updated** date and the status table whenever work changes.

## DEV-A task status at creation

| Order | ID | Task | Priority / milestone | Dependencies | Status |
|---:|---|---|---|---|---|
| 1 | X2 | Complete repository bootstrap | P0 / M0 | None | In progress — approved and pushed on DEV-A; awaiting merge to main |
| 2 | X1 | Sign off contracts and resolve/default open questions | P0 / M0 | None | In progress — DEV-A accepts current drafts/P-02…P-17 and confirms canonical fixtures; Dev-B/Dev-C acknowledgement and open questions remain |
| 3 | A12 | Compose skeleton and `pricing.yaml` shell | P0 / M0 | X1, X2 | In progress — postgres/bifrost/mock_llm compose + `pricing.yaml` shell landed from main (7bb2440); proxy/api/orchestrator/frontend services, Bifrost pin and start/stop smoke remain |
| 4 | A2 | Database migration and fabricated fixtures | P0 / M0 | X1 | In progress — verified 2026-11-14: `python db/check_db.py` → `db OK` on compose Postgres 16 (fixtures load, 4 events read back, status/state + event-type CHECKs reject bad rows, `schema_migrations` = `001_init`). Migration runner `db/migrate.py` + compose `migrate` one-shot on `feat/A2-migrate` (tests pass; fresh-volume and existing-DB runs verified). Remaining: merge to main |
| 5 | A3 | `mock_llm` service | P0 / M0 | X1 | Done per board (main) — `mock_llm/test_mock_llm.py` passes; doc 10 script-format note still to confirm |
| 6 | A1 | Bifrost/provider verification and pricing | P0 / M0 | A12; provider access/OQ-05 | Blocked — provider/model/key/budget (OQ-05); `scripts/smoke_bifrost.py` ready |
| 7 | A4 | Measuring proxy | P0 / M1 | A2, A3; A1 for real upstream | In progress — merged to main via PR #2 (2026-11-14); T-01…T-05 pass vs `mock_llm`; remaining: real-Bifrost check once A1 unblocks |
| 8 | A5 | Statistics engine and P0 API | P0 / M2 | A2, X1 | In progress — implemented on `feat/A5-stats-api`; T-15 + T-16 pass; needs review/merge; re-check against `frontend/mocks` when C1 lands |
| 9 | A6 | Proxy-vs-Bifrost reconciliation | Conditional P0 / M2 | A4, A1, V-03 | Blocked/conditional — determine feasibility after V-03 verification |
| 10 | A7 | Provider fault injection and resilience endpoint | P0 / M3 | A4, A5 | In progress — provider faults on `feat/A7-provider-faults` (T-20 passes, compose smoke OK); resilience endpoint ships with A5 (PR #3); needs review/merge |
| 11 | A13 | Mutation task generator and test-strength score | P0 / M3 | B1, B3 | Planned — coordinate interfaces and generated-task handoff with Dev-B |
| 12 | X5 | Milestone 2 compose integration and benchmark smoke | P0 / M2 | A5, B5, B6, C5, C4 | Planned — shared integration task; DEV-A owns the task |
| 13 | X7 | Freeze and restore demo database | P0 / M4 | X6 | Planned |
| 14 | X9 | Fresh-clone walkthrough and secrets scan | P0 / M5 | C10 | Planned |
| 15 | A9 | Model override and agent/model matrix API | P2 / stretch | A4, A5; only after P0 gate | Planned — gated |
| 16 | A10 | Security score API | P2 / stretch | B10; only after P0 gate | Planned — gated |
| 17 | A11 | Record/replay and local-model support | P3 / stretch | A4; only after P0/P1 gates | Planned — gated |

The order above is the practical dependency order, not permission to bypass the task board's milestone gates. M0/M1/M2/M3/M4/M5 dates and scope cuts are in [PROJECT_ROADMAP.md](../PROJECT_ROADMAP.md) and [12-delivery-plan.md](12-delivery-plan.md). Stretch work is not started unless the preceding release gate is green and DEV-A has capacity.

## Step-by-step task checklist

### 1. X2 — Complete repository bootstrap

**Goal:** Give the team the agreed repository layout and safe baseline.

- [x] Verify Git repository root, current branch, clean worktree, and `.env` ignore rule.
- [x] Create the component skeleton from [10-integration-contracts.md](10-integration-contracts.md) §5 for DB, proxy, API, `mock_llm`, and shared configuration.
- [x] Add `.env.example` containing variable names/placeholders only; never put real credentials in it.
- [x] Add the shared Python dependency specification and pin/record the initial tool versions in `requirements.txt` and `requirements-dev.txt`.
- [x] Check `.gitignore` covers secrets, local environments, caches, and generated artifacts without ignoring needed source.
- [x] Scan for common credential patterns and confirm the bootstrap tree is ready for parallel work.

**Acceptance:** Required folders/files exist, `.env` remains ignored, `.env.example` is safe, dependency setup is reproducible, and secrets scan is clean.
**Tests/evidence:** `git diff --check` passed; `pyproject.toml` parses; `pip install --dry-run -r requirements-dev.txt` resolves; `.env` is ignored and `.env.example` is trackable; common credential-pattern scan found no matches. Update X2 on the shared board after review/integration.

### 2. X1 — Sign off contracts and resolve/default open questions

**Goal:** Freeze the interfaces before dependent implementation begins.

- [ ] Review schema, HTTP API, and component interfaces in [07-data-schema.md](07-data-schema.md), [08-api-contracts.md](08-api-contracts.md), and [10-integration-contracts.md](10-integration-contracts.md).
- [ ] Confirm the fixture list and T-30 scope with Dev-B and Dev-C.
- [ ] Obtain all three developers' acknowledgement; record the contract version and acknowledgements in doc 10's changelog.
- [ ] Record known answers, explicit defaults, or unresolved blockers and dates in [15-open-questions.md](15-open-questions.md).
- [ ] Do not silently decide another developer's interface; use the documented contract-change process for disagreements.

**Known unresolved DEV-A items:** OQ-05 provider/model/key/budget; OQ-06 runtime smoke tests for streaming usage/auth/logging; OQ-09 collaborator access confirmation; OQ-12 confirmation of any prior external work and `.anchor/` ownership. OQ-08 affects B4 (Dev-B), and OQ-13 affects Tavily (Dev-C), so request answers from the relevant owners rather than assuming them.

**Acceptance:** Docs 07/08/10 are version 1 and acknowledged; every relevant open question has an answer, explicit default, or dated blocker; fixtures are agreed.

### 3. A12 — Compose skeleton and pricing shell

**Goal:** Start the agreed service skeleton and prepare pricing configuration.

- [ ] Create the Compose services and documented ports/env wiring for Postgres, Bifrost, proxy, API, orchestrator, and frontend.
- [ ] Add a structurally valid `pricing.yaml` shell without inventing provider prices.
- [ ] Keep credentials in local `.env`; ensure they are not passed into agent containers.
- [ ] Verify `docker compose up` starts Postgres and Bifrost; document health/readiness and stop procedure.

**Acceptance:** Compose starts the required M0 services; ports and configuration are documented; no secrets are committed.
**Tests/evidence:** Compose smoke start/stop and service health output.

### 4. A2 — Database migration and fabricated fixtures

**Goal:** Implement the data schema and repeatable local database setup.

- [x] Implement `db/migrations/001_init.sql` from [07-data-schema.md](07-data-schema.md); preserve its table constraints, enums, indexes, and single-writer rules.
- [x] Add an idempotent migration/apply step and migration tracking.
- [x] Add fabricated, clearly labelled fixtures under `db/fixtures`; never represent fixtures as benchmark results.
- [x] Exercise insert/read of a fake run and its events; check schema/state constraints and fixture load.

**Acceptance:** Tables and constraints match doc 07; migrations and fixtures load; run/event insert-read works.
**Tests/evidence:** Migration/fixture command output and T-30 database-load result.
**Acceptance:** Tables and constraints match doc 07; migrations and fixtures load; run/event insert-read works.  
**Tests/evidence:** Migration/fixture command output and T-30 database-load result.  
**Evidence (2026-11-14):** `db/check_db.py` → `db OK`. `pytest tests/db` → 12 passed (fresh DB gets full schema, idempotent re-run, initdb-created DB recognised, new files applied in numeric order, failing file rolled back and stops, dry run, CLI exit codes 0/1/2, bad names). Compose: existing volume → `up to date (1 applied)`, exit 0, proxy starts after it; fresh volume (separate project) → `applying 001_init`, 6 tables, then `up to date`.

### 5. A3 — `mock_llm`

**Goal:** Let agents and proxy tests run without real provider cost.

- [ ] Implement the HTTP paths and scripted response format in [10-integration-contracts.md](10-integration-contracts.md) §2.6.
- [ ] Support OpenAI-shaped non-stream and stream responses, including `usage` and scripted tool calls.
- [ ] Support `fail_next` for controlled upstream failures.
- [ ] Verify both `/v1/...` and proxy-shaped development paths work.
- [ ] Document invocation/script format in doc 10 and the component README when created.

**Acceptance:** Mock answers scripted calls, streams, tool calls, usage, and configured failures reproducibly.
**Tests/evidence:** Curl smoke checks and use from T-01.

### 6. A1 — Verify Bifrost/provider and record prices

**Goal:** Prove the real integration instead of relying on assumptions.

- [ ] Obtain provider, allowed model, key holder, budget, and rate-limit details (OQ-05); configure secrets locally only.
- [ ] Pin the Bifrost version and confirm endpoint/auth/model naming.
- [ ] Exercise one non-stream and one stream completion; check whether stream usage is returned.
- [ ] Tag a request with the planned run ID/custom metadata and inspect Bifrost logs/API.
- [ ] Record V-01…V-06 evidence/results in [04-trd-architecture.md](04-trd-architecture.md) §6 and the open-question answer document.
- [ ] Add actual input/output token prices and effective date to `pricing.yaml`.

**Acceptance:** V-01/V-02 have evidence; V-03…V-06 are answered or explicitly recorded unknown; valid price entries exist. If provider access is not available, keep A1 blocked and use `mock_llm` for development.

### 7. A4 — Measuring proxy

**Goal:** Forward agent traffic and persist trustworthy usage events.

- [x] Implement the agent-facing API and run-state lookup per [08-api-contracts.md](08-api-contracts.md) §2.
- [x] Forward requests to Bifrost or `mock_llm`; preserve normal responses; add streaming usage options when required.
- [x] Capture model, tokens, latency, cost and confidence; use the versioned pricing table and documented missing-usage behavior.
- [x] Persist `llm_call`, `tool_call`, and provider-fault events (provider-fault events arrive with A7) with documented payload shapes.
- [x] Return the documented OpenAI-shaped 404 for an unknown/non-running run.
- [x] Ensure a DB write failure is surfaced to logs but does not prevent forwarding to the agent.
- [x] Implement `X-Agent-Role` event attribution as specified.

**Acceptance:** Behavior conforms to docs 07/08; DB failure does not block forwarding; T-01…T-05 pass.
**Dependencies:** A2 and A3; A1 is needed for real-provider validation but not for mock-based development.
**Acceptance:** Behavior conforms to docs 07/08; DB failure does not block forwarding; T-01…T-05 pass.  
**Dependencies:** A2 and A3; A1 is needed for real-provider validation but not for mock-based development.  
**Tests/evidence (2026-11-14):** `pytest tests/proxy` → 18 passed (T-01, T-02, T-04 stream+non-stream, T-05 incl. finished run, upstream 5xx/unreachable, DB down; headers, missing usage, unpriced model, truncation, other endpoints). T-03 live: median +17.3 ms. Compose smoke: `docker compose --profile mock up -d --build proxy mock_llm` → stream + non-stream curl stored 2 `llm_call` events (8/11 tokens), unknown run → 404. Event writes are a single multi-row INSERT; a BEGIN/executemany/COMMIT version added ~50 ms per call on Windows.

### 8. A5 — Statistics engine and P0 API

**Goal:** Deliver server-side statistics and all P0 dashboard API shapes.

- [x] Implement stats per [03-feature-specs.md](03-feature-specs.md) F-07 and metric definitions in doc 07 §4; do not compute stats in the UI.
- [x] Implement Wilson pass-rate intervals and fixed-seed bootstrap intervals, plus mean/median/std and edge cases.
- [x] Exclude INFRA_ERROR rows from agent outcome statistics while returning their counts and correct null values.
- [x] Implement P0 catalog, benchmark, run/event, results, and resilience endpoints per [08-api-contracts.md](08-api-contracts.md) §3.
- [x] Validate request parameters and return the documented error envelope.
- [ ] Validate API responses against canonical fixtures and record generated time, counts, and confidence values accurately.

**Acceptance:** Responses match doc 08; INFRA exclusions/null handling are correct; T-15 and T-16 pass.  
**Tests/evidence (2026-11-14):** `pytest tests/stats tests/api` → 43 passed (Wilson goldens incl. 11/15 = 0.4805–0.8910 matching doc 08 §4, bootstrap fixed seed, n=0/1, INFRA exclusion, progress/spend, launch validation rules, pagination bounds, error envelope, doc 08 §4 payloads vs models). Compose: `docker compose up -d --build api` → all endpoints answer on fixture data; `/docs` 200. Open item: validate `frontend/mocks` once C1 adds them.

### 9. A6 — Proxy-vs-Bifrost reconciliation (conditional)

**Goal:** Flag material differences between proxy accounting and Bifrost records if the integration supports it.

- [ ] First establish V-03 tagging/log retrieval feasibility through A1.
- [ ] If feasible, define and document a comparison threshold and flag a run when counts/cost materially mismatch.
- [ ] Test with deliberately altered Bifrost/log data.
- [ ] If infeasible or too costly, document the reason and the measurement limitation; do not ship a fake reconciliation result.

**Acceptance:** Either mismatch detection is verified, or the limitation is explicitly recorded. This task is conditional per the task board.

### 10. A7 — Provider faults and resilience endpoint

**Goal:** Run deterministic outage/rate-limit scenarios and report measured resilience.

- [x] Load/validate provider fault configuration using the fault definitions in doc 07 §7.
- [x] Implement `provider_503_outage` and `provider_429_ratelimit` at the proxy layer with first-N behavior and deterministic seeding.
- [x] Emit `fault_injected` events and mark injected errors distinctly from real upstream errors.
- [x] Implement the resilience response per doc 08 §3.6 and formula P-16; return `null` when the baseline is zero/absent.
- [x] Verify injected failures never get classified as INFRA_ERROR and that repeat runs are reproducible.

**Acceptance:** T-20 and T-21 pass; provider faults and resilience output are visible and correctly scoped.  
**Tests/evidence (2026-11-14):** `pytest tests/proxy/test_faults.py` → 20 passed (exact first-N for 503/429 with OpenAI error shape and `Retry-After`, `fault_injected` + `llm_call(error=injected)` ordering, upstream never reached for injected calls, same sequence across runs, no re-injection after a proxy restart, baseline/tool/unknown scenarios untouched, loader rejects bad YAML). Full proxy suite 38 passed. Compose smoke: 503 run → 503 503 503 200; 429 run → 429 429 200 200. Resilience formula (P-16, null on zero baseline) covered by `tests/api::test_resilience` in PR #3. "Never INFRA" holds on the proxy side (`error='injected'`); the orchestrator's classification is Dev-B's (B5).

### 11. A13 — Mutation generator and test-strength score

**Goal:** Generate valid benchmark tasks and identify weak test suites.

- [ ] Coordinate generator input/output with Dev-B's task format, validator, grader, and seed loader before implementing.
- [ ] Implement generation according to F-17 and the authoritative task shape in doc 07; generated tasks must be labelled and reproducible.
- [ ] Add Hypothesis/property tests where the agreed scope permits.
- [ ] Run every generated task through the validator; reject generation results whose broken state passes or reference state fails.
- [ ] Compute and persist the documented test-strength/weak-task outcome without bypassing validation.
- [ ] Add or update tests and provide a generated fixture for integration.

**Acceptance:** A generated task passes validation and weak tasks are flagged; T-28 and relevant T-06 coverage pass. If schedule slips, apply the documented cut rules with the team rather than silently dropping the P0 requirement.

### 12. X5 — Milestone 2 integration (DEV-A owner; shared work)

**Goal:** Prove the compose stack works end-to-end before expanding scope.

- [ ] Check all dependencies have landed: A5 plus Dev-B orchestration/resume and Dev-C live UI/Agent B.
- [ ] Run compose E2E smoke: 1 agent, 1 task, one run, `mock_llm`.
- [ ] Run the planned tiny real benchmark only when provider access, budget, and time permit.
- [ ] Verify run/event persistence, stats, live UI visibility, and proxy/orchestrator ordering contract (doc 10 §2.5).
- [ ] Fix integration defects and record T-29 outcome; update all owners' task statuses as appropriate.

**Acceptance:** Tiny benchmark completes and is visible in the live UI; T-29 passes; ordering contract holds.

### 13. X7 — Freeze and restore demo data

**Goal:** Produce reproducible demo data that does not depend on a live provider during the demo.

- [ ] Wait for X6 final benchmark completion and agreement on the benchmark to freeze.
- [ ] Export the database to `db/demo-data.sql` without secrets or development/mock rows.
- [ ] Restore the dump into a clean database and compare leaderboard/results with the source.
- [ ] Record restore evidence and any known data limitations.

**Acceptance:** Clean restore produces identical expected leaderboard/results; dump is safe to share.

### 14. X9 — Fresh-clone walkthrough and secrets scan

**Goal:** Verify onboarding instructions on a clean environment before submission.

- [ ] Coordinate with Dev-C, who owns README content, to use the final quickstart instructions.
- [ ] Follow the README from a fresh clone without undocumented local assumptions.
- [ ] Run the complete documented startup/health check; record deviations and fix or report them.
- [ ] Scan tracked files for secrets and verify `.env` remains untracked/ignored.
- [ ] Record T-27 results and update the task board.

**Acceptance:** README steps work unmodified on a clean machine/user; secrets scan is clean; T-27 evidence is recorded.

### 15. A9 — Model override and matrix API (P2, gated)

- [ ] Do not start until P0 integration/release gates are green and scope is approved.
- [ ] Define model-override behavior without changing agent identity or corrupting baseline results.
- [ ] Implement the matrix API and fixture/model separation specified by F-13/doc 08.
- [ ] Verify agent-vs-model effect on fixture data; T-24 passes.

### 16. A10 — Security score API (P2, gated)

- [ ] Do not start until P0 gates are green and Dev-B's security findings/data contract exists.
- [ ] Implement the API shape in doc 08 §3.7; do not imply this is a full security audit.
- [ ] Test score/violation/null behavior against the security fixtures; T-23 passes.

### 17. A11 — Record/replay and local model (P3, gated)

- [ ] Do not start until P0/P1 release gates are green and replay scope is approved.
- [ ] Define what is recorded and what constitutes an identical replay result.
- [ ] Implement offline replay and local-model support without altering original run records.
- [ ] Verify replay determinism with T-26; document unsupported cases.

## Shared working rules for DEV-A

1. Before starting, check the task status and dependencies in this tracker and the shared board. Do not implement against an unsigned/breaking contract.
2. Keep changes within DEV-A ownership in [10-integration-contracts.md](10-integration-contracts.md) §5. Coordinate shared files (`docker-compose.yml`, `.env.example`, migrations, pricing) through the documented ownership rules.
3. Use mocks/fixtures by default; only run real-provider calls when key, budget, and provider limits are confirmed.
4. For each task: set **In progress**, implement, run its listed tests, record evidence, merge/integrate, then mark **Done** in this tracker, the board, and test catalog. If blocked, record who/what is needed and the next action.
5. Keep `main` runnable; no secrets in source, fixtures, logs, or documentation.
6. Raise schedule risk early. DEV-A's planned P0 workload is roughly 42.5 hours in the planning estimates; use the delivery-plan cut rules rather than hiding slippage.

## Change log

| Date | Update |
|---|---|
| 2026-11-12 | Created from the repository documentation pack; verified Git/bootstrap facts and captured DEV-A task sequence and initial status. |
| 2026-11-12 | Implemented and verified X2; approved by DEV-A and pushed as commit `1c84fe3`; awaiting merge to main. |
| 2026-11-12 | DEV-A reviewed docs 07/08/10, accepted current drafts and P-02…P-17, and confirmed the documented T-30 fixture scope; X1 remains open for other-owner acknowledgement and team-only answers. |
| 2026-11-14 | Merged `origin/main` (Stage 0-1 foundation, commit `7bb2440`) into DEV-A; resolved `.env.example`, `.gitignore`, `requirements.txt`, docs README/task-board conflicts; updated A1/A2/A3/A12 statuses. |
| 2026-11-14 | A2 DB check passed (`db OK`). Native Windows Postgres on host port 5432 blocked the first attempt; compose host port is now `${POSTGRES_PORT:-5432}` (documented in `.env.example`), and this machine uses 5433 via local `.env`. |
| 2026-11-14 | A4 measuring proxy implemented on `feat/A4-proxy` (FastAPI, compose service, README); T-01…T-05 pass against `mock_llm`; NFR-03 measured at +17.3 ms median. |
| 2026-11-14 | A2 migration runner (`db/migrate.py`) and compose `migrate` one-shot added on `feat/A2-migrate`; initdb mount removed; proxy waits for migrate. |
| 2026-11-14 | Reviewed Dev-C's C1 contract proposal: 100 fixture objects vs A5 API models, 93 matched. Accepted `agent_started` / `grader_result` event types: migration `002_event_lifecycle_types` (PR #5) and API `Event` model (PR #3). Reported fixture `steps: 7.2` (must be an integer) to Dev-C. |
| 2026-11-14 | A5 stats engine + P0 API implemented on `feat/A5-stats-api` (FastAPI, compose `api` service, README with stats definitions); T-15 and T-16 pass. |
| 2026-11-14 | A7 provider faults implemented on `feat/A7-provider-faults` (faults/*.yaml, loader, proxy injection); T-20 passes; resilience endpoint ships with A5 (PR #3). |
