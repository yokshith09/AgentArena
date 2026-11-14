# AgentArena frontend

The React/Vite dashboard scaffold is contract-shaped around the API described in
[`../docs/08-api-contracts.md`](../docs/08-api-contracts.md). Its user-facing routes and states follow
[`../docs/05-ux-spec.md`](../docs/05-ux-spec.md).

## Run locally

```powershell
cd frontend
npm install
npm run dev
```

`npm run build` type-checks and builds the app; `npm run lint` runs Oxlint; `npm test` runs the Vitest suite (every route in every mock state, live-mode data/error/launcher behaviour against a stubbed API).

The default is mock mode, with a persistent MOCK DATA ribbon. The fixture-state selector switches
between completed, empty, INFRA exclusion, injected fault, partial, spend-cap-halted, loading, and
error examples. These are illustrative fixtures, not benchmark results. Live mode (`?mode=live`, header toggle) reads the real API (`VITE_API_BASE`, default `http://localhost:8000`; start it with `docker compose up -d api`), shows no fixtures, and polls every 5 s while a benchmark is queued or running. Run detail and trace are fetched only for the run being viewed.
