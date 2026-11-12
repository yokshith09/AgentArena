# 15 · Open Questions: Answers

> Status: 2026-11-12 · Drafted by Claude from the problem sheet pages 01-04, our planning chat, the Bifrost docs and README, and Tavily's docs. Everything marked **TEAM** can only be answered by you two. Everything else is answered below and should be confirmed with a quick check where noted.
> Sources are listed at the bottom.

## Summary

| # | Pri | Status | One-line answer |
|---|---|---|---|
| OQ-01 | Shapes | Answered (default holds) | The pages we have contain **no rubric**. Use the 5 mandatory requirements as the checklist. Get page 05. |
| OQ-03 | Shapes | Partly | Build ends **15 Nov**, judging is **29 Nov**. No cutoff time or submission format in pages 01-04. |
| OQ-04 | Minor | Answered (updated: team is now three) | Akhil = Dev-A, third member = Dev-B, Yokshith = Dev-C. Still need the third member's name and everyone's availability. |
| OQ-05 | **Blocking** | **TEAM** | Needs provider, key, price, and budget. Model naming format provided. |
| OQ-06 | Shapes | Mostly answered from docs | Endpoint, `provider/model` naming, run-ID tagging, and logging all confirmed in docs. Two items need a 10-minute smoke test. |
| OQ-07 | Shapes | Answered | Option (a). |
| OQ-08 | **Blocking** | **TEAM** | Run the 3-line check below on each machine. |
| OQ-09 | **Blocking** | **TEAM** (rules answered) | Yokshith owns the repo, so he must invite Akhil and the third member with write access. |
| OQ-10 | Minor | Answered | Vite + TypeScript, plain CSS, no chart library. |
| OQ-11 | Minor | Answered | Local demo + video + data dump. |
| OQ-12 | **Blocking** | Partly | No code exists as far as our chat shows. **TEAM** must identify `.anchor/`. |
| OQ-13 | **Blocking** | Answered (needs account) | Free tier: 1,000 credits/month, no card. Create the account. |
| OQ-14 | Shapes | Answered | The sheet gives no detail beyond the footer. The default is the right interpretation. |

---

### OQ-01 · Official judging rubric
- **Answer:** The four pages we have (01-04) contain **no rubric, weights, or penalties**. What they do contain, for Problem 02, is a goal, **five mandatory requirements**, an expected outcome, and optional guidance. Treat the five mandatory requirements as the scoring checklist and the must-haves:
  1. Framework independence
  2. Consistent evaluation (success, steps, tool calls, tokens, cost, time)
  3. Repeatability
  4. Failure testing
  5. Inspection and comparison (step-by-step records)
- **Keep** G1-G8 with equal weight, but make sure G-items for those five requirements are never cut.
- **Action:** The pages are numbered "of 5" and we only have 01-04. Page 05 is either a fifth problem statement or the rules and judging page. **Ask whoever has the file for page 05.** If it has a rubric, replace this answer.
- **Date / By:** 2026-11-12 / Claude (draft)

### OQ-03 · Submission requirements and cutoff
- **Answer:** The sheet footer states: build **1-15 Nov 2026**, teams of 1-4, online and global, judging **29 Nov 2026**. So the last build day is **15 Nov**; keep the plan's **14 Nov EOD target with 15 Nov as buffer**.
- **Not in the pages we have:** the cutoff time and timezone, the submission form, video limits, and whether judges run code. Defaults apply: repo link + README + ≤5 min demo video, local-only demo.
- **Action:** check page 05 or the hackathon portal for the exact cutoff time. Until then, plan to submit by the evening of 14 Nov IST.
- **Date / By:** 2026-11-12 / Claude (draft)

### OQ-04 · Who is Dev-A / Dev-B / Dev-C
- **Answer (updated, team is now three):** Dev-A = **Akhil**, Dev-B = **the third member**, Dev-C = **Yokshith**. This matches the plan's default, so no redistribution is needed:
  - **Dev-A (Akhil):** Bifrost setup, measuring proxy, metrics and cost reconciliation, database, and API.
  - **Dev-B (third member):** runner, hardened sandbox, grader, repeat engine, and the security checks.
  - **Dev-C (Yokshith):** tasks, reference agents, dashboard, Tavily research agent, docs, demo.
  - Keep cut rule 7 as a safety net: if the hardened sandbox (B4) is not working by the end of the first end-to-end run, fall back to subprocess isolation.
- **TEAM must provide:** the third member's name, plus hours per day for 12, 13, 14, 15 Nov and any hard gaps for all three people. Akhil's timezone is IST (UTC+05:30); the others to confirm.
- **Date / By:** 2026-11-12 / Claude (draft), availability pending

