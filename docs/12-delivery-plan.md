# 12 · Delivery Plan

> Status: Draft. Scope decision D-12: team keeps the **full plan** (Stages 0–8, 10, 15 P0; 9 P1; 11–13 P2; 14 P3), parallelised across 3 developers. Today = 2026-11-11, build deadline 15 Nov; submission cutoff time unknown (OQ-03) → treat **14 Nov EOD as the real deadline**, 15 Nov as buffer.

## 1. Sequencing
Milestones, windows, per-task lanes: [PROJECT_ROADMAP.md](../PROJECT_ROADMAP.md) §3 and [14 Task Board](14-task-board.md) (re-baselined 2026-11-12: CP0 midday 12 Nov, CP1 12 Nov EOD, CP2 13 Nov midday, CP3 13 Nov EOD, CP4 14 Nov midday = freeze, CP5 14 Nov EOD, 15 Nov buffer). Not duplicated here.

## 2. Stabilisation buffer
Sat PM + Sun are buffer. After CP4: bug fixes only, each with a failing test first. Final benchmark launched at CP3 so data exists before freeze; one rerun allowed. Frozen demo data kept as a DB dump `db/demo-data.sql` (proposal, owner A), restored by README steps, so the demo never depends on a live provider.

## 3. Final benchmark sizing (decide at CP2 from measured run time and cost)
Plan DoD minimum: ≥ 3 agents × ≥ 8 tasks × N ≥ 3 baseline, plus ≥ 4 fault scenarios. Example: 3 × 8 × 3 = 72 baseline runs; faults on all 8 tasks = 3 × 8 × 4 × 3 = 288 more (360 total). Per-run time and cost are **unmeasured**. Rule: `runs × measured mean cost ≤ 50% of budget` (OQ-05) and `runs × mean duration ÷ parallelism ≤ 3 h`; if not, shrink fault coverage to a task subset first (never below 4 scenarios, N ≥ 3).

## 4. Cut rules (plan §5 cut line; cut from the bottom up)

| Order | Cut | Trigger | Disclosure |
|---|---|---|---|
| 1 | Stage 14 (replay, Ollama) | any P0/P1 slip | Future work |
| 2 | Stage 13 (multi-agent, non-coding, Tavily) | CP3 not green (Tavily research agent C14 + B13 are P0, D-13, and are not cut) | Future work |
| 3 | Stage 12 security extras | CP3 not green | Limitations: sandbox hardening (Stage 4) remains; no security score |
| 4 | Stage 11 model matrix | CP3 not green | Future work |
| 5 | Stage 9 registry UI form, then `doctor`, then whole stage | CP4 at risk | README manual "how to add your agent" |
| 6 | Stage 8 reduced: tasks 10 → 8, drop test-strength, drop Hypothesis | CP3 slip | State actual task count; 8 is the plan minimum |
| 7 | Stage 4 Docker hardening falls back to subprocess | OQ-08 (no Docker) or CP2 slip > 0.5 d | Limitations, DoD gap stated |
| 8 | Final benchmark size (§3) | cost/time | Wider intervals shown |

**Never cut:** Stages 0–7, Stage 10 with ≥ 4 faults, Stage 15 (README, Limitations, demo), intervals/n and INFRA visibility, MOCK ribbon, the three reference agents.

## 5. Deployment plan (A-04, OQ-11)
1. `docker compose up` (services: TRD §7); `.env` from `.env.example`.
2. Migrations, then seed loader loads validated tasks and agents.
3. Demo: restore `db/demo-data.sql`; live launch of a small benchmark available for DA-06.
4. Local only, ports on localhost. Rollback: `docker compose down -v` + restore dump.
Pre-demo checklist: provider key valid (or labelled `mock_llm` mode), Docker running, disk space, dump backed up off-machine.

## 6. Demo-critical path
V-01 → proxy events (T-01) → runner + Docker sandbox + grader (T-07…T-09) → Agent A (CP1) → orchestrator (T-13/T-14) → stats/API (T-15/T-16) → leaderboard + trace UI (T-17/T-18) → faults + resilience (T-20/T-21) → final data (CP4) → docs/video (CP5).

## 7. Watchpoints
Daily: provider spend vs cap, hours of CP slip, count of `not run` P0 tests. Risks: TRD §9.

## 8. Submission package (assumed; confirm OQ-03)
Repo with README + docs, demo video, final data dump, Limitations page. PPT supplied separately ([PPT_FRAMEWORK.md](PPT_FRAMEWORK.md)).
