# 14 · Task Board

> Status: Draft, generated from one task list on 2026-11-12. **Authoritative for task IDs, owners, estimates, acceptance, status.** Milestones/timeboxes: [PROJECT_ROADMAP.md](../PROJECT_ROADMAP.md). Contracts referenced: [07](07-data-schema.md), [08](08-api-contracts.md), [10](10-integration-contracts.md); tests T-xx in [09](09-testing-and-demo.md).
> Statuses: **Planned · In progress · Blocked · Done**. Nothing is Done: the repo does not exist yet. Update status in place; one accountable owner per task (reviewers: [11](11-team-execution-plan.md) §3).

**Estimate scale:** S ≤ 1 h · M 1–3 h · L 3–6 h · XL 6–10 h of focused work. Load maths uses midpoints S 0.75, M 2, L 4.5, XL 8 h. These are planning guesses, not measurements; re-estimate at each checkpoint.

**Rule:** no task starts before every contract it cites is in version 1 (X1). Tasks depending on another component use the mock listed in 10 §4 until the real one lands.

## Board

| ID | Story/Feature | Task | Owner | Priority | Dependencies | Estimate | Acceptance Criteria | Tests | Status |
|---|---|---|---|---|---|---|---|---|---|
| X2 | US-01 / - | Bootstrap repo: `git init`, `main`, `.gitignore` (incl. `.env`), folder skeleton per 10 §5, `.env.example`, dependency spec files | Dev-A | P0 | none | S | Repo initialised; skeleton dirs exist; `.env` ignored | Credential-pattern scan clean; clean status after review/integration | In progress (approved, committed and pushed on DEV-A; awaiting merge to main) |
| X1 | US-01 / - | Sign off contracts 07, 08, 10 as version 1; answer or default OQ-01…OQ-12 in 01; accept/modify P-02…P-17 | Dev-A | P0 | none | M | All 3 devs ack in 10 changelog; every OQ has a status+date; contract version = 1 | Review checklist; fixture list agreed (T-30 scope) | In progress (drafted, unsigned) |
| A12 | US-02 / F-01 | Compose skeleton (postgres, bifrost, proxy, api, orchestrator, frontend), `pricing.yaml` shell | Dev-A | P0 | X2, X1 | M | `docker compose up` starts postgres + bifrost; ports + env documented in 04 §7 | Compose smoke start/stop | Planned |
| A1 | US-02 / F-01 | Bifrost + one provider key: one successful chat completion; verify V-01…V-06; record in 04 §6; fill model price in `pricing.yaml` | Dev-A | P0 | A12, provider key (OQ-05) | M | V-01, V-02 answered with evidence; V-03…V-06 answered or recorded "unknown"; price in `pricing.yaml` | Saved curl transcript | Planned (needs provider key) |
| A2 | US-03 / F-01 | `001_init.sql`, migration step, `db/fixtures` (fabricated, labelled) | Dev-A | P0 | X1 | M | Tables/constraints per 07 §2; fixtures load; status/state check holds | Insert/read fake run + events; T-30 (load part) | Planned |
| A3 | US-03 / F-01 | `mock_llm` per 10 §2.6; add script format to doc 10 | Dev-A | P0 | X1 | M | Serves `/v1/...` and proxy-shaped path; streaming; `fail_next`; always returns `usage` | Called by curl; used by T-01 | Planned |
| C1 | US-11 / F-09 | Frontend scaffold, routes (05 §2), `types.ts` copied from 08, mock fixtures (08 §4 + empty/INFRA/fault/partial/halted cases), MOCK ribbon, mock/live flag | Dev-C | P0 | X1, X2 | M | Every route renders from fixtures; ribbon visible in mock mode | T-17 (route render) | Planned |
| B1 | US-04 / F-02 | Task format (07 §5), validator CLI (10 §2.4), grader skeleton, 2 exemplar tasks | Dev-B | P0 | X1 | L | Validator accepts 2 tasks, rejects a task whose broken state passes and one whose reference fails | T-06 | Planned |
| A4 | US-03 / F-01 | Proxy: stream + non-stream, usage→tokens, cost with confidence, `tool_call` events, `X-Agent-Role`, upstream-error tagging | Dev-A | P0 | A2, A3 (A1 for real upstream) | L | Behaviour per 08 §2 and 07 §3; unknown run → 404; DB failure does not block forward | T-01…T-05 | Planned |
| B2 | US-05 / F-03 | Runner (subprocess): RunSpec/RunResult (10 §2.1), env contract (§2.2), `agents/dummy`, diff, timeout + process-tree kill | Dev-B | P0 | X1, A3 | L | Dummy agent receives all env vars; diff captured; timeout kills tree; temp dir cleaned | T-08, T-09 (spawn failure) | Planned |
| B3 | US-06 / F-04 | Grader (10 §2.3): clean copy, protected-file restore, tamper flag, visible + hidden tests; seed loader (validated tasks only) | Dev-B | P0 | B1, A2 | L | Tamper → `passed=false`; reference passes; hidden tests never in agent workspace | T-07, T-10 | Planned |
| C2 | US-07 / F-05 | Agent A: no framework, `agent.yaml`, uses env contract | Dev-C | P0 | A3, X1 | M | Completes a scripted task on `mock_llm`; exits 0 | T-11 | Planned |
| C3 | US-11 / F-09 | UI Leaderboard + Run detail (timeline, diff, grader, environment tabs) on mocks, all states | Dev-C | P0 | C1 | L | Matches 05 S1, S4; loading/empty/error/partial states | T-17 | Planned |
| C4 | US-07 / F-05 | Agent B: built with one framework that supports a base-URL setting; `agent.yaml` | Dev-C | P0 | A3, X1 | L | Completes a scripted task through `OPENAI_BASE_URL`; framework named in manifest description | T-11 | Planned |
| X3 | US-08 / F-06 | **Milestone 1 integration:** Agent A × 1 task via runner → proxy → grader → DB (mock first, then real provider once) | Dev-B | P0 | A4, B2, B3, C2 | M | Run row + events + tokens + cost + status stored (plan Milestone 1) | T-12 (once, real); manual DB check | Planned |
| A5 | US-09,10 / F-07,F-08 | Stats engine + all P0 API endpoints (08 §3) | Dev-A | P0 | A2, X1 | XL | Responses match 08 shapes; INFRA excluded; null handling per F-07 | T-15, T-16 | Planned |
| A6 | US-03 / F-01 ext. | Proxy-vs-Bifrost log reconciliation flag (only if V-03 allows) | Dev-A | P0 (conditional) | A4, A1 | M | Mismatch above threshold flags run; if infeasible, gap written to Limitations | Test with doctored log | Planned (conditional on V-03) |
| B5 | US-08 / F-06 | Orchestrator: slot expansion, parallelism, outcome classification, finalise run from events, INFRA retry ≤3, fingerprint | Dev-B | P0 | B2, B3, A4, A2 | XL | Rules per F-06 steps 1-6; injected faults never INFRA; single writer of `runs` | T-13 | Planned |
| B6 | US-08 / F-06 | Checkpoint/resume + spend cap | Dev-B | P0 | B5 | M | Killed orchestrator resumes without redoing done slots; halts at cap | T-14 | Planned |
| C5 | US-11 / F-09 | UI Benchmarks (list, launcher, progress), Compare; switch Leaderboard/Run detail to live | Dev-C | P0 | C3, A5 | XL | Matches 05 S2, S3; live and mock shapes identical | T-17, T-18 | Planned |
| X4 | US-01 / - | Fixture ↔ mocks ↔ API-model consistency check | Dev-C | P0 | A5, C1 | S | Frontend mocks validate against API models | T-30 | Planned |
| X5 | US-08 / - | **Milestone 2 integration:** compose E2E smoke (1 agent, 1 task, N=1, `mock_llm`) + tiny real benchmark (2 agents × 2 tasks × 2 runs) | Dev-A | P0 | A5, B5, B6, C5, C4 | M | Benchmark completes; visible in live UI; ordering contract 10 §2.5 holds | T-29 | Planned |
| B4 | US-05 / F-03 | Hardened Docker sandbox + behaviour monitor (commands, file writes, net attempts) | Dev-B | P0 | B2, B5, Docker confirmed (OQ-08) | XL | Non-root, read-only rootfs, CPU/mem limits, no Docker socket, network only to proxy; blocked attempt logged | T-09 | Blocked until OQ-08 answered |
| A13 | US-13 / F-17 | Mutation generator + Hypothesis property tests + test-strength score + weak flag | Dev-A | P0 | B1, B3 | XL | Generated task passes validator; weak tasks flagged in DB | T-28, T-06 | Planned |
| B12 | US-13 / F-02 | Hand-written tasks to reach 8-10 total with generator output (visible + hidden) | Dev-B | P0 | B1 | L | Each task passes validator; suite size 8-10 | T-06 | Planned |
| C7 | US-07,12 / F-05,F-10 | Agent C (different prompt/model/retry) + `agents/common/tools.py` with tool-fault hook | Dev-C | P0 | C2, X1 | L | Behaviour differs from A; `tool_run_tests_error` fires first N calls | T-11, T-21 | Planned |
| B8 | US-12 / F-10 | Instruction fault + fault loader (07 §7, fail-fast validation) | Dev-B | P0 | B2 | M | Workspace edited pre-run; `fault_injected` event; invalid YAML aborts startup | T-21 | Planned |
| A7 | US-12 / F-10 | Provider faults (503, 429) in proxy + resilience endpoint (08 §3.6) | Dev-A | P0 | A4, A5 | L | First-N semantics, seeded, reproducible; score per P-16 | T-20, T-21 | Planned |
| C8 | US-11,12 / F-09 | UI Failure scenarios, Catalog (weak flags), Limitations page, accessibility pass | Dev-C | P0 | C5, A7 | L | Matches 05 S5, S6, S8; a11y checklist | T-17, T-19 | Planned |
| C14 | US-07 / F-14 | Research agent with Tavily search tool (Tavily key via `.env`); runs through the proxy; Tavily calls visible as `tool_call` events | Dev-C | P0 | C2, A4, Tavily key (OQ-13) | M | Agent answers a research task using Tavily; calls appear in trace; key not in repo | T-11, T-25 (part) | Planned (needs Tavily key) |
| B13 | US-13 / F-14 | `answer_match` grader + 2 research tasks (validator-accepted) for C14 | Dev-B | P0 | B3, B1 | M | Both tasks pass validator; grader returns `GradeResult` (10 §2.3) | T-06, T-10 | Planned |
| X6 | US-08 / - | **Milestone 3 integration:** size and launch final benchmark (F: 12 §3), watch spend | Dev-B | P0 | A7, B4 (or subprocess fallback), B8, A13, B12, B13, C7, C8, C14 | M | Benchmark launched with sized matrix; spend < cap; ≥ 4 fault scenarios present | Monitoring; T-14 on spend | Planned |
| A8 | US-14 / F-11 | Registry `register` + auto-detect + `doctor` + four connection modes | Dev-B | P1 | B2, A4 | XL | One command registers; doctor flags broken manifest / no proxy traffic | T-22 | Planned |
| C9 | US-14 / F-11 | Registry UI form + doctor checks list | Dev-C | P1 | A8 | M | Matches 05 S6 | T-17 | Planned |
| X7 | US-16 / - | Data freeze + `db/demo-data.sql` dump + restore test | Dev-A | P0 | X6 | S | Dump restores a clean DB with identical leaderboard | Restore test | Planned |
| X8 | US-09 / - | Accuracy audit: 5 random runs compared with their events (steps, tokens, cost) | Dev-C | P0 | X6 | M | All 5 match or discrepancies logged and fixed | Manual audit table | Planned |
| C10 | US-16 / F-16 | README quickstart, how-to-add-agent, Limitations text, demo acceptance walkthrough | Dev-C | P0 | X7 | L | AC-08, AC-09 met | T-27 | Planned |
| X9 | US-16 / F-16 | Fresh-clone walkthrough on a clean machine/user + secrets scan | Dev-A | P0 | C10 | M | README steps work unmodified; no secrets in repo | T-27 | Planned |
| X10 | US-16 / F-16 | Two demo rehearsals + video recording | Dev-C | P0 | X7, C10 | L | DA-01…DA-09 evidenced in `docs/evidence/` | Rehearsal checklist | Planned |
| X11 | US-16 / - | Replace derived goals with official rubric in 13 when OQ-01 answered | Dev-C | P0 | OQ-01 | S | 13 rows map official criteria | Review | Planned (waiting OQ-01) |
| A9 | US-15 / F-13 | Stage 11 model override + matrix API | Dev-A | P2 | A4, A5 | L | Matrix separates agent vs model effect | T-24 | Planned (gated) |
| A10 | US-15 / F-12 | Stage 12 security score API | Dev-A | P2 | B10 | M | Per 08 §3.7 | T-23 | Planned (gated) |
| B9 | US-15 / F-14 | Stage 13 `json_fields` grader + doc-analysis suite and remaining research tasks (~5 each; `answer_match` and first 2 research tasks are B13) | Dev-B | P2 | B3 | L | Suites pass validator | T-25, T-06 | Planned (gated) |
| B10 | US-15 / F-12 | Stage 12 canary secret, injection tasks, static scan | Dev-B | P2 | B4 | L | Obedient agent flagged, well-behaved not | T-23 | Planned (gated) |
| C11 | US-15 / F-12,F-14 | Stage 12/13 UI: security tab, role tree, category filter | Dev-C | P2 | A10, B9 | L | Per 05 S7 | T-17 | Planned (gated) |
| C12 | US-15 / F-14 | Stage 13 planner+coder team (sends `X-Agent-Role`) vs single agent | Dev-C | P2 | C7, A4 | XL | Per-role cost sums equal run total | T-25 | Planned (gated) |
| A11 | US-15 / F-15 | Stage 14 record/replay, Ollama, reproducibility pass | Dev-A | P3 | A4 | L | Recorded run replays offline identically | T-26 | Planned (gated) |
| C13 | US-15 / F-15 | Stage 14 fingerprint display + "replay this run" button | Dev-C | P3 | A11 | S | Shown on run detail | T-17 | Planned (gated) |