### OQ-05 · Provider, model, key and budget (**TEAM**)
- **What I can add:** Bifrost names models as `provider/model`, for example `openai/gpt-4o-mini`. The key is configured inside Bifrost (web UI at `http://localhost:8080` or config file), so the key belongs in one place, never in agent containers or the repo.
- **TEAM must provide:**
  - Provider and allowed model(s). Choose **one cheap model** and, if possible, a second model for the agent × model experiment.
  - Who holds the key and how it is shared (`.env` locally, never committed).
  - Price per 1M input and output tokens, **copied from the provider's pricing page** into `pricing.yaml` with today's date.
  - Dollar budget. Sizing formula: `runs = agents × tasks × N × scenarios`, `cost ≈ runs × avg_tokens × price`. Set the spend cap at roughly **2× the estimate for the final benchmark plus a development allowance**, then adjust.
  - Rate limits, if known.
- **Fallback:** `mock_llm` until the key arrives (A1 stays Blocked). Bifrost also ships a `mocker` plugin for mock responses, which may save work.
- **Date / By:** pending

### OQ-06 · Bifrost facts (V-01 to V-06)
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
- **Date / By:** 2026-11-12 / Claude (draft from docs)

### OQ-07 · How to inject "broken tool" faults
- **Answer: (a)**, an env var read by our shared tools module (P-08). It is reproducible, works for all three reference agents, and is quick to build. Add (b), the PATH shim, **only if time remains**, as a demo of black-box fault injection on a third-party agent. Be honest on the Limitations page that (a) only covers our own agents.
- **Date / By:** 2026-11-12 / Claude (draft)

### OQ-08 · Docker availability (**TEAM**)
- **Please run on each dev and demo machine and paste the result here:**
  1. `docker --version`
  2. `docker run --rm hello-world` (this proves Linux containers work, or WSL2 on Windows)
  3. `docker compose version`
  Also note OS, free RAM, and whether you have admin rights.
- **Default:** assume available. A machine without it uses the subprocess fallback (cut rule 7) and is documented.
- **Date / By:** pending

### OQ-09 · Git and GitHub workflow
- **Answer (rules):** the repo `https://github.com/yokshith09/AgentArena.git` belongs to Yokshith, so **Yokshith must invite Akhil and the third member as collaborators with write access**. No branch protection, squash merge, rules as in HACKATHON_PLAN.md §4. **A `contract` PR is reviewed and merged by someone other than its author.**
- **TEAM:** confirm Akhil and the third member have accepted the invitation and can push a test branch.
- **Date / By:** rules 2026-11-12 / Claude (draft), access pending

### OQ-10 · Frontend tooling
- **Answer:** **Vite + TypeScript**, **plain CSS** (no UI library), and **no chart library**: use tables and CSS bars for the leaderboard and comparison. Reconsider a small chart library only for the optional cost-vs-success scatter after the core views work.
- **Date / By:** 2026-11-12 / Claude (draft)

### OQ-11 · Demo hosting
- **Answer:** **Local laptop demo only**, plus the demo video and a data dump (exported JSON/SQL) so judges can see results without running anything. The pages we have do not ask for a hosted URL, and judging is online on 29 Nov, so a video plus a clear `docker compose up` quickstart is the safe combination. Confirm against page 05.
- **Date / By:** 2026-11-12 / Claude (draft)

### OQ-12 · Existing work outside this folder
- **Answer:** As far as our planning chat shows, **no code, notebooks, or accounts existed**; the only artifacts are the planning documents. I cannot see the workspace, so **TEAM must say what the hidden `.anchor/` folder is** (and whether anything was created 1-11 Nov).
- **Default:** nothing exists.
- **Date / By:** partly answered / TEAM to confirm

### OQ-13 · Tavily account, key, limits
- **Answer:** Tavily's **free "Researcher" plan gives 1,000 credits per month with no credit card**. A basic search costs **1 credit**; deeper searches cost more (check the credit page before using advanced depth). A third-party source lists rate limits of about **100 requests/min on a development key** and 1,000 on a production key; verify this in the Tavily dashboard. A free student program also exists.
- **Plan:** one free-tier key, **one person creates the account and shares the key via `.env`**. Use `basic` depth and a small `max_results`. The budget is tiny (two research tasks × N runs × agents is well under 1,000), but the quota is shared across dev and final runs, so **cache or replay Tavily responses** the way we do LLM responses.
- **Until the key exists:** C14 uses a stub response and stays Blocked for real runs.
- **Date / By:** 2026-11-12 / Claude (draft), account creation pending

### OQ-14 · What does "Integrate Bifrost + Tavily" require?
- **Answer:** In pages 01-04, the only Tavily text is the footer line **"INTEGRATE BIFROST + TAVILY"**, repeated on every page. No sentence explains how or where Tavily must appear. For Problem 02 the only related guidance is that Bifrost can give gateway-level visibility into model requests and operational metrics, while agent steps and tool execution need extra instrumentation. So the sheet does not require a specific shape.
- **Decision:** keep the default (DA-12), and make Tavily **visible in three places** so a judge cannot miss it: (1) the research agent's Tavily tool calls in the run trace, (2) the architecture diagram and README, and (3) a dashboard filter for the research category. Bifrost is visible as the gateway in every trace.
- **Action:** if page 05 or the organizers say otherwise, update this answer.
- **Date / By:** 2026-11-12 / Claude (draft)

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
