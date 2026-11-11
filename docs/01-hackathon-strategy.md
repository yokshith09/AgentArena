# 01 · Hackathon Strategy, Constraints & Decision Register

> Status: **Draft for CP0 sign-off** · Last updated: 2026-11-11
> Source of truth for: problem statement, constraints, **decision register (D / P / A / OQ)**. Other docs reference IDs from here; they do not restate them.

## 1. Problem and selected solution

| Item | Value | Source |
|---|---|---|
| Event | Global AI Hackathon (GEEK Room) · Problem Statement 02 · Bifrost by Maxim AI | Plan header |
| Team | 3 members (user instruction). The plan names two: Duggineni Akhil, Kuchipudi Yokshith. Third member unnamed → see OQ-04 | User message, Plan |
| Build window / deadline | 1–15 Nov 2026 · judging 29 Nov 2026 | Plan |
| Today | 2026-11-11 → **4 days remain** (11, 12, 13, 14) + 15 Nov as submission buffer | Environment date |
| Repository state | Empty, not a git repo, no `docs/` before this pack | Inspected 2026-11-11 |
| Problem | Benchmarks score models; products ship agents (model + prompts + tools + memory + retries). Developers need a fair, repeatable way to compare agents head-to-head, see what happens when things break, and understand why one beats another. | Plan §1 |
| Selected solution | **AgentArena**: framework-independent platform that runs any agent as a black box on identical tasks through a measuring proxy (→ Bifrost), grades outcomes, repeats runs for statistics, injects controlled faults, checks security behaviour, and shows comparisons with step-by-step traces. | Plan §1–2 |

