# 15 · Open Questions (expanded) — for the other developers to answer

> Status: 2026-11-12. **This file is where answers are recorded.** One-line register stays in [01](01-hackathon-strategy.md) §3.4 and points here. Answering: edit the **Answer / Date / By** cells (PR or direct commit to `main` is fine, label `docs`). If nobody answers by the deadline, the **Default** applies automatically and is noted as "defaulted".
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
- **Why it matters:** [13](13-traceability.md) and the demo order are built on *derived* goals G1–G8. Weights decide what we polish vs cut.
- **Please provide:** criteria names, weights, any must-haves, any penalties; source (link/screenshot/text).
- **Default:** keep G1–G8; equal weight.
- **Answer / Date / By:** _____

### OQ-03 · Submission requirements and cutoff
- **Why:** sets the real deadline (we assume 14 Nov EOD with 15 Nov buffer) and the final deliverables.
- **Please provide:** exact cutoff (date, time, timezone); what is submitted (repo link? video? deployed link? form?); video length/format limits; whether judges run the code or only watch.
- **Default:** repo link + README + ≤ 5 min demo video; local-only demo.
- **Answer / Date / By:** _____

### OQ-04 · Who is Dev-A / Dev-B / Dev-C
- **Why:** every task has one accountable owner; names needed on the board.
- **Please provide:** name for each role; availability per person for 12, 13, 14, 15 Nov (hours/day, any hard gaps); preferred timezone for syncs. (Skills deliberately not used for assignment.)
- **Default:** Akhil → Dev-A, Yokshith → Dev-C, third member → Dev-B; availability assumed full-time (A-03).
- **Answer / Date / By:** _____

### OQ-05 · Provider, model, key and budget
- **Why:** blocks A1 (Bifrost call), `pricing.yaml`, run sizing, spend cap.
- **Please provide:** which LLM provider(s) Bifrost will route to; model name(s) allowed; who holds the key and how it is shared (never in the repo; `.env` locally); price per 1M input/output tokens (from provider page); total dollar budget for all dev + final benchmark runs; per-minute rate limits if known.
- **Default:** one cheap model on one provider; budget cap set by team lead; if no key by M0 gate → `mock_llm` only until key arrives (A1 stays Blocked).
- **Answer / Date / By:** _____

### OQ-06 · Bifrost facts (V-01…V-06 in [04](04-trd-architecture.md) §6)
- **Why:** reconciliation (A6), streaming usage, model naming, outage simulation depend on them.
- **Please verify by experiment or docs and record:** V-01 chat completion works (endpoint URL, auth header, model naming scheme); V-02 streaming returns `usage` with `include_usage`; V-03 how to read per-request logs/metrics, custom headers/IDs; V-04 can fallback simulate outages; V-06 exact model/price.
- **Default:** assume A-01/A-02 true; if V-01 fails → proxy talks to the provider directly (deviation noted on Limitations).
- **Answer / Date / By:** _____

### OQ-07 · How to inject "broken tool" faults
- **Why:** black-box agents have no tool hook; options differ in realism and effort.
- **Options:** (a) **env var read by our shared tools module** (P-08; works for our 3 agents only) · (b) PATH shim that makes `pytest`/`python -m pytest` fail first N times (works for any command-line agent but bypassable) · (c) both.
- **Default:** (a).
- **Answer / Date / By:** _____

### OQ-08 · Docker availability (every dev + demo machine)
- **Why:** blocks B4 (hardened sandbox) and `docker compose up` itself.
- **Please provide per machine:** OS, Docker Desktop installed? Linux containers/WSL2 working? RAM available? Admin rights?
- **Default:** assume available; any machine without it is documented, and B4 falls back to subprocess (cut rule 7).
- **Answer / Date / By:** _____

### OQ-09 · Git and GitHub workflow
- **Why:** blocks X2.
- **Facts:** remote given: `https://github.com/yokshith09/AgentArena.git`.
- **Please confirm:** all three have push access (collaborator invites sent?); branch protection on/off; squash merge OK; who merges `contract` PRs; any naming constraint.
- **Default:** collaborators with write access, no protection, squash merge, rules in [HACKATHON_PLAN.md](../HACKATHON_PLAN.md) §4.
- **Answer / Date / By:** _____

### OQ-10 · Frontend tooling
- **Why:** affects scaffold (C1) only.
- **Please decide:** bundler (Vite assumed), TypeScript yes/no (assumed yes), UI/CSS library (default none/plain CSS to avoid dependency risk), charting library (default none; tables + simple bars).
- **Answer / Date / By:** _____

### OQ-11 · Demo hosting
- **Why:** hosted demo adds deployment work not in the board.
- **Please decide:** local laptop demo only, or must judges open a URL?
- **Default:** local only + demo video + data dump.
- **Answer / Date / By:** _____

### OQ-12 · Existing work outside this folder
- **Why:** plan assumes zero implemented code; any prior code changes the audit.
- **Please confirm:** any code, notebooks, accounts (Bifrost, Tavily, provider), or design assets created 1–11 Nov? Where? (A hidden `.anchor/` folder exists in the workspace; if it is yours, say what it is.)
- **Default:** nothing exists.
- **Answer / Date / By:** _____

### OQ-13 · Tavily account, key, limits (new, from D-13)
- **Why:** blocks C14 (research agent with Tavily tool).
- **Please provide:** Tavily account created? API key holder; plan/free-tier quota (requests per month, per minute); how the key is shared (`.env`, never committed).
- **Default:** one free-tier key; Tavily calls only inside the research agent and 2 research tasks (low volume). Until a key exists, C14 uses a stub Tavily response and stays Blocked for real runs.
- **Answer / Date / By:** _____

### OQ-14 · What exactly does "Integrate Bifrost + Tavily" require? (new)
- **Why:** we assume Tavily is used as a search tool by an agent (C14) and judges look for it in the trace. The problem sheet may mean something different (e.g. Tavily inside the platform, or inside every research task).
- **Please quote** the sentence(s) from the problem statement/rules about Tavily and Bifrost, and say whether Tavily must be visible: in the architecture, in the dashboard, or only in one agent.
- **Default:** one research agent with Tavily search tool + 2 research tasks + visible in trace (DA-12).
- **Answer / Date / By:** _____
