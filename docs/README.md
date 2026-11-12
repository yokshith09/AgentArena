# AgentArena · Documentation Pack

Status: **Draft for CP0 sign-off (2026-11-11).** The documentation describes the target system; foundation implementation is underway. Current task status is tracked in [14 · Task Board](14-task-board.md).

## Read order by role

| If you are… | Read |
|---|---|
| Anyone, first | [01 Strategy & decision register](01-hackathon-strategy.md) → [02 PRD](02-prd.md) |
| Dev-A Platform | [04 TRD](04-trd-architecture.md), [07 Schema](07-data-schema.md), [08 API](08-api-contracts.md), [10 Integration](10-integration-contracts.md) |
| Dev-B Execution | [03 Features](03-feature-specs.md) (F-02…F-06, F-10), [07](07-data-schema.md) §5–7, [10](10-integration-contracts.md) |
| Dev-C Experience | [05 UX](05-ux-spec.md), [06 Flow](06-app-flow.md), [08](08-api-contracts.md) §3–4, [10](10-integration-contracts.md) §4 |
| Reviewer / lead | [09 Testing & demo](09-testing-and-demo.md), [11 Team plan](11-team-execution-plan.md), [12 Delivery plan](12-delivery-plan.md), [13 Traceability](13-traceability.md), [14 Task board](14-task-board.md), [PROJECT_ROADMAP](../PROJECT_ROADMAP.md) |

## Index

| # | Doc | Authoritative for |
|---|---|---|
| 01 | [Hackathon strategy](01-hackathon-strategy.md) | Problem, constraints, **decisions (D), proposals (P), assumptions (A), open questions (OQ)** |
| 02 | [PRD](02-prd.md) | Users, requirements FR/NFR, priorities, scope, non-goals, acceptance criteria |
| 03 | [Feature specs](03-feature-specs.md) | Behaviour per feature F-01…F-17 |
| 04 | [TRD / architecture](04-trd-architecture.md) | Components, stack, data flow, deployment, risks, Bifrost verification list |
| 05 | [UI/UX spec](05-ux-spec.md) | Screens, navigation, states, responsive, accessibility |
| 06 | [Application flow](06-app-flow.md) | Primary journey, failure paths, state machines |
| 07 | [Data schema & migrations](07-data-schema.md) | Tables, enums, metric definitions, task/agent/fault/pricing formats |
| 08 | [API contracts](08-api-contracts.md) | HTTP routes, errors, response types, mock payloads |
| 09 | [Testing & demo acceptance](09-testing-and-demo.md) | Test catalog T-xx, demo criteria DA-xx |
| 10 | [Integration contracts](10-integration-contracts.md) | Component I/O, env/runner/grader interfaces, mocks, repo ownership, change rules |
| 11 | [Team execution plan](11-team-execution-plan.md) | Workstreams, tasks, reviewers, fallbacks, checkpoints |
| 12 | [Delivery plan](12-delivery-plan.md) | Schedule, scope-cut rules, deployment, demo-critical path |
| 13 | [Traceability](13-traceability.md) | Criterion → requirement → feature → owner → test → evidence |
| 14 | [Task board](14-task-board.md) | Task IDs, owners, estimates, acceptance, tests, status |
| 15 | [Open questions](15-open-questions.md) | Expanded OQs with options, defaults and recorded answers |
| — | [PROJECT_ROADMAP](../PROJECT_ROADMAP.md) | Current focus, audit, milestones, criteria map |
| — | [HACKATHON_PLAN](../HACKATHON_PLAN.md) | Allocation, dependency graph, SDLC rules, risks, cuts |
| — | [PPT framework](PPT_FRAMEWORK.md) | Placeholder, supplied separately |

Source material: `AgentArena_Complete_Plan.md` (team plan, outside this repo).

## Conventions
- One authoritative definition per interface (see 10 §3.1). Other docs link, never restate.
- Tags: **D** approved · **P** proposed · **A** assumption · **OQ** open question; **[plan]**/**[P]** on schema fields.
- IDs: G goals · FR/NFR · F features · T tests · DA demo acceptance · CP checkpoints · V Bifrost checks · R risks.
