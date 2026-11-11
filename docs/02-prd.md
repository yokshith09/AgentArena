# 02 · Product Requirements (PRD)

> Status: Draft for CP0 sign-off · IDs: G (goals, [01](01-hackathon-strategy.md)), FR/NFR (here), F (features, [03](03-feature-specs.md))

## 1. Users

| User | Needs | Primary screens |
|---|---|---|
| **Agent developer** (primary) | Compare my agent with others on identical tasks; see cost, reliability, failure behaviour; find *why* it lost | Leaderboard, Compare, Run detail |
| **Benchmark operator** (same person, other hat) | Launch a benchmark, watch progress, stay under budget, resume after interruption | Benchmarks |
| **Hackathon judge** (demo audience) | Understand value in minutes; verify claims are honest | Leaderboard, Failure scenarios, Limitations |

## 2. Problem & goals
See [01](01-hackathon-strategy.md) §1–2 (G1–G8). Not restated.

## 3. Functional requirements

Priority follows the plan's cut line (D-12): **P0** = Stages 0-8, 10, 15 (must ship); **P1** = Stage 9; **P2** = Stages 11-13; **P3** = Stage 14. Plan-stage references are to `AgentArena_Complete_Plan.md` §4.

| ID | Requirement | Goal | Pri | Feature | Plan stage |
|---|---|---|---|---|---|
| FR-01 | Proxy forwards OpenAI-compatible chat requests to Bifrost and records one `llm_call` event per request (model, tokens from `usage`, latency, error) plus one `tool_call` event per tool call in the response; supports streaming | G1 G2 | P0 | F-01 | 2 |
| FR-02 | Cost computed from `pricing.yaml` and tokens; each run labelled `cost_confidence` verified/estimated | G2 | P0 | F-01 | 1–2 |
| FR-03 | Task = `prompt + workspace + grader (+ reference solution)`; validator accepts only tasks whose broken state fails and reference solution passes | G1 | P0 | F-02 | 3 |
| FR-04 | Runner executes an agent as a black box in an isolated temp workspace with injected env vars; captures workspace diff; enforces timeout | G1 | P0 | F-03 | 4 |
| FR-05 | Grader runs visible + hidden pytest from a clean copy, restores protected test files (tamper check), returns pass/fail with details | G2 | P0 | F-04 | 5 |
| FR-06 | Three reference agents: A (no framework), B (framework), C (variant of A: different prompt/model/retry) | G1 | P0 | F-05 | 5, 8 |
| FR-07 | Repeat each (agent, task, scenario) N times; classify PASS/FAIL/INFRA_ERROR; retry INFRA_ERROR; record env fingerprint | G3 | P0 | F-06 | 6 |
| FR-08 | Stats: pass rate + Wilson CI; mean/median/std + bootstrap CI for cost, steps, tool calls, duration | G3 | P0 | F-07 | 6 |
| FR-09 | Benchmark checkpoint/resume after interruption; spend cap halts a benchmark | G3 | P0 | F-06 | 6 |
| FR-10 | REST API for benchmarks, runs, events, results, resilience, catalog | G6 | P0 | F-08 | 7 |
| FR-11 | Dashboard: leaderboard (with intervals), benchmark launcher/progress, compare view, run trace timeline | G6 | P0 | F-09 | 7 |
| FR-12 | ≥ 4 fault scenarios (outage, rate limit, broken tool, misleading instruction), seeded; resilience score; failure-scenario view | G4 | P0 | F-10 | 10 |
| FR-13 | Agent registration by one command with manifest auto-detect and `agent doctor`; `command` mode first | G1 | P1 | F-11 | 9 |
| FR-14 | Security baseline: canary secret, ≥ 1 prompt-injection task, out-of-workspace write / network attempt detection, security score + tab (sandbox hardening and behaviour monitor are FR-15, P0) | G5 | P2 | F-12 | 4, 12 |
| FR-15 | Hardened Docker sandbox (non-root, read-only rootfs, limits, network only to proxy) + behaviour monitor events (command, file_write, net_attempt) | G5 | P0 | F-03 | 4 |
| FR-16 | Grow suite to 8-10 tasks (hand-written + mutation generator), property-based tests, test-strength score, weak-task flag | G1 | P0 | F-02, F-17 | 8 |
| FR-17 | Model override in proxy; agent × model matrix with diagnostics | G1 | P2 | F-13 | 11 |
| FR-18 | `X-Agent-Role` attribution, per-role breakdown, trace tree; research + document-analysis categories; Tavily tool for one agent | G1 G8 | P2 for roles/tree/non-coding; **Tavily research agent P0 (D-13)** | F-14 | 13 |
| FR-19 | Record/replay cache, local model baseline, "replay this run" | G3 | P3 | F-15 | 14 |
| FR-20 | One-command setup, README quickstart, "how to add your agent", Limitations page, final benchmark, demo video | G7 | P0 (min) | F-16 | 15 |
| FR-21 | Environment fingerprint stored per run and shown on run detail | G3 | P0 | F-06 | 6 |
| FR-22 | Proxy-vs-Bifrost log reconciliation flag (plan Stage 6.4; feasibility depends on V-03) | G2 | P0 if V-03 allows, else documented gap | F-01 ext. | 6 |

