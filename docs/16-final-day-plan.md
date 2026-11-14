# 16 · Final-day plan (15 Nov): Dev-B work reassigned

> Status: **proposed 2026-11-15, cuts need team approval.** Authoritative for who owns the former Dev-B tasks and what is cut today. Task IDs, acceptance and estimates stay in [14](14-task-board.md); contracts in [10](10-integration-contracts.md) (§2.1 runner, §2.3 grader, §2.5 ordering).

## 1. Situation
- Submission window closes **15 Nov 2026 11:59 PM** (timezone not stated; confirm on the portal, OQ-03).
- Dev-B has made no commits, branch or PR. The runner, grader, task validator, orchestrator and tasks do not exist, so **no real benchmark run exists yet**. Everything else on our side is built and merged (proxy, API/stats, fault injection for 503/429, Bifrost+Groq, dashboard with live mode, three agents).
- Hence the only goal today: **one honest end-to-end benchmark with real data, then docs and submission.** Cut rules of [12](12-delivery-plan.md) §4 apply in full.

## 2. Split (two people, by interface so both can work at once)

**Dev-C (Yokshith): "task and execution side", file-based, no database**
| # | Task (board ID) | Deliverable | Interface it must meet |
|---|---|---|---|
| C-1 | B1 task format + validator + 5 hand-written tasks (B12) | `tasks/<id>/` folders per 07 §5; `grader/validate.py: validate(task_dir)` | 10 §2.4 |
| C-2 | B3 grader | `grader/grade.py: grade(task_dir, workspace_dir) -> GradeResult` (+ CLI). Clean copy, protected files restored, tamper flag, visible + hidden tests | 10 §2.3 |
| C-3 | B2 runner (subprocess) + B8 instruction fault | `runner/run.py: run_agent(spec) -> RunResult`; env vars per 10 §2.2; timeout and process-tree kill; unified diff; instruction fault applied to the temp workspace | 10 §2.1, §2.2 |
| C-4 | Agent manifests | `agents/*/agent.yaml` model = `groq/openai/gpt-oss-20b`; confirm `temperature: 0` is accepted | 07 §6 |
| C-5 | C10 + X12 docs and submission | README quickstart, Limitations, "add your agent", AI-usage statement, submission form text | rules (D-15) |
| C-6 | X10 demo rehearsal and video | Recording of the dashboard on real data | 09 §4 |

**Dev-A (Akhil): "orchestration and integration side", database**
| # | Task (board ID) | Deliverable | Interface it must meet |
|---|---|---|---|
| A-1 | Seed loader (part of B3) | Loads validated `tasks/*` and `agents/*` into the `tasks`/`agents` tables | 07 §5-6 |
| A-2 | B5 + B6 orchestrator | Polls queued benchmarks, expands slots, calls `run_agent` then `grade`, writes `agent_started` and `grader_result` events, finalises the run row from events, classifies PASS/FAIL/INFRA_ERROR, retries INFRA up to 3, resumes after restart, enforces the spend cap. **Develop against a stub runner and stub grader** (10 §4) until C-2 and C-3 land | 10 §2.5, F-06 |
| A-3 | X3 then X6 | First real run (Agent A x 1 task through compose), then the final benchmark with Groq, with spend watched | 09 §4 |
| A-4 | X7 + X9 | Demo data dump and fresh-clone check | 12 §2, §5 |

Shared files: `docker-compose.yml` (orchestrator service: Akhil), `agents/`, `tasks/`, `runner/`, `grader/` (Yokshith). Nobody else edits the other's folders without telling them.

## 3. Order of work (gates, no clock times because hours left are unknown)
1. **G1, interfaces agreed (now):** module paths and signatures above. Akhil confirms he can call them as written; any change goes to doc 10 first.
2. **G2, first real run:** C-1 (one task), C-2, C-3 done and merged; A-2 can start a run end to end with Agent A on Groq. Stop and verify the database rows, events and the dashboard.
3. **G3, full data:** 5 tasks validated; baseline benchmark (3 agents x 5 tasks x N=3); then the fault scenarios (503, 429 via proxy; tool fault via env; instruction fault via runner) on a subset sized from the measured cost and time of G2.
4. **G4, freeze and ship:** dump the database, finish README and Limitations, record the video, submit. Start G4 **no later than a few hours before the deadline**.

## 4. Proposed cuts (need your OK; the first six follow the cut order)
| Cut | Effect | Disclosed as |
|---|---|---|
| B4 Docker sandbox | Runner stays a subprocess | Limitations: no container hardening (cut rule 7) |
| A13 mutation generator, test-strength, property tests | 5 hand-written tasks instead of 8-10 | Limitations: task count below plan minimum 8 |
| Stage 9: A8 registry/doctor, C9 form | Agents added by folder + seed loader | README "add your agent" |
| A6 proxy-vs-Bifrost reconciliation | Cost comes from proxy only | Limitations: no cross-check |
| Stages 11-14 (A9-A11, B9, B10, C11-C13) | Security page has no data | Marked "future work" |
| X8 reduced to a 3-run spot check | | Limitations |
| **Tavily (C14 + B13), decision needed** | Keep only if G3 is complete with time to spare | If cut: unticked Tavily box, Bifrost-only submission (allowed by the rules) |

## 5. Decisions and inputs needed
1. Approve the cuts above (especially Tavily).
2. Hours available today for each of you, and the deadline in your timezone.
3. Model and budget for the final benchmark: `groq/openai/gpt-oss-20b` and a USD cap (Akhil holds the Groq key).
4. Who builds the **pitch deck** (required by the rules; the PPT stays outside this repo, see [PPT_FRAMEWORK](PPT_FRAMEWORK.md)).
5. If Tavily is kept: a Tavily key (Q6 in [15](15-open-questions.md)).

## 6. Human actions only you can do
- Send Akhil the split and ask for a branch/PR per task, pushed often.
- Make the repository **public** and join the official Discord before submitting.
- Record the demo video and submit the form (Bifrost benchmarking theme; Tavily box only if Tavily stays).
- Confirm the deadline timezone.
