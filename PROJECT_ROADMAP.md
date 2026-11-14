# PROJECT_ROADMAP · AgentArena

Status: Draft v1 · Last updated 2026-11-12 · Deadline 2026-11-15 · Team 3 (Dev-A, Dev-B, Dev-C; names open, OQ-04). Planning and foundation implementation are underway. This plan does not guarantee success: planned P0 load (≈ 42 h per developer, midpoint estimates) is high against three working days — see [docs/14-task-board.md](docs/14-task-board.md) load table and the cut rules.

Authority: tasks/owners/status → [docs/14-task-board.md](docs/14-task-board.md) · contracts → docs 07/08/10 · decisions → [docs/01](docs/01-hackathon-strategy.md) · team operating rules, dependency graph, risks → [HACKATHON_PLAN.md](HACKATHON_PLAN.md).

## 1. Current Focus

**Active milestone: M0 — Foundation & contracts (Stages 0–1). Window: 12 Nov morning → CP0 gate midday.**

Do now, in this order:
1. **X2** repo bootstrap (Dev-A, ≤ 1 h) — everything needs a repo.
2. **X1** contract sign-off v1 + answer/default open questions (Dev-A drives, all ack).
3. In parallel as soon as X1 is signed: A12/A1 (Bifrost + V-01/V-02), A2 (DB), A3 (`mock_llm`), C1 (UI scaffold on fixtures), B1 (task format + validator).

Nothing else starts until its contract (X1) exists. Only one milestone is active at a time; the next one opens when the current gate passes (or when a time-box expires and the cut rules are applied).

## 2. Progress audit (2026-11-12)

| Class | Items |
|---|---|
| Implemented | **X2** repository bootstrap and skeleton; **A3** scripted `mock_llm` (standalone integration check passes). Contract schemas, DB migration/fixtures, compose config, and smoke/check scripts are present. |
| In progress | **X1** contracts 07/08/10 drafted, unsigned; **A12** compose config present but services not started; **A2** migration/fixtures present but DB check not run. |
| Planned | All tasks in the [board](docs/14-task-board.md) except those below. |
| Blocked / waiting | A1 (needs provider key and model, OQ-05) · B4 Docker sandbox (needs Docker confirmed, OQ-08) · C14 needs a Tavily key (OQ-13). No P0 implementation task should start until X1 is signed off. |
| Unknown | Whether any work from 1–11 Nov exists outside this folder (OQ-12). If it does, re-audit before M0. |

## 3. Milestones

Ordered by dependency first, then demo importance, then technical uncertainty (Bifrost, framework agent, Docker go early), then rubric impact. Windows are half-day boxes because working hours are unknown (A-03).

| MS | Window → gate | Stages | User value | Tasks | Exit gate (must be true) | Plan milestone |
|---|---|---|---|---|---|---|
| **M0** | 12 Nov AM → CP0 midday | 0, 1 | Team can work in parallel without interface guesswork | X2, X1, A12, A1, A2, A3, C1, B1 | Contracts v1 signed; V-01 + V-02 evidenced; compose, DB, `mock_llm` up; UI renders every route from fixtures; validator accepts 2 tasks | — |
| **M1** | 12 Nov midday → CP1 EOD | 2, 3, 4 (subprocess), 5 | A single run is measured and graded end to end | A4, B2, B3, C2, C3, C4, X3 | Agent A × 1 task: run row, events, tokens, cost, status in DB; T-01, T-06, T-07, T-08, T-10, T-11 pass | **Milestone 1** |
| **M2** | 13 Nov AM → CP2 midday | 6, 7 | Statistical comparison visible in a live dashboard | A5, A6, B5, B6, B12, C5, X4, X5 | Tiny benchmark completes via compose; live Leaderboard + Run detail + Compare; kill/resume works; T-13…T-16, T-29, T-30 pass | **Milestone 2** |
| **M3** | 13 Nov midday → CP3 EOD | 4 (hardening), 8, 10 | Trust (hardened sandbox, strong tasks) and failure behaviour | B4, A13, B12, B13, C7, C14, B8, A7, C8, X6 | 8–10 validated tasks; 3 agents; 4 faults + resilience view; Docker sandbox (or documented fallback); final benchmark launched; T-09, T-20, T-21, T-28 pass | **Milestone 3** |
| **M4** | 14 Nov AM → CP4 midday | 9 | Easy onboarding of new agents; data trustworthy | A8, C9, X7, X8 | **Feature freeze.** Registry + doctor (T-22) or cut; final data complete, dumped, audited; all P0 tests pass | — |
| **M5** | 14 Nov midday → CP5 EOD | 15 | Judges can run and understand it | C10, X9, X10, X11 | README works on a clean machine (T-27); Limitations; demo rehearsed twice; video recorded; submit-ready | — |
| Buffer | 15 Nov | — | Reliability | blocker fixes only | Submission made | — |
| Stretch | only if the previous gate is green and owner is idle | 11–14 | Differentiators | A9, A10, A11, B9, B10, C11, C12, C13 | Frozen at CP4 with everything else | — |