## Tasks by milestone

| Milestone | Tasks (owner) |
|---|---|
| M0 | X2 (A), X1 (A), A12 (A), A1 (A), A2 (A), A3 (A), C1 (C), B1 (B) |
| M1 | A4 (A), B2 (B), B3 (B), C2 (C), C3 (C), C4 (C), X3 (B) |
| M2 | A5 (A), A6 (A), B5 (B), B6 (B), C5 (C), X4 (C), X5 (A), B12 (B) |
| M3 | B4 (B), A13 (A), C7 (C), B8 (B), A7 (A), C8 (C), C14 (C), B13 (B), X6 (B) |
| M4 | A8 (B), C9 (C), X7 (A), X8 (C) |
| M5 | C10 (C), X9 (A), X10 (C), X11 (C) |
| ST | A9 (A), A10 (A), B9 (B), B10 (B), C11 (C), C12 (C), A11 (A), C13 (C) |

## Planned load (hours, midpoint estimates)

| Scope | Dev-A | Dev-B | Dev-C |
|---|---|---|---|
| M0 | 10.8 | 4.5 | 2.0 |
| M1 | 4.5 | 11.0 | 11.0 |
| M2 | 12.0 | 14.5 | 8.8 |
| M3 | 12.5 | 14.0 | 11.0 |
| M4 | 0.8 | 8.0 | 4.0 |
| M5 | 2.0 | 0.0 | 9.8 |
| **P0 total** | 42.5 | 44.0 | 44.5 |
| **P0 + P1 total** | 42.5 | 52.0 | 46.5 |
| Stretch (P2/P3, gated) | 11.0 | 9.0 | 13.2 |

Reading: available hours per developer are **unknown** (A-03). Day 1 (12 Nov, M0 + M1) plans 15.2 / 15.5 / 13.0 h for Dev-A / B / C. Three working days (12–14 Nov) at 8 h = 24 h each would be exceeded by the P0 totals above; the plan only holds with substantially longer days or by applying the cut rules ([12](12-delivery-plan.md) §4) early. This is a risk, not a guarantee.
