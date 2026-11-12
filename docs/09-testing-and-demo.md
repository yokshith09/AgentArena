# 09 · Testing Strategy & End-to-End Demo Acceptance

> Status: Draft. Results are recorded per test row; T-17 has a manual browser result, and all other `not run` entries remain pending. Owners per [11](11-team-execution-plan.md).

## 1. Strategy
1. **Contract-first:** fixtures from [08](08-api-contracts.md) §4 / `db/fixtures` are validated against live response models (T-16, T-30) — the main guard against A/B/C drift.
2. **Zero-cost by default:** `mock_llm` upstream for all dev and CI-style checks; real provider only in T-12 and the final benchmark.
3. **Test pyramid (hackathon-sized):** unit (stats, classification, grader), component (proxy, runner, API), one E2E smoke (T-29), manual demo rehearsal.
4. **Independent verifiability:** each component test runs alone (see [10](10-integration-contracts.md) §4).
5. Test framework choices (pytest assumed for Python; JS runner TBD by C) — recorded by owners at CP0.

## 2. Test catalog

Pri = priority of the feature tested. Result column is the only place status is recorded.

| ID | Component | What is checked | Owner | Pri | Result |
|---|---|---|---|---|---|
| T-01 | PX | Non-stream call via `mock_llm` → one `llm_call` event with correct tokens, cost, `cost_confidence`, latency | A | P0 | not run |
| T-02 | PX | Streaming call: chunks pass through unchanged; `include_usage` injected; tokens captured | A | P0 | not run |
| T-03 | PX | Added latency vs direct `mock_llm` measured (NFR-03) | A | P0 | not run |
| T-04 | PX | Response with N tool calls → N `tool_call` events | A | P0 | not run |
| T-05 | PX | Unknown/finished `run_id` → 404 OpenAI error; upstream 5xx tagged `error=upstream`; DB down → still forwards | A | P0 | not run |
| T-06 | Validator/TK | Good tasks accepted; task whose broken state passes → rejected; task whose reference fails → rejected; nondeterministic task rejected | B | P0 | not run |
| T-07 | Grader | Agent edits protected tests → `tamper_detected`, `passed=false`; reference solution → passes | B | P0 | not run |
| T-08 | Runner | Dummy agent gets all env vars (§2.2); diff captured; timeout kills process tree; cleanup done | B | P0 | not run |
| T-09 | Runner | Spawn failure → `sandbox_error`; works on each dev OS (A-06); non-proxy network call blocked + logged in the Docker sandbox | B | P0 | not run |
| T-10 | Grader | Hidden tests run from clean copy; hidden tests absent from agent workspace | B | P0 | not run |
| T-11 | AG | Each reference agent completes a scripted task against `mock_llm` | C | P0 | not run |
| T-12 | AG | Each reference agent attempts ≥ 1 real task via proxy→Bifrost (cost recorded) | C | P0 | not run |
| T-13 | OR | Outcome classification table (PASS / FAIL / INFRA_ERROR; injected faults never INFRA) — unit | B | P0 | not run |
| T-14 | OR | Kill mid-benchmark → resume completes without redoing `done` slots; spend cap halts scheduling | B | P0 | not run |
| T-15 | Stats | Wilson, bootstrap (fixed seed), median/std, edge cases (n=0,1, all pass) vs hand-computed goldens | A | P0 | not run |
| T-16 | API | Each endpoint's response validates against models and mock payloads; error envelope; launch validation rules | A | P0 | not run |
| T-17 | UI | Every screen renders loading/empty/error/success/partial/halted from fixtures; MOCK ribbon visible in mock mode | C | P0 | pass (manual browser check: 9 data routes × 8 fixture states, 72 checks; `/limitations` static route and mock ribbon also checked) |
| T-18 | UI+API | Live mode: leaderboard and run trace for a 2×5×3 benchmark; load < 2 s (NFR-04) | C | P0 | not run |
| T-19 | UI | Accessibility checklist ([05](05-ux-spec.md) §7): keyboard-only pass, focus, contrast spot-check, status not color-only | C | P0 | pass (manual browser check: tab order and visible focus on all 10 routes; mobile menu opens by Enter and links are reachable; Run detail tabs switch by arrow keys; Catalog filter and benchmark preview operate by keyboard; contrast spot-check: link 5.78:1, focus ring 7.31:1, PASS 8.02:1, FAIL 8.63:1; status conveyed in text) |
| T-20 | Faults | 503 and 429 faults fire exactly as defined (first N), emit `fault_injected`, are reproducible with same run_id | A | P0 | not run |
| T-21 | Faults/Stats | Instruction and tool faults applied; resilience score computed per P-16, null on zero baseline | B/A | P0 | not run |
| T-22 | Registry | Register by one command; doctor catches broken manifest and "no proxy traffic" | B | P1 | not run |
| T-23 | Security | Obedient agent flagged; well-behaved agent not; canary leak detected | B | P2 | not run |
| T-24 | Model override | Matrix separates agent vs model effect on fixture data | A | P2 | not run |
| T-25 | Multi-agent | Per-role cost sums equal run total; non-coding graders | A/B | P2 | not run |
| T-26 | Replay | Recorded run replays offline with identical results | A | P3 | not run |
| T-27 | Docs | Fresh-clone walkthrough of README quickstart on a clean machine/user | C + reviewer | P0 | not run |
| T-28 | Generator | Mutation-generated task passes validator; weak task flagged | A | P0 | not run |
| T-29 | E2E smoke | `docker compose up` + tiny benchmark (1 agent, 1 task, N=1, `mock_llm` upstream) → run PASS in DB → visible in UI | all | P0 | not run |
| T-30 | Contracts | `db/fixtures` load into DB; fixtures ↔ `frontend/mocks` ↔ API models consistent | A + C | P0 | not run |

