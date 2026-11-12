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

`npm run build` type-checks and builds the app; `npm run lint` runs Oxlint.

The default is mock mode, with a persistent MOCK DATA ribbon. The fixture-state selector switches
between completed, empty, INFRA exclusion, injected fault, partial, and spend-cap-halted examples.
These are illustrative fixtures, not benchmark results. Live mode intentionally shows an
unavailable message and does not render fixtures until API wiring is implemented.
