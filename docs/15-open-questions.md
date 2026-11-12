# 15 · Open Questions (expanded) — for the other developers to answer

> Status: 2026-11-12, answers merged from the former `15-open-questions-answered.md` (drafted from the problem-sheet pages 01-04, Bifrost and Tavily docs; **not verified by running anything**). **This file is where answers are recorded.** One-line register stays in [01](01-hackathon-strategy.md) §3.4 and points here. Answering: edit the **Answer / Date / By** cells (PR or direct commit to `main` is fine, label `docs`). If nobody answers by the deadline, the **Default** applies automatically and is noted as "defaulted".
> Priority: **Blocking** = work cannot start/finish without it · **Shapes** = changes design/scope · **Minor**.

| # | Pri | Needed by | Question owner → answerer |
|---|---|---|---|
| OQ-01 | Shapes | M0 gate (12 Nov midday) | Dev-C → team lead / whoever has the problem sheet |
| OQ-03 | Shapes | M0 | Dev-C → team lead |
| OQ-04 | Minor | M0 | Dev-A → all |
| OQ-05 | **Blocking** (A1) | M0 | Dev-A → whoever holds provider access |
| OQ-06 | Shapes | M0 (V-01/V-02) | Dev-A → Dev-A (verified by experiment) |
| OQ-07 | Shapes | M1 | Dev-B → Dev-B/C |
| OQ-08 | **Blocking** (B4) | M0 | Dev-B → all (each machine) |
| OQ-09 | **Blocking** (X2) | M0 | Dev-A → all |
| OQ-10 | Minor | M0 | Dev-C → Dev-C |
| OQ-11 | Minor | M4 | Dev-C → team lead |
| OQ-12 | **Blocking** (audit) | M0 | Dev-A → all |
| OQ-13 | **Blocking** (C14) | M1 | Dev-C → whoever creates accounts |
| OQ-14 | Shapes | M1 | Dev-C → team lead / problem sheet |

---

### OQ-01 · Official judging rubric
> **UPDATE (D-15):** rules received. Criteria: Innovation, Technical execution, Problem and potential impact, Use of AI, User experience, Scalability and potential. No weights. This supersedes the draft answer below.
- **Why it matters:** [13](13-traceability.md) and the demo order are built on *derived* goals G1–G8. Weights decide what we polish vs cut.
- **Please provide:** criteria names, weights, any must-haves, any penalties; source (link/screenshot/text).
- **Default:** keep G1–G8; equal weight.

**Answer (2026-11-12):**
- **Answer:** The four pages we have (01-04) contain **no rubric, weights, or penalties**. What they do contain, for Problem 02, is a goal, **five mandatory requirements**, an expected outcome, and optional guidance. Treat the five mandatory requirements as the scoring checklist and the must-haves:
  1. Framework independence
  2. Consistent evaluation (success, steps, tool calls, tokens, cost, time)
  3. Repeatability
  4. Failure testing
  5. Inspection and comparison (step-by-step records)
- **Keep** G1-G8 with equal weight, but make sure G-items for those five requirements are never cut.
- **Action:** The pages are numbered "of 5" and we only have 01-04. Page 05 is either a fifth problem statement or the rules and judging page. **Ask whoever has the file for page 05.** If it has a rubric, replace this answer.
- **Date / By:** 2026-11-12 / draft (from docs)

### OQ-03 · Submission requirements and cutoff
> **UPDATE (D-15):** submission window closes 15 Nov 2026 11:59 PM (timezone not stated). Required: public GitHub repo with detailed README (project, install, implementation, technologies), project description, problem, technologies, how AI is used, working demo/prototype, pitch deck (separate), demo video (about 6 min suggested). Self-host or local is fine; bring own keys. Still unknown: timezone, submission form specifics beyond the theme dropdown.
- **Why:** sets the real deadline (we assume 14 Nov EOD with 15 Nov buffer) and the final deliverables.
- **Please provide:** exact cutoff (date, time, timezone); what is submitted (repo link? video? deployed link? form?); video length/format limits; whether judges run the code or only watch.
- **Default:** repo link + README + ≤ 5 min demo video; local-only demo.

**Answer (2026-11-12):**
- **Answer:** The sheet footer states: build **1-15 Nov 2026**, teams of 1-4, online and global, judging **29 Nov 2026**. So the last build day is **15 Nov**; keep the plan's **14 Nov EOD target with 15 Nov as buffer**.
- **Not in the pages we have:** the cutoff time and timezone, the submission form, video limits, and whether judges run code. Defaults apply: repo link + README + ≤5 min demo video, local-only demo.
- **Action:** check page 05 or the hackathon portal for the exact cutoff time. Until then, plan to submit by the evening of 14 Nov IST.
- **Date / By:** 2026-11-12 / draft (from docs)