## 4. Non-functional requirements

| ID | Requirement | Verification |
|---|---|---|
| NFR-01 | Contracts frozen at CP0; after that changes are additive-only unless all three owners ack ([10](10-integration-contracts.md) §6) | Contract change log |
| NFR-02 | Every component runnable and testable alone using mocks ([10](10-integration-contracts.md) §4) | T-01…T-10 |
| NFR-03 | Proxy overhead per call is small relative to LLM latency (target < 50 ms added, to be measured; **not yet measured**) | T-03 |
| NFR-04 | Dashboard loads leaderboard for a 2-agent × 5-task × 3-run benchmark in < 2 s locally (target) | T-18 |
| NFR-05 | No secrets in repo; provider key only via `.env`; `.env.example` committed | Review at CP4 |
| NFR-06 | Results are explicit statistics: every aggregate shows n and interval; INFRA exclusions are visible | UI test T-17 |
| NFR-07 | Accessibility baseline per [05](05-ux-spec.md) §7 | Manual checklist T-19 |
| NFR-08 | Total provider spend capped per benchmark (`spend_cap_usd`) | T-14 |

## 5. Scope definition (D-12)

**P0 = plan Stages 0-8, 10, 15** as the plan's Definition of Done states; nothing is pre-reduced. Gates and cut rules ([12](12-delivery-plan.md) section 4) handle slippage.

| Dimension | Target | Source |
|---|---|---|
| Agents | 3+ (A no-framework, B framework, C variant) | Plan DoD, Stages 5, 8 |
| Tasks | 8-10 (hand-written + mutation-generated), each validator-accepted | Stage 8 |
| Runs per cell | N >= 3 (default 5 if budget allows) | Stage 6 |
| Fault scenarios | >= 4 with resilience score | Stage 10 |
| Sandbox | Hardened Docker + behaviour monitor (subprocess first) | Stage 4 |
| Grading | visible + hidden + property-based + tamper check + test-strength | Stages 5, 8 |
| Registry + doctor | P1 (Stage 9) | Cut line |
| Security score + injection task | P2 (Stage 12); sandbox hardening already P0 | Cut line |
| Matrix / multi-agent / non-coding | P2 (Stages 11, 13) | Cut line |
| Replay / local model | P3 (Stage 14) | Cut line |

## 6. Non-goals

- Not a general LLM leaderboard; not a model-quality benchmark.
- Not a full security audit; not production-realistic failure simulation (stated on Limitations page).
- No user accounts, multi-tenancy, billing, or hosted SaaS.
- No agent modification or SDK required for black-box agents (reference agents may use our shared tools module).
- No proof of causality between model and agent effects (only decomposition via matrix, P2).
- No presentation content in this repo pack ([PPT_FRAMEWORK.md](PPT_FRAMEWORK.md) is a placeholder).

## 7. Acceptance criteria (product level)

| ID | Criterion | Maps to |
|---|---|---|
| AC-01 | A benchmark of 3 agents × 5 tasks × 3 runs completes and every run is stored with events, tokens, cost + confidence, status | FR-01…FR-09 |
| AC-02 | Leaderboard shows pass rate with CI, cost, steps, tool calls, time, n and INFRA exclusion count per agent | FR-08, FR-11 |
| AC-03 | Any run opens a timeline with every LLM call, tool call, error and injected fault in order | FR-01, FR-11 |
| AC-04 | Same agent shown under baseline and all 4 fault scenarios with resilience score | FR-12 |
| AC-05 | Killing the orchestrator mid-benchmark and restarting finishes without redoing completed runs | FR-09 |
| AC-06 | A task whose reference solution fails (or broken state passes) is rejected by the validator | FR-03 |
| AC-07 | An agent that edits a protected test file is flagged `tamper_detected` and graded FAIL | FR-05 |
| AC-08 | `docker compose up` + documented steps bring the system up on a clean machine | FR-20 |
| AC-09 | Limitations page lists the plan's honest limits | D-10, FR-20 |

Detailed demo acceptance: [09](09-testing-and-demo.md) §4.
