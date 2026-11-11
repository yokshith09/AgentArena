# 11 · Team Execution Plan

> Status: Draft; names pending (OQ-04). Team = 3; skills not used for assignment (user instruction). Scope = the shared plan's full cut line (D-12): **P0 = Stages 0–8, 10, 15 · P1 = Stage 9 · P2 = Stages 11, 12, 13 · P3 = Stage 14.** Dates: [12](12-delivery-plan.md).

## 1. Workstreams (P-15)

| WS | Dev | Theme | Owns ([10](10-integration-contracts.md) §5) |
|---|---|---|---|
| A | **Dev-A** | Platform | DB/migrations, compose, Bifrost, `pricing.yaml`, `mock_llm`, proxy, provider faults, stats, API, reconciliation, mutation generator + test-strength |
| B | **Dev-B** | Execution | Task format, validator, grader, seed loader, runner, Docker sandbox + monitor, orchestrator, instruction fault, hand-written tasks, registry + `doctor` |
| C | **Dev-C** | Experience | Dashboard + mocks, reference agents A/B/C + `agents/common`, tool-fault hook, docs steward, demo |

Names → A/B/C open (OQ-04): A=__, B=__, C=__.

## 2. Tasks
Authoritative list (IDs, owners, estimates, acceptance, tests, status): [14 Task Board](14-task-board.md). Not duplicated here.

## 3. Reviewers & fallbacks

| Work of | Reviewed by | Fallback owner |
|---|---|---|
| Dev-A | Dev-B | Dev-B (proxy), Dev-C (API wiring) |
| Dev-B | Dev-C | Dev-A (orchestrator, grader), Dev-C (tasks) |
| Dev-C | Dev-A | Dev-B (agents), Dev-A (UI data wiring) |

`contract` PRs need both other owners. Others: named reviewer, or self-merge with passing tests if reviewer blocked > 1 h (logged in PR).

## 4. Checkpoints
Milestones, windows and gates (re-baselined 2026-11-12): [PROJECT_ROADMAP.md](../PROJECT_ROADMAP.md) §3. Operating rules (branching, PR, merge checks): [HACKATHON_PLAN.md](../HACKATHON_PLAN.md) §4.

## 5. Working agreements
- Trunk-based, short branches (repo not yet git, OQ-09). Decisions go into [01](01-hackathon-strategy.md), not chat.
- Blocked > 1 h → say so; fallback owner picks up.
- Daily start-of-day sync + CP sync; status line in `HACKATHON_PLAN.md`.
- Honest load warning: Dev-B carries the heaviest path (runner → Docker → orchestrator → generator). Dev-A takes B's overflow (grader, orchestrator pieces) once A5 is done.