### OQ-04 · Who is Dev-A / Dev-B / Dev-C
- **Why:** every task has one accountable owner; names needed on the board.
- **Please provide:** name for each role; availability per person for 12, 13, 14, 15 Nov (hours/day, any hard gaps); preferred timezone for syncs. (Skills deliberately not used for assignment.)
- **Default:** Akhil → Dev-A, Yokshith → Dev-C, third member → Dev-B; availability assumed full-time (A-03).

**Answer (2026-11-12):**
- **Answer (updated, team is now three):** Dev-A = **Akhil**, Dev-B = **the third member**, Dev-C = **Yokshith**. This matches the plan's default, so no redistribution is needed:
  - **Dev-A (Akhil):** Bifrost setup, measuring proxy, metrics and cost reconciliation, database, and API.
  - **Dev-B (third member):** runner, hardened sandbox, grader, repeat engine, and the security checks.
  - **Dev-C (Yokshith):** tasks, reference agents, dashboard, Tavily research agent, docs, demo.
  - Keep cut rule 7 as a safety net: if the hardened sandbox (B4) is not working by the end of the first end-to-end run, fall back to subprocess isolation.
- **TEAM must provide:** the third member's name, plus hours per day for 12, 13, 14, 15 Nov and any hard gaps for all three people. Akhil's timezone is IST (UTC+05:30); the others to confirm.
- **Date / By:** 2026-11-12 / draft (from docs), availability pending

### OQ-05 · Provider, model, key and budget
- **Why:** blocks A1 (Bifrost call), `pricing.yaml`, run sizing, spend cap.
- **Please provide:** which LLM provider(s) Bifrost will route to; model name(s) allowed; who holds the key and how it is shared (never in the repo; `.env` locally); price per 1M input/output tokens (from provider page); total dollar budget for all dev + final benchmark runs; per-minute rate limits if known.
- **Default:** one cheap model on one provider; budget cap set by team lead; if no key by M0 gate → `mock_llm` only until key arrives (A1 stays Blocked).

**Answer (2026-11-12):**
- **What I can add:** Bifrost names models as `provider/model`, for example `openai/gpt-4o-mini`. The key is configured inside Bifrost (web UI at `http://localhost:8080` or config file), so the key belongs in one place, never in agent containers or the repo.
- **TEAM must provide:**
  - Provider and allowed model(s). Choose **one cheap model** and, if possible, a second model for the agent × model experiment.
  - Who holds the key and how it is shared (`.env` locally, never committed).
  - Price per 1M input and output tokens, **copied from the provider's pricing page** into `pricing.yaml` with today's date.
  - Dollar budget. Sizing formula: `runs = agents × tasks × N × scenarios`, `cost ≈ runs × avg_tokens × price`. Set the spend cap at roughly **2× the estimate for the final benchmark plus a development allowance**, then adjust.
  - Rate limits, if known.
- **Fallback:** `mock_llm` until the key arrives (A1 stays Blocked). Bifrost also ships a `mocker` plugin for mock responses, which may save work.
- **Date / By:** pending

### OQ-06 · Bifrost facts (V-01…V-06 in [04](04-trd-architecture.md) §6)
- **Why:** reconciliation (A6), streaming usage, model naming, outage simulation depend on them.
- **Please verify by experiment or docs and record:** V-01 chat completion works (endpoint URL, auth header, model naming scheme); V-02 streaming returns `usage` with `include_usage`; V-03 how to read per-request logs/metrics, custom headers/IDs; V-04 can fallback simulate outages; V-06 exact model/price.
- **Default:** assume A-01/A-02 true; if V-01 fails → proxy talks to the provider directly (deviation noted on Limitations).

**Answer (2026-11-12):**
Verified against the Bifrost README and docs (not by running it). Items marked **TEST** need a quick smoke test.

| V | Finding |
|---|---|
| V-01 | **Confirmed.** Run with `npx -y @maximhq/bifrost` or `docker run -p 8080:8080 -v $(pwd)/data:/app/data maximhq/bifrost`. Endpoint: `POST http://localhost:8080/v1/chat/completions`, model as `openai/gpt-4o-mini`. SDK drop-in base URLs also exist (`http://localhost:8080/openai`). **TEST:** whether an auth header is required when no virtual keys or admin auth are set. The docs I found do not require credentials by default for the logs API. |
| V-02 | **TEST.** Bifrost's own logs count tokens for streamed calls (an accumulator finishes the stream before logging). Whether the **response stream** includes a `usage` chunk with `stream_options.include_usage` was **not confirmed**. Test it. If it does not, the proxy estimates tokens and labels the run `estimated`. |
| V-03 | **Confirmed.** Logging is on by default and records tokens, cost, latency, model, and status. **Run tagging works:** any `x-bf-lh-*` request header is stored in the log metadata (for example `x-bf-lh-run_id`), and `x-bf-dim-*` adds dimensions to logs and metric labels. A custom request ID can be set with `x-request-id`. Responses carry `x-bifrost-*` headers (request ID, provider, model, whether a fallback served it). A logs API exists. **Version note:** some features need Bifrost v2.0.0 or later, so pin the version. |
| V-04 | **Partly.** Automatic fallbacks exist between providers and models, but the docs do not describe simulating outages. **Keep our proxy's fault injection** and do not rely on Bifrost for it. |
| V-06 | **TEAM** (model and price). Bifrost computes cost from its own pricing table, and integrators label it an **estimate**, which supports our plan: keep our own `pricing.yaml` and reconcile against Bifrost's number. |

