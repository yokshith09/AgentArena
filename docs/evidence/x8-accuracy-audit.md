# X8 · Accuracy audit (5 random runs)

**Date:** 2026-11-15 · **By:** Dev-A (task owner Dev-C, reassigned per docs/16) · **Data:** X6 final benchmarks
`b4ab097e` (baseline) and `aba39bd6` (faults), Groq `openai/gpt-oss-20b` via Bifrost; also in `db/demo-data.sql`.

## Method
- 5 of the 30 X6 runs drawn with `random.Random(20261115).sample(runs ordered by run_id, 5)`, so the
  pick is reproducible.
- For each run, three independent sources:
  1. **Run row** (what the API and dashboard show), written by the orchestrator.
  2. **Events**: recount of `llm_call` (2xx) and `tool_call` events and sums of their token/cost fields,
     written by the proxy (docs/07 §4 definitions).
  3. **Bifrost's own log** (`data/bifrost/logs.db`, rows tagged `metadata.run_id` by the proxy's
     `x-bf-lh-run_id` header): call count, prompt/completion tokens, cost.
- Plus an independent cost recomputation: tokens × Groq list price ($0.075 in / $0.30 out per 1M).

## Results
Cells are run row / events / Bifrost.

| Run | Agent | Task | Scenario | Status | Steps (LLM calls) | Tool calls (row / events) | Tokens in | Tokens out | Cost row / events | Exact list price | Bifrost cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `53a9b35c` | agent-a-plain | fix-off-by-one | tool_run_tests_error | FAIL | 9 / 9 / 9 ✓ | 8 / 8 ✓ | 7053 / 7053 / 7053 ✓ | 872 / 872 / 872 ✓ | $0.000789 / $0.000789 | $0.00079058 (-0.20%) | $0.00068497 (cached 2816; list − cache discount = $0.00068498) |
| `11fc5e15` | agent-b-openai-agents | add-slugify | baseline | PASS | 6 / 6 / 6 ✓ | 5 / 5 ✓ | 3412 / 3412 / 3412 ✓ | 584 / 584 / 584 ✓ | $0.000432 / $0.000432 | $0.00043110 (+0.21%) | $0.00042150 (cached 256; list − cache discount = $0.00042150) |
| `801d4d88` | agent-b-openai-agents | fix-average-empty | baseline | PASS | 5 / 5 / 5 ✓ | 4 / 4 ✓ | 2388 / 2388 / 2388 ✓ | 300 / 300 / 300 ✓ | $0.000270 / $0.000270 | $0.00026910 (+0.33%) | $0.00024990 (cached 512; list − cache discount = $0.00024990) |
| `baaff6e4` | agent-a-plain | fix-off-by-one | baseline | PASS | 6 / 6 / 6 ✓ | 5 / 5 ✓ | 3595 / 3595 / 3595 ✓ | 425 / 425 / 425 ✓ | $0.000396 / $0.000396 | $0.00039713 (-0.28%) | $0.00035872 (cached 1024; list − cache discount = $0.00035873) |
| `d585c54d` | agent-a-plain | fix-off-by-one | instruction_misleading_hint | PASS | 6 / 6 / 6 ✓ | 5 / 5 ✓ | 3787 / 3787 / 3787 ✓ | 405 / 405 / 405 ✓ | $0.000404 / $0.000404 | $0.00040552 (-0.37%) | $0.00035752 (cached 1280; list − cache discount = $0.00035752) |

## Findings
- **Steps, tool calls and tokens match exactly across all three sources for all 5 runs.** No discrepancy.
- **Run cost = sum of event costs exactly** (orchestrator aggregation is correct).
- **Stored cost vs exact list price: within ±0.4% per run.** Cause: each call's cost is rounded to
  6 decimals (`pricing.yaml` × tokens, `round(…, 6)`) and stored as `numeric(12,6)`; gpt-oss-20b calls
  cost about $0.00002–0.0002. Known limitation; totals over a benchmark stay within ~0.1%.
- **Bifrost's cost is lower** because Groq bills cached input tokens at 50%. Applying that discount to
  the list price reproduces Bifrost's figure to within $0.00000001 on every run. Our cost is list price
  (stated on the Limitations page).

**Conclusion:** no metric errors; the two cost differences are explained and documented. No fixes required.
