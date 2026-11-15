# AgentArena

Benchmarking platform for AI agents (Global AI Hackathon · Problem Statement 02 · Bifrost by Maxim AI).

**Problem:** agent comparisons are usually anecdotes: one run, one prompt, no cost, no trace, no
idea how the agent behaves when something breaks. **AgentArena** runs any agent as a black box on
identical coding tasks, routes every LLM call through a measuring proxy and the **Bifrost** gateway,
grades the result with visible *and hidden* tests, repeats runs, injects controlled failures, and shows
success rate with confidence intervals, cost, steps, tool calls, time, resilience and the full
step-by-step trace of every run.

## Quickstart (see the real results, no API keys needed)

Prerequisites: **Docker Desktop**, **Python 3.12+**, **Node.js 22.12+**, Git.

```bash
git clone https://github.com/yokshith09/AgentArena.git
cd AgentArena
cp .env.example .env                  # PowerShell: Copy-Item .env.example .env
```

If something on your machine already uses port 5432 (e.g. a local PostgreSQL), set
`POSTGRES_PORT=5433` **and** the same port in `DATABASE_URL` in `.env`.

```bash
docker compose up -d --build migrate api        # Postgres + schema + REST API on :8000
pip install -r requirements.txt                 # host tools (psycopg etc.)
```

Load the frozen benchmark data (real runs on Groq `gpt-oss-20b` via Bifrost, 15 Nov 2026). On
PowerShell set the connection first: `$env:DATABASE_URL="postgresql://arena:arena@localhost:5432/arena"`
(use your `POSTGRES_PORT`); bash users: `export $(grep DATABASE_URL .env)`.

```bash
python db/demo.py load
```

Start the dashboard:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173/?mode=live** and pick a benchmark (top right): *X6 final: baseline* for
the leaderboard, *X6 final: faults* for **Failure scenarios**. Click an agent, then a run, to see its
timeline, diff, grader result and environment fingerprint. API docs: http://localhost:8000/docs.
Without `?mode=live` the dashboard shows illustrative mock fixtures (labelled MOCK DATA).

Stop: `docker compose down` (keeps the data volume; add `-v` to delete it).

## Run your own benchmark (needs a Groq API key)

1. Put the key in `.env` as `GROQ_API_KEY=...` (it is passed **only** to the Bifrost container;
   `bifrost/config.json` references it as `env.GROQ_API_KEY`). Keep `UPSTREAM_BASE_URL=http://bifrost:8080/v1`.
2. Start the measuring path: `docker compose up -d --build migrate api proxy bifrost`
   (check: `curl http://localhost:8080/v1/models` lists Groq models).
3. Agent dependencies, in a virtual environment (the runner starts agents with the same Python):
   ```bash
   python -m venv .venv
   .venv/Scripts/activate                 # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt -r agents/requirements.txt
   ```
4. Index agents and tasks (tasks are loaded only if the validator accepts them):
   `python -m orchestrator.seed`
5. Launch a benchmark from the dashboard (**Benchmarks → New benchmark**) or `POST /api/benchmarks`.
6. Run the orchestrator (Groq free tier: 8K tokens/min, so space runs ~35 s):
   ```bash
   python -m orchestrator --once --parallel 1 --min-interval 35
   ```
   Progress and results appear live in the dashboard. Zero-cost alternative: set
   `UPSTREAM_BASE_URL=http://mock_llm:9000/v1` and start `docker compose --profile mock up -d mock_llm proxy`
   (scripted replies, so agents cannot actually solve tasks; useful to test the pipeline).

## How it works

```
dashboard (React) ─▶ API + stats (FastAPI) ─▶ Postgres ◀─ orchestrator ─▶ runner ─▶ agent (subprocess)
                                                  ▲                                      │ OPENAI_BASE_URL
                                                  └──── events ◀── measuring proxy ◀─────┘
                                                                         │
                                                                   Bifrost gateway ─▶ Groq (gpt-oss-20b)
```