- **Action:** a 10-minute smoke test: one non-streaming call, one streaming call with `include_usage`, one call with `x-bf-lh-run_id: test1`, then check the log entry and logs API.
- **Default:** if V-01 fails, the proxy calls the provider directly and the deviation goes on the Limitations page.
- **Date / By:** 2026-11-12 / draft (from docs)

### OQ-07 · How to inject "broken tool" faults
- **Why:** black-box agents have no tool hook; options differ in realism and effort.
- **Options:** (a) **env var read by our shared tools module** (P-08; works for our 3 agents only) · (b) PATH shim that makes `pytest`/`python -m pytest` fail first N times (works for any command-line agent but bypassable) · (c) both.
- **Default:** (a).

**Answer (2026-11-12):**
- **Answer: (a)**, an env var read by our shared tools module (P-08). It is reproducible, works for all three reference agents, and is quick to build. Add (b), the PATH shim, **only if time remains**, as a demo of black-box fault injection on a third-party agent. Be honest on the Limitations page that (a) only covers our own agents.
- **Date / By:** 2026-11-12 / draft (from docs)

### OQ-08 · Docker availability (every dev + demo machine)
- **Why:** blocks B4 (hardened sandbox) and `docker compose up` itself.
- **Please provide per machine:** OS, Docker Desktop installed? Linux containers/WSL2 working? RAM available? Admin rights?
- **Default:** assume available; any machine without it is documented, and B4 falls back to subprocess (cut rule 7).

**Answer (2026-11-12):**
- **Please run on each dev and demo machine and paste the result here:**
  1. `docker --version`
  2. `docker run --rm hello-world` (this proves Linux containers work, or WSL2 on Windows)
  3. `docker compose version`
  Also note OS, free RAM, and whether you have admin rights.
- **Default:** assume available. A machine without it uses the subprocess fallback (cut rule 7) and is documented.
- **Date / By:** pending

### OQ-09 · Git and GitHub workflow
- **Why:** blocks X2.
- **Facts:** remote given: `https://github.com/yokshith09/AgentArena.git`.
- **Please confirm:** all three have push access (collaborator invites sent?); branch protection on/off; squash merge OK; who merges `contract` PRs; any naming constraint.
- **Default:** collaborators with write access, no protection, squash merge, rules in [HACKATHON_PLAN.md](../HACKATHON_PLAN.md) §4.

**Answer (2026-11-12):**
- **Answer (rules):** the repo `https://github.com/yokshith09/AgentArena.git` belongs to Yokshith, so **Yokshith must invite Akhil and the third member as collaborators with write access**. No branch protection, squash merge, rules as in HACKATHON_PLAN.md §4. **A `contract` PR is reviewed and merged by someone other than its author.**
- **TEAM:** confirm Akhil and the third member have accepted the invitation and can push a test branch.
- **Date / By:** rules 2026-11-12 / draft (from docs), access pending

### OQ-10 · Frontend tooling
- **Why:** affects scaffold (C1) only.
- **Please decide:** bundler (Vite assumed), TypeScript yes/no (assumed yes), UI/CSS library (default none/plain CSS to avoid dependency risk), charting library (default none; tables + simple bars).

**Answer (2026-11-12):**
- **Answer:** **Vite + TypeScript**, **plain CSS** (no UI library), and **no chart library**: use tables and CSS bars for the leaderboard and comparison. Reconsider a small chart library only for the optional cost-vs-success scatter after the core views work.
- **Date / By:** 2026-11-12 / draft (from docs)

### OQ-11 · Demo hosting
> **UPDATE (D-15):** organizers confirm a deployed app is not mandatory; local with a clear README and demo video is fine.
- **Why:** hosted demo adds deployment work not in the board.
- **Please decide:** local laptop demo only, or must judges open a URL?
- **Default:** local only + demo video + data dump.

