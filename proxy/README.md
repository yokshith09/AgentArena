# Measuring proxy (A4)

Forwards agent LLM traffic to Bifrost (or `mock_llm`) and records an `llm_call` event per call plus
one `tool_call` event per tool call the model requests. Contract: [docs/08 §2](../docs/08-api-contracts.md);
event payloads: [docs/07 §3](../docs/07-data-schema.md); ordering rules: [docs/10 §2.5](../docs/10-integration-contracts.md).

Agents set `OPENAI_BASE_URL=http://<proxy>:8001/runs/<run_id>/v1`. The run must exist with `state='running'`.

## Run

```bash
# zero-cost: proxy -> mock_llm (set UPSTREAM_BASE_URL=http://mock_llm:9000/v1 in .env)
docker compose --profile mock up -d --build proxy mock_llm
curl localhost:8001/health
```

Local without Docker: `uvicorn proxy.app:app --port 8001` with `UPSTREAM_BASE_URL` and either `DATABASE_URL` (as in your `.env`) or the `PG*` variables set.

| Variable | Default | Meaning |
|---|---|---|
| `UPSTREAM_BASE_URL` | `http://bifrost:8080/v1` | OpenAI-compatible base; the path after `/runs/<id>/v1/` is appended |
| `DATABASE_URL` | empty → libpq `PGHOST`/`PGPORT`/`PGUSER`/`PGPASSWORD`/`PGDATABASE` | Reads `runs`, writes `events` only (compose sets the `PG*` variables) |
| `PRICING_FILE` | `<repo>/pricing.yaml` | Versioned prices (docs/07 §8) |
| `BIFROST_API_KEY` | empty | Sent upstream only if set; the agent's `Authorization` header is always dropped |

## Behaviour

- Adds `x-bf-lh-run_id: <run_id>` upstream; stores `X-Agent-Role` as `events.agent_role` (not forwarded).
- Streaming: adds `stream_options.include_usage=true` if absent; chunks are relayed byte-for-byte and
  parsed on the way through; the event is written when the stream ends.
- Cost = tokens × `pricing.yaml` price effective on the run's `started_at` date → `verified`.
  No `usage` in the response → tokens `null`, cost `0`, `estimated`, `payload.warning`.
  Model not in `pricing.yaml` → cost `null`, `estimated`, `payload.warning`.
- Errors: unknown/not-running run → 404 `run_not_found`. Upstream 5xx/429 → passed through,
  `events.error='upstream'`; unreachable upstream → 502 `upstream_unreachable`, `error='upstream'`;
  other upstream 4xx (agent's own bad request) → passed through, `error='http_<status>'` (not INFRA).
- DB down: requests are still forwarded (run check skipped); lost events are logged to stderr.
- Previews over 8 KB are cut and the payload gets `truncated: true`. Extra payload keys beyond 07 §3
  (additive): `response_model`, `pricing_version`, `warning`.
- Provider faults (A7) hook in before forwarding — not implemented yet.

## Tests

```bash
# with DATABASE_URL (or PG* variables) pointing at the compose Postgres, e.g. from your .env
python -m pytest tests/proxy -q
```
Needs the compose Postgres (skipped otherwise); `mock_llm` runs in-process. Covers T-01…T-05.