`docs/01-hackathon-strategy.md` was referenced by the request but did not exist; this file is created from the shared plan `AgentArena_Complete_Plan.md` (user's Downloads folder). **The official judging rubric and submission rules were not in the shared material** (OQ-01, OQ-03). Goals G1–G8 below are *derived* from the problem statement and the plan's Definition of Done and stand in for rubric criteria until OQ-01 is answered.

## 2. Derived goals (stand-in for rubric criteria)

| ID | Goal (derived) | Plan basis |
|---|---|---|
| G1 | Run different agents (framework / no framework / team) on identical tasks, framework-independently | §1 goal, loophole 4 |
| G2 | Record success, steps, tool calls, tokens, cost, time per run | §1 goal |
| G3 | Repeat runs and report reliability statistically | §1 goal, loophole 11 |
| G4 | Inject controlled failures and compare against baseline | §1 goal, loophole 12, "mandatory requirement" in §5 |
| G5 | Check security behaviour (baseline) | §1 goal, loophole 14 |
| G6 | Present comparisons with step-by-step execution traces | §1 goal, Stage 7 |
| G7 | Reproducible, one-command setup, honest limitations, demo | Stage 15, Definition of Done |
| G8 | Use Bifrost (and Tavily if required) as integration | Problem sheet per plan Stage 0 |

## 3. Decision register

Legend — **D** Approved (stated in the team's plan or by the user) · **P** Proposed by this doc pack, needs sign-off at CP0 · **A** Assumption (unverified) · **OQ** Open question.

### 3.1 Approved decisions (D)

| ID | Decision | Source |
|---|---|---|
| D-01 | Agents are measured as **black boxes**; every LLM call goes through our proxy, which forwards to Bifrost | Plan §2 |
| D-02 | Stack: FastAPI (proxy + API), Postgres, React dashboard, Docker Compose; Python for backend tooling (pytest/Hypothesis named in plan) | Plan §2, Stage 0–1 |
| D-03 | Run outcome `status` ∈ {PASS, FAIL, INFRA_ERROR}; INFRA_ERROR is retried and excluded from agent statistics | Plan loophole 9, Stage 6 |
| D-04 | Stats: pass rate with Wilson interval; cost/time with bootstrap intervals; mean/median/std | Plan Stage 6 |
| D-05 | Cost = tokens (provider `usage`) × versioned `pricing.yaml`; label `cost_confidence` ∈ {verified, estimated} | Plan loophole 10 |
| D-06 | Layered grading with test-tampering check (tests restored from clean copy) | Plan loophole 5, Stage 5 |
| D-07 | Faults are YAML, seeded, in four groups: provider, tool, instruction, environment | Plan loophole 12 |
| D-08 | Shared data contract fields for Run, Event, Task, Agent manifest as listed in plan §2 | Plan §2 |
| D-09 | Cut line: Stages 0–8 must; 10 and 9 strongly recommended; 11–13 differentiators; 14 polish; **15 never skipped** | Plan §5 |
| D-10 | Honest limits are published on a Limitations page | Plan Stage 15 |
| D-12 | **Full plan scope kept** (user decision 2026-11-11): Stages 0-8, 10, 15 = P0; Stage 9 = P1; Stages 11-13 = P2; Stage 14 = P3. Parallelised over 3 developers; no up-front scope compression | User message |
| D-13 | **Tavily is required** (user, 2026-11-12): a Tavily search tool is wired into a reference research agent as P0 (tasks C14, B13). Remaining unknowns: key, budget, exact integration expectation → OQ-13, OQ-14 | User message |
| D-11 | PPT framework is supplied separately; this pack contains only a placeholder | User message |

### 3.2 Proposals (P) — need sign-off at CP0 (2026-11-11 EOD)

| ID | Proposal | Why | Defined in |
|---|---|---|---|
| ~~P-01~~ | Withdrawn - superseded by D-12 (full scope kept). Time risk remains (4 days left) and is handled by gates and cut rules, [12](12-delivery-plan.md) §4 | - | - |
| P-02 | Run ID travels in the **proxy URL path**: `OPENAI_BASE_URL={PROXY}/runs/{run_id}/v1`; `X-Agent-Role` stays an optional header | Most agent SDKs honour only a base URL env var, not custom headers | [08](08-api-contracts.md) §2 |
| P-03 | **Proxy writes `events` only**; the orchestrator is the single writer that finalises the `runs` row (aggregates from events) | Avoids write races and double counting | [07](07-data-schema.md), [10](10-integration-contracts.md) |
| P-04 | Add to `runs`: `benchmark_id`, `repeat_index`, `attempt`, `state`, `started_at`, `finished_at`, `grader_result`, `workspace_diff`, `error` | Needed for resume, INFRA retry, UI detail | [07](07-data-schema.md) |
| P-05 | Metric definitions: `steps` = count of successful (2xx) `llm_call` events; `tool_calls` = count of `tool_call` events (calls the model *requested*); `duration` = agent process wall time (grading excluded) | One definition, no dashboard drift | [07](07-data-schema.md) §4 |
| P-06 | API surface in doc 08, with one `/results` endpoint serving both leaderboard and compare | Fewer contracts to keep in sync | [08](08-api-contracts.md) |
| P-07 | No authentication; local single-user deployment; CORS limited to dashboard origin | Hackathon scope; no user data | [08](08-api-contracts.md) §1 |
| P-08 | Tool-fault delivery: env var `ARENA_TOOL_FAULT` honoured by a shared tools module used by **our reference agents only**; third-party agents report provider + instruction faults only | Black-box agents have no tool hook | [03](03-feature-specs.md) F-10 |
| P-09 | Build the sandbox subprocess-first (plan risk table), then harden in Docker (plan Stage 4, P0) | Early end-to-end run, then plan-complete sandbox | [03](03-feature-specs.md) F-03 |
| P-10 | Repo layout and ownership as in [10](10-integration-contracts.md) §5 | Parallel work, conflict control | [10](10-integration-contracts.md) |
| P-11 | Mocks: `mock_llm` scripted upstream (Dev-A) + static JSON fixtures for the UI (Dev-C) | Parallel build, zero API cost during dev | [10](10-integration-contracts.md) §4 |
| P-12 | Fault catalog = 4 entries: `provider_503_outage`, `provider_429_ratelimit`, `tool_run_tests_error`, `instruction_misleading_hint` | Matches plan Milestone 3 | [03](03-feature-specs.md) F-10 |
| P-13 | Task folder adds `task.yaml` (id, category, faults_allowed) and `hidden_tests/` outside the agent workspace | Plan layout lacks a metadata file and a hidden-test location | [03](03-feature-specs.md) F-02 |
| P-14 | Orchestrator is a separate Python process that polls the DB for `queued` benchmarks | Simplest; survives API restarts; enables resume | [04](04-trd-architecture.md) |
| P-15 | Workstreams Dev-A Platform / Dev-B Execution / Dev-C Experience | Balances load, minimises shared files | [11](11-team-execution-plan.md) |
| P-16 | Resilience score = pass rate under fault ÷ baseline pass rate (null if baseline = 0) | Plan says "performance under fault ÷ baseline"; pass rate chosen as performance | [03](03-feature-specs.md) F-10 |
| P-17 | Extra runner→agent env vars: `OPENAI_API_KEY` (dummy), `ARENA_MODEL`, `ARENA_TOOL_FAULT` | Reference agents need a model name and fault hook | [10](10-integration-contracts.md) §2 |

### 3.3 Assumptions (A)

| ID | Assumption | Verify by |
|---|---|---|
| A-01 | Bifrost exposes an OpenAI-compatible chat-completions endpoint | Stage 0 / CP0 (V-01) |
| A-02 | Streaming usage is available if the proxy sets `stream_options.include_usage` and Bifrost passes it through | V-02 |
| A-03 | All 3 developers are available full-time 11–14 Nov (hours unknown) | Team confirm at kickoff |
| A-04 | Demo runs locally via `docker compose up`; no hosted deployment | OQ-11 |
| A-05 | One provider key and one cheap model suffice for all benchmarks | OQ-05 |
| A-06 | Dev machines include Windows (this workspace is Windows 11); backend code must be OS-agnostic Python; Linux containers via Docker Desktop | Kickoff check |
| A-07 | Dashboard built with React + a standard bundler (Vite assumed) and no charting dependency required for P0 | OQ-10 |
| A-08 | Token estimation fallback (for `estimated` cost) uses an off-the-shelf tokenizer library chosen by Dev-A | P1 task |

### 3.4 Open questions (OQ)

| ID | Question | Owner | Needed by | Impact |
|---|---|---|---|---|
| OQ-01 | What is the official judging rubric (criteria + weights)? | Team lead | CP0 | Re-map [13](13-traceability.md) rows |
| OQ-02 | ~~Is Tavily required?~~ **Resolved 2026-11-12: yes (D-13).** Follow-ups in OQ-13/OQ-14 | — | — | Tavily tool is P0 |
| OQ-03 | Submission format, cutoff time on 15 Nov, demo-video length/limits? | Team lead | CP0 | Delivery buffer, F-16 |
| OQ-04 | Name of the third team member; confirm Dev-A/B/C assignment | Team | CP0 | [11](11-team-execution-plan.md) owners |
| OQ-05 | Which provider/model and what dollar budget for all benchmark runs (spend cap defaults)? | Dev-A | CP0 | `pricing.yaml`, `n_runs`, task count |
| OQ-06 | Bifrost verification results V-01…V-06 (see [04](04-trd-architecture.md) §6) | Dev-A | CP0 | Log reconciliation (P1/P2) feasibility |
| OQ-07 | Is the tool-fault mechanism in P-08 acceptable, or is a runner-side PATH shim preferred? | Dev-B | CP0 | F-10 |
| OQ-08 | Is Docker Desktop available on every dev/demo machine (needed for compose and the Stage 4 hardened sandbox)? | Team | CP0 | F-03, deployment |
| OQ-09 | `git init` + remote location and branch policy? | Team | CP0 | [11](11-team-execution-plan.md) §5 |
| OQ-10 | Chart library / bundler preferences for dashboard | Dev-C | 12 Nov | UI effort |
| OQ-11 | Does the demo need a hosted URL, or is local acceptable? | Team lead | CP0 | [12](12-delivery-plan.md) §5 |
| OQ-12 | Does any code/asset from 1–10 Nov exist outside this folder? | Team | CP0 | Scope baseline |
| OQ-13 | Tavily account/key/quota and how it is shared | Dev-C | M1 | C14 |
| OQ-14 | What exactly does the problem sheet require for "Bifrost + Tavily"? | Dev-C | M1 | DA-12, scope of C14 |

Full wording, options and defaults for every OQ, and the place to record answers: [15 Open questions](15-open-questions.md). Answers are never recorded only in chat.