**Answer (2026-11-12):**
- **Answer:** **Local laptop demo only**, plus the demo video and a data dump (exported JSON/SQL) so judges can see results without running anything. The pages we have do not ask for a hosted URL, and judging is online on 29 Nov, so a video plus a clear `docker compose up` quickstart is the safe combination. Confirm against page 05.
- **Date / By:** 2026-11-12 / draft (from docs)

### OQ-12 · Existing work outside this folder
- **Why:** plan assumes zero implemented code; any prior code changes the audit.
- **Please confirm:** any code, notebooks, accounts (Bifrost, Tavily, provider), or design assets created 1–11 Nov? Where? (A hidden `.anchor/` folder exists in the workspace; if it is yours, say what it is.)
- **Default:** nothing exists.

**Answer (2026-11-12):**
- **Answer:** As far as our planning chat shows, **no code, notebooks, or accounts existed**; the only artifacts are the planning documents. I cannot see the workspace, so **TEAM must say what the hidden `.anchor/` folder is** (and whether anything was created 1-11 Nov).
- **Default:** nothing exists.
- **Date / By:** partly answered / TEAM to confirm

### OQ-13 · Tavily account, key, limits (new, from D-13)
- **Why:** blocks C14 (research agent with Tavily tool).
- **Please provide:** Tavily account created? API key holder; plan/free-tier quota (requests per month, per minute); how the key is shared (`.env`, never committed).
- **Default:** one free-tier key; Tavily calls only inside the research agent and 2 research tasks (low volume). Until a key exists, C14 uses a stub Tavily response and stays Blocked for real runs.

**Answer (2026-11-12):**
- **Answer:** Tavily's **free "Researcher" plan gives 1,000 credits per month with no credit card**. A basic search costs **1 credit**; deeper searches cost more (check the credit page before using advanced depth). A third-party source lists rate limits of about **100 requests/min on a development key** and 1,000 on a production key; verify this in the Tavily dashboard. A free student program also exists.
- **Plan:** one free-tier key, **one person creates the account and shares the key via `.env`**. Use `basic` depth and a small `max_results`. The budget is tiny (two research tasks × N runs × agents is well under 1,000), but the quota is shared across dev and final runs, so **cache or replay Tavily responses** the way we do LLM responses.
- **Until the key exists:** C14 uses a stub response and stays Blocked for real runs.
- **Date / By:** 2026-11-12 / draft (from docs), account creation pending

### OQ-14 · What exactly does "Integrate Bifrost + Tavily" require? (new)
- **Why:** we assume Tavily is used as a search tool by an agent (C14) and judges look for it in the trace. The problem sheet may mean something different (e.g. Tavily inside the platform, or inside every research task).
- **Please quote** the sentence(s) from the problem statement/rules about Tavily and Bifrost, and say whether Tavily must be visible: in the architecture, in the dashboard, or only in one agent.
- **Default:** one research agent with Tavily search tool + 2 research tasks + visible in trace (DA-12).

**Answer (2026-11-12):**
- **Answer:** In pages 01-04, the only Tavily text is the footer line **"INTEGRATE BIFROST + TAVILY"**, repeated on every page. No sentence explains how or where Tavily must appear. For Problem 02 the only related guidance is that Bifrost can give gateway-level visibility into model requests and operational metrics, while agent steps and tool execution need extra instrumentation. So the sheet does not require a specific shape.
- **Decision:** keep the default (DA-12), and make Tavily **visible in three places** so a judge cannot miss it: (1) the research agent's Tavily tool calls in the run trace, (2) the architecture diagram and README, and (3) a dashboard filter for the research category. Bifrost is visible as the gateway in every trace.
- **Action:** if page 05 or the organizers say otherwise, update this answer.
- **Date / By:** 2026-11-12 / draft (from docs)

---
## What only the team can still fill in

1. **OQ-05:** provider, model, key holder, price, budget.
2. **OQ-08:** Docker check on each machine.
3. **OQ-09:** collaborator invite accepted and push access confirmed.
4. **OQ-12:** what `.anchor/` is.
5. **OQ-04:** the third member's name, and availability per day for all three of you.
6. **Page 05:** rubric, cutoff time, and submission format (affects OQ-01, OQ-03, OQ-11).

## Sources

- Bifrost README and quickstart: https://github.com/maximhq/bifrost
- Bifrost request options (headers): https://docs.getbifrost.ai/providers/request-options
- Bifrost response headers: https://docs.getbifrost.ai/providers/response-headers.md
- Bifrost logging plugin: https://docs.getbifrost.ai/features/observability/default.md
- Bifrost integration notes (logging on by default, estimated cost): https://help.doit.com/docs/integrations/connect-bifrost
- Tavily credits and pricing: https://docs.tavily.com/documentation/api-credits.md
- Tavily rate limits (third-party summary): https://www.morphllm.com/tavily