## 3. Cross-cutting checks
- **Secrets scan** before submission (NFR-05). Owner: A. 
- **Accuracy audit:** compare 5 random run rows vs their events by hand (steps, tokens, cost). Owner: A + reviewer. 
- **Data hygiene:** final benchmark data contains no fixture/mock rows.

## 4. End-to-end demo acceptance criteria

Run on the demo machine from a clean state with the **final benchmark data** loaded (recorded at CP4). Each item needs evidence (screenshot or clip) filed under `docs/evidence/` (folder created when first evidence exists).

| ID | Scenario (what the judge sees) | Pass criteria | Evidence | Maps to |
|---|---|---|---|---|
| DA-01 | One command starts the stack | `docker compose up` → dashboard reachable; health OK | clip/screenshot | AC-08 |
| DA-02 | Leaderboard for 3 agents | pass rate with interval, cost, steps, tool calls, time, n, INFRA excluded shown | screenshot | AC-02 |
| DA-03 | Compare agents A vs B | per-task grid; "no clear difference" label when intervals overlap | screenshot | FR-11 |
| DA-04 | Drill into a failed run | timeline shows LLM calls, tool calls, error, diff, grader result | clip | AC-03 |
| DA-05 | Same agent under 4 faults | Failure scenarios matrix with resilience scores; fault event visible in a run timeline | screenshot + clip | AC-04 |
| DA-06 | Launch a small live benchmark | New benchmark appears, progresses, completes (use small N for time) | clip | FR-07 |
| DA-07 | Interrupt and resume (rehearsed, optional live) | benchmark completes after restart | clip | AC-05 |
| DA-08 | Limitations page | honest limits listed | screenshot | AC-09 |
| DA-09 | Cost transparency | run shows cost + verified/estimated label | screenshot | FR-02 |
| DA-10 (P1) | Register an agent + doctor | one command; doctor output for broken manifest | clip | FR-13 |
| DA-12 | Tavily integration | research agent run shows Tavily `tool_call` events in trace, passes its research task; Tavily appears in README/architecture and the category filter | screenshot | D-13 |
| DA-11 (P2) | Security | injection task flags obedient agent only | screenshot | FR-14 |

Rehearsal: full run-through at CP4 (target ≤ 5 min), once more after any hotfix.

## 5. Exit criteria for release (CP5)
All P0 tests `pass` with evidence recorded in the Result column; DA-01…DA-09 evidenced; known failures listed on Limitations page or in README "Known issues"; no `not run` P0 row.