Integration is continuous, not final: every milestone ends with an integration task (X3, X5, X6) run through the real compose stack; `main` stays runnable ([HACKATHON_PLAN.md](HACKATHON_PLAN.md) §4).

### Time buffers and test/fix/deploy/rehearsal time
- Last hour of every day: integration + fix slot, no new tasks.
- M3 → M4: overnight final benchmark run (decision on size at CP2 from measured cost/time).
- Deployment (compose from a clean clone): X9 in M5. Rehearsals: two in X10; second after any hotfix.
- 15 Nov: blockers and submission only.

## 4. Epics and user stories

| Epic | Stories (acceptance = see feature in [docs/03](docs/03-feature-specs.md)) | Stage |
|---|---|---|
| E1 Foundation | **US-01** As a team we work from frozen contracts and a shared repo. **US-02** As an operator I can send an LLM request through Bifrost and read the result. | 0, 1 |
| E2 Measurement | **US-03** As an operator every agent LLM call is logged with tokens, cost and latency. | 2 |
| E3 Tasks & grading | **US-04** As an author I can only add tasks that are sound. **US-06** As a judge I can trust pass/fail. **US-13** As an author I get 8–10 tasks, some generated, with weak ones flagged. | 3, 5, 8 |
| E4 Execution | **US-05** As an operator an agent runs isolated with a captured diff and monitored behaviour. **US-08** As an operator I launch a matrix and trust it to finish, resume, and stay in budget. | 4, 6 |
| E5 Agents | **US-07** As a developer I have three agents with real differences to compare. | 5, 8 |
| E6 Statistics & API | **US-09** I see intervals, not bare percentages. **US-10** The dashboard reads stable endpoints. | 6, 7 |
| E7 Dashboard | **US-11** I see leaderboard, compare, run trace, failure view, limitations. | 7, 10 |
| E8 Failure injection | **US-12** I see the same agent normally vs under outage, rate limit, broken tool, misleading instruction. | 10 |
| E9 Registry | **US-14** I add an agent with one command and learn what is wrong with it. | 9 |
| E10 Differentiators | **US-15** Model-vs-agent, security score, multi-agent, non-coding, replay. | 11–14 |
| E11 Delivery | **US-16** A judge can run it, read the limits, and watch the demo. | 15 |

## 5. Judging criteria → feature → evidence → demo point

**Official judging criteria (hackathon rules, 2026-11-12):** Innovation · Technical execution · Problem and potential impact · Use of AI · User experience · Scalability and potential. No weights were given. Official-criteria trace: [docs/13](docs/13-traceability.md) (bottom table). The table below keeps the derived G1-G8 order used for the demo walkthrough; the five mandatory requirements of Problem 02 are covered by rows 2-5.

| Order | Criterion (derived) | Feature | Test / evidence | Demo point |
|---|---|---|---|---|
| 1 | G7 reproducible setup | F-16 | T-27, T-29; DA-01 | One-command start, health OK |
| 2 | G1 framework-independent, identical tasks | F-02, F-03, F-05 | T-06, T-08, T-11; DA-02 | Leaderboard lists 3 agents (plain, framework, variant) on the same tasks |
| 3 | G2 metrics recorded; G3 reliability | F-01, F-06, F-07 | T-01, T-13, T-15; DA-02, DA-09 | Pass rate with interval, cost + confidence label, steps, tool calls, time, n, INFRA excluded |
| 4 | G6 comparisons | F-08, F-09 | T-16, T-18; DA-03 | Compare view with "no clear difference" labelling |
| 5 | G6 step-by-step traces | F-09 | T-17; DA-04 | Open a failed run: timeline, diff, grader result |
| 6 | G4 controlled failures | F-10 | T-20, T-21; DA-05 | Failure matrix: baseline vs 4 faults + resilience score; fault event in a timeline |
| 7 | G5 security behaviour (baseline) | F-03 monitor (P0), F-12 (P2) | T-09 (+T-23 if built); DA-11 | Blocked network attempt logged; injection result only if F-12 built |
| 8 | G3 resilience of the platform | F-06 | T-14; DA-06, DA-07 | Launch small benchmark live; show resume (rehearsed) |
| 9 | G8 Bifrost + Tavily | F-01, F-14 | V-01, T-29, T-25; DA-12 | Proxy → Bifrost path shown in architecture/trace; Tavily research agent (C14, D-13) shown in trace |
| 10 | G7 honesty | F-16 | DA-08 | Limitations page |

## 6. Scope-cut candidates and fallbacks (summary; full rules in [docs/12](docs/12-delivery-plan.md) §4)

Cut bottom-up: Stage 14 → 13 → 12 extras → 11 → Stage 9 UI/doctor → Stage 8 extras (task count to 8, drop strength/Hypothesis) → Docker hardening (subprocess fallback) → final benchmark size. Never cut: Stages 0–7, ≥ 4 faults, Stage 15, interval/n/INFRA visibility, MOCK ribbon, three agents. External-service fallbacks and risk table: [HACKATHON_PLAN.md](HACKATHON_PLAN.md) §6.

## 7. Presentation
Out of scope here. [docs/PPT_FRAMEWORK.md](docs/PPT_FRAMEWORK.md) is an untouched placeholder, "To be supplied separately".