- **Agents** are black boxes: any program that honours `OPENAI_BASE_URL` (env contract in
  [docs/10 §2.2](docs/10-integration-contracts.md)). Three reference agents: framework-free (A),
  OpenAI Agents SDK (B), test-retry variant (C).
- **Measuring proxy** (`proxy/`): forwards calls to Bifrost, records every `llm_call` and `tool_call`
  with tokens, cost (from `pricing.yaml`), latency, and injects **provider faults** (503 outage, 429
  rate limit). Tags each call with `x-bf-lh-run_id`, so Bifrost's own logs carry the run id.
- **Bifrost** (`bifrost/config.json`): the single gateway to the model provider. The provider key
  lives only there. Verified: proxy token counts match Bifrost's logs exactly.
- **Orchestrator** (`orchestrator/`): expands agents × tasks × scenarios × repeats, runs them,
  classifies PASS / FAIL / INFRA_ERROR (injected faults never count as infrastructure errors),
  retries infrastructure failures, enforces a spend cap, resumes after a crash.
- **Runner + grader** (`runner/`, `grader/`): copy the task workspace, run the agent with a timeout,
  then grade on a clean copy with visible and **hidden** tests and tamper detection.
- **Faults**: provider (503, 429, in the proxy), tool (`run_tests` errors, via the agent env),
  instruction (misleading note added to the workspace by the runner).
- **Stats** (`api/stats`): Wilson 95% intervals for pass rate; mean/median/std and fixed-seed bootstrap
  intervals for cost, steps, tool calls, time; resilience = pass rate under fault ÷ baseline.

### Add your agent
Create `agents/<name>/agent.yaml` (`name`, `mode: command`, `entrypoint`, `model_config.model`,
`description`) and make the program read `TASK_PROMPT`, `WORKSPACE` and `OPENAI_BASE_URL`. Run
`python -m orchestrator.seed`, then select it in a new benchmark.

## Results in the demo data
X6 on Groq `gpt-oss-20b`: Agent B 5/5, Agents A and C 4/5 (both miss a hidden test on
`fix-off-by-one`). Under faults, Agent A fails on 503, 429 and the tool fault; Agent C is the only
one to survive the 429 rate limit. 30 runs, 0 infrastructure errors, **$0.011** total.

## Limitations
- One run per agent × task in the demo data (Groq free tier: 200K tokens/day), so intervals are wide.
- One model (Groq `gpt-oss-20b`); 5 hand-written Python tasks; faults measured on one task.
- Cost uses list prices; Groq's cached-input discount is not modelled (Bifrost's figure was 8.5%
  lower on X6). Tokens match Bifrost exactly.
- Agents run as subprocesses with a minimal environment, not in a hardened container.
- Tool faults only reach agents that use our shared tools module; provider and instruction faults
  apply to any agent. Results describe behaviour under the chosen conditions, not production failures.

## Technologies and tools
Python 3.12/3.13, FastAPI, psycopg 3, PostgreSQL 16, Docker Compose, Bifrost (Maxim AI) LLM
gateway, Groq (`openai/gpt-oss-20b`), OpenAI Agents SDK (Agent B), React 19 + Vite + TypeScript,
pytest.

## How AI is used
- **In the product:** the benchmarked agents are LLM-driven (Groq `gpt-oss-20b`, reached only through
  Bifrost); AgentArena measures them.
- **AI tools used to build it:** _to be completed by the team before submission._

## Documentation
- Start here: [HACKATHON_PLAN.md](HACKATHON_PLAN.md) · [Final-day plan](docs/16-final-day-plan.md) · [Task board](docs/14-task-board.md) · full index: [docs/README.md](docs/README.md)
- Component READMEs: [proxy](proxy/README.md) · [api](api/README.md) · [orchestrator](orchestrator/README.md) · [db](db/README.md) · [frontend](frontend/README.md)
- [PRD](docs/02-prd.md) · [Feature specs](docs/03-feature-specs.md) · [TRD](docs/04-trd-architecture.md) · [Data schema](docs/07-data-schema.md) · [API contracts](docs/08-api-contracts.md) · [Integration contracts](docs/10-integration-contracts.md) · [Testing & demo](docs/09-testing-and-demo.md)
