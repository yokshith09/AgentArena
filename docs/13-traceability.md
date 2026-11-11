# 13 · Traceability Matrix

> Chain: **Rubric criterion → Requirement → Feature/Story → Component/Owner → Test → Demo evidence.**
> The official rubric is unknown (OQ-01). "Criterion" = derived goals G1–G8 ([01](01-hackathon-strategy.md) §2). When the rubric arrives, replace the first column; rows stay. Story = the story line inside each feature in [03](03-feature-specs.md). Test results live only in [09](09-testing-and-demo.md).

| Criterion | Requirement | Feature / story | Component · owner | Tests | Demo evidence | Pri |
|---|---|---|---|---|---|---|
| G1 framework-independent | FR-04 black-box runner | F-03 | RN · B | T-08, T-09 | DA-04 | P0 |
| G1 | FR-06 three agents (no-framework / framework / variant) | F-05 | AG · C | T-11, T-12 | DA-02, DA-03 | P0 |
| G1 | FR-03 identical sound tasks | F-02 | TK/GR · B | T-06 | DA-02 | P0 |
| G1 | FR-13 register + doctor | F-11 | RG · B (UI C) | T-22 | DA-10 | P1 |
| G1 | FR-16 8-10 tasks, strength, weak flag | F-02, F-17 | TK · B+A | T-06, T-28 | DA-02 | P0 |
| G1 | FR-17 model vs agent effect | F-13 | PX/API · A | T-24 | — | P2 |
| G2 record metrics | FR-01 proxy logging | F-01 | PX · A | T-01…T-05 | DA-04 | P0 |
| G2 | FR-02 cost + confidence | F-01 | PX · A | T-01, T-15 | DA-09 | P0 |
| G2 | FR-05 trustworthy grading | F-04 | GR · B | T-07, T-10 | DA-04 | P0 |
| G2 | FR-22 proxy-vs-Bifrost reconciliation | F-01 ext. | PX · A | (test added once V-03 known) | — | P0 if V-03 allows |
| G3 reliability | FR-07 repeats + INFRA handling + fingerprint (FR-21) | F-06 | OR · B | T-13 | DA-06 | P0 |
| G3 | FR-08 intervals | F-07 | API/stats · A | T-15 | DA-02 | P0 |
| G3 | FR-09 resume + spend cap | F-06 | OR · B | T-14 | DA-07 | P0 |
| G3 | FR-19 replay/local model | F-15 | PX · A | T-26 | — | P3 |
| G4 controlled failures | FR-12 4 faults + resilience + view | F-10 | PX · A, RN · B, AG · C | T-20, T-21 | DA-05 | P0 |
| G5 security | FR-14 canary + injection task + score | F-12 | RN/GR · B, API · A | T-23 | DA-11 | P2 |
| G5 | FR-15 hardened sandbox + behaviour monitor | F-03 | RN · B | T-09 | DA-04 | P0 |
| G6 comparisons + traces | FR-10 API | F-08 | API · A | T-16, T-30 | DA-02 | P0 |
| G6 | FR-11 dashboard (leaderboard, compare, run trace) | F-09 | UI · C | T-17, T-18, T-19 | DA-02, DA-03, DA-04 | P0 |
| G6 / multi-agent | FR-18 roles, trace tree | F-14 | PX/UI · A+C | T-25 | — | P2 |
| G7 setup, docs, demo | FR-20 compose, README, Limitations, video | F-16 | all · C steward | T-27, T-29 | DA-01, DA-08 | P0 |
| G8 Bifrost (+Tavily) | Bifrost routing (D-01) | F-01 | PX/BF · A | T-01, T-29, V-01 | DA-01 | P0 |
| G8 | Tavily tool for research agent (D-13) | F-14 | AG · C (C14), GR · B (B13) | T-11, T-25 | DA-12 | P0 (D-13) |

Coverage check: every FR in [02](02-prd.md) §3 appears above (FR-01…FR-22; FR-21 within FR-07 row). Every P0 test T-01…T-21, T-27, T-29, T-30 appears at least once here or in [09](09-testing-and-demo.md) §2 (T-30 covered under G6 row).
