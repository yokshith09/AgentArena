# 05 · UI/UX Specification

> Status: Draft. Data shown comes only from [08](08-api-contracts.md); the UI never recomputes statistics (TRD §2). Owner: Dev-C. Priorities: P0 unless marked.

## 1. Principles
1. **Honesty first:** every aggregate shows `n`, interval, and INFRA exclusions. No bare percentages.
2. **Trace is the product:** any number is one click from the runs behind it.
3. **Desktop-first** (demo is on a laptop/projector); readable on tablet; read-only usable on phone.
4. Mock mode and live mode render identically (same shapes).

## 2. Navigation & routes

Top bar: **Leaderboard · Benchmarks · Compare · Failure scenarios · Catalog · Limitations**. A benchmark selector (persisted as `?benchmark=<id>`) sits left of the nav on Leaderboard/Compare/Failure scenarios.

| Screen | Route | Pri | Data (08) |
|---|---|---|---|
| S1 Leaderboard | `/` | P0 | §3.5 `group_by=agent` |
| S2 Benchmarks (list + launcher + progress) | `/benchmarks`, `/benchmarks/new` | P0 | §3.2, §3.1 |
| S3 Compare | `/compare?benchmark=&agents=a,b` | P0 | §3.5 `group_by=agent_task` |
| S4 Run detail | `/runs/:run_id` | P0 | §3.4 |
| S5 Failure scenarios | `/resilience?benchmark=` | P0 | §3.6, §3.5 |
| S6 Catalog (agents, tasks) | `/catalog` | P0 (list) / P1 (register, weak flags) | §3.1, §3.7 |
| S7 Security | `/security?benchmark=` | P2 | §3.7 |
| S8 Limitations | `/limitations` | P0 | static |
| Run list (drill-down) | `/runs?benchmark=&agent=&task=&scenario=&status=` | P0 | §3.4 |

## 3. Screens

### S1 Leaderboard
- Header: benchmark name, state badge, scenario select (default `baseline`), category filter (P2, hidden when one category).
- Table, one row per agent (server-sorted): **Success rate** (value + `[ci_low–ci_high]` + `passed/n`), **Cost** (mean + interval) with confidence badge (✓ verified / ≈ estimated count), **Steps**, **Tool calls**, **Time**, **INFRA excluded** count. Row actions: select checkbox (2+) → "Compare"; agent name → run list filtered.
- Footnote under table: definitions (steps, tool calls) linking to Limitations.

### S2 Benchmarks
- List: name, state, progress bar (`done/total`, with INFRA and excluded counts), spend vs cap, created.
- "New benchmark" form: name, agents (multi-select), tasks (multi-select), scenarios (multi-select; baseline preselected; disallowed combos disabled with reason), `n_runs` (default 3), `spend_cap_usd` (required). Submit → 202 → redirect to list row. Client validation mirrors 08 §3.2 rules; server errors rendered per field.
- Progress auto-refresh (poll every 3 s while `queued|running`; pause when tab hidden).

### S3 Compare
- Agent picker (2–3). Grid: rows = tasks (+ "All" pooled row), columns = agents; each cell: pass rate with interval, cost, steps, time. Winner highlighting only when intervals do **not** overlap; otherwise label "no clear difference". Cell click → run list.

### S4 Run detail
- Summary strip: status chip (PASS / FAIL / INFRA_ERROR with text), agent, task, scenario, model, tokens in/out, cost + confidence, duration, steps, tool calls, attempt/repeat, started time.
- Tabs: **Timeline** (default), **Diff** (workspace diff), **Grader** (suites, tamper flag), **Environment** (fingerprint JSON).
- Timeline: ordered list from `/events`; row = relative time, type chip, role (if any), one-line summary, latency; expand → pretty-printed payload (truncated flag shown). Errors in error style; `fault_injected` rows with distinct marker and a connector to the failing `llm_call`. Filter chips by type. P2: tree grouped by `agent_role`.
- Previous/next run within the same (agent, task, scenario) cell.

### S5 Failure scenarios
- Matrix: rows = agents, columns = scenarios (baseline first). Cell: pass rate (value, n) and, for fault columns, resilience score with a plain-language delta ("−37 pts vs baseline"). Cell click → run list. Static note: "Tests resilience under chosen conditions, not all production failures."

### S6 Catalog
- Agents table (name, mode, model, description). Tasks table (id, category, grader type, validated, weak flag P2/ allowed faults). P1: "Register agent" (path/URL input) → shows doctor checks list; failure keeps form with checks.

### S7 Security (P2)
- Per agent: security score + violations list with links to runs; label "baseline assessment, not an audit".

### S8 Limitations
- Static page from the plan's honest limits (tests cannot cover everything; faults simulated; repeated runs statistical; security baseline; tool faults only for reference agents; black-box agents that hard-code provider endpoints can't be measured; metric definitions from 07 §4).

## 4. State matrix (every data screen)

| State | Behaviour |
|---|---|
| Loading | Skeleton rows with fixed heights (no layout shift); `aria-busy` on region |
| Empty | Explains why + one action: no benchmarks → "Launch your first benchmark"; benchmark with 0 done runs → "Runs in progress"; filters with 0 results → "Clear filters" |
| Error | Inline banner with message from error envelope + Retry; never a blank page; API down → "Cannot reach API" with health-check hint |
| Success | Data + `generated_at`; after launch a toast "Benchmark queued" and focus moves to the new row |
| Partial | Running benchmark: stats shown with current `n`; banner "Results incomplete (x of y runs)" |
| Halted | `halted_spend_cap` banner: "Stopped at spend cap $X" |
| INFRA | Run rows with INFRA_ERROR display "excluded from statistics" |
| Mock mode | Persistent "MOCK DATA" ribbon (so mock numbers can never be mistaken for results) |

## 5. Primary interaction flows
See [06](06-app-flow.md). Key UI rule: launching never blocks; progress is observed, not awaited.

## 6. Responsive behaviour

| Width | Behaviour |
|---|---|
| ≥ 1280 | Full tables; compare shows up to 3 agent columns side by side |
| 768–1279 | Tables scroll horizontally with sticky first column; compare max 2 columns, third stacked |
| < 768 | Read-only priority: leaderboard as cards (rank, agent, success rate + interval, cost); run timeline vertical; launcher usable but not optimised; nav collapses to a menu button |

## 7. Accessibility baseline (target WCAG 2.1 AA)

- Semantic tables (`th scope`), headings per screen, landmarks (nav, main).
- Status never by color alone: chips carry text (PASS/FAIL/INFRA_ERROR) and icon.
- All controls keyboard-operable; visible focus; timeline rows are buttons with `aria-expanded`; Esc closes dialogs.
- Contrast ≥ 4.5:1 for text; respect `prefers-reduced-motion` (no animated progress except opacity).
- Progress updates announced via `aria-live="polite"` (throttled).
- Any chart (A-07: none required in P0) must have an adjacent table equivalent.
- Verification: checklist T-19 (manual, keyboard-only pass + contrast spot-check).

## 8. Content rules
Plain labels: "Success rate", "Cost (USD)", "Steps (LLM calls)", "Tool calls requested", "Time (s)". Always show units. Numbers: cost 4 decimals, rates as % with 1 decimal, intervals as `[low–high]`.
