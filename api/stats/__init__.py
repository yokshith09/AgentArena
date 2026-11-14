"""Stats engine (A5, F-07). Pure functions; the API feeds them finished runs.

Definitions (docs/03 F-07, docs/07 section 4), also stated on the Limitations page:
- Pass rate = PASS / (PASS + FAIL), Wilson score interval at 95%. INFRA_ERROR rows never count.
- cost / steps / tool_calls / duration: mean, median, sample std (n-1), and a 95% percentile
  bootstrap CI of the mean (1000 resamples, fixed seed) so results are reproducible.
- n = 0 gives nulls (never 0%). n = 1 gives null std and null CI for non-proportions.
- Resilience = scenario pass rate / baseline pass rate (P-16); null when baseline is 0 or null.
"""
from __future__ import annotations

import math
import random
import statistics
from collections.abc import Iterable, Sequence

Z95 = 1.959963984540054
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 0
METRICS = ("cost", "steps", "tool_calls", "duration")
COUNTED = ("PASS", "FAIL")
ROUND = 6  # strip float noise; the UI does display rounding


def _r(x: float | None) -> float | None:
    return None if x is None else round(x, ROUND)


def wilson(passed: int, n: int, z: float = Z95) -> dict:
    """PassRate = {passed, n, value, ci_low, ci_high}; all-null value/CI when n = 0."""
    if n == 0:
        return {"passed": 0, "n": 0, "value": None, "ci_low": None, "ci_high": None}
    p = passed / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return {"passed": passed, "n": n, "value": _r(p),
            "ci_low": _r(max(0.0, centre - half)), "ci_high": _r(min(1.0, centre + half))}


def bootstrap_mean_ci(values: Sequence[float], resamples: int = BOOTSTRAP_RESAMPLES,
                      seed: int = BOOTSTRAP_SEED, level: float = 0.95) -> tuple[float, float] | None:
    """Percentile bootstrap CI of the mean. None when n < 2 (no spread to resample)."""
    n = len(values)
    if n < 2:
        return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(resamples))
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    return _quantile(means, lo_q), _quantile(means, hi_q)


def _quantile(sorted_vals: Sequence[float], q: float) -> float:
    """Linear interpolation between closest ranks (numpy's default 'linear' method)."""
    pos = (len(sorted_vals) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def describe(values: Iterable[float | None]) -> dict:
    """Stat = {n, mean, median, std, ci_low, ci_high}; nulls in the input are skipped."""
    vals = [float(v) for v in values if v is not None]
    n = len(vals)
    if n == 0:
        return {"n": 0, "mean": None, "median": None, "std": None, "ci_low": None, "ci_high": None}
    ci = bootstrap_mean_ci(vals)
    return {"n": n, "mean": _r(statistics.fmean(vals)), "median": _r(statistics.median(vals)),
            "std": _r(statistics.stdev(vals)) if n > 1 else None,
            "ci_low": _r(ci[0]) if ci else None, "ci_high": _r(ci[1]) if ci else None}


def result_row(agent_id: str, task_id: str | None, scenario: str, runs: Sequence[dict]) -> dict:
    """ResultRow (docs/08 section 3.5) from finished runs (state='done') of one group.
    Each run dict needs: status, cost, steps, tool_calls, duration, cost_confidence."""
    counted = [r for r in runs if r["status"] in COUNTED]
    infra = sum(1 for r in runs if r["status"] == "INFRA_ERROR")
    passed = sum(1 for r in counted if r["status"] == "PASS")
    conf = {"verified": 0, "estimated": 0}
    for r in counted:
        if r.get("cost_confidence") in conf:
            conf[r["cost_confidence"]] += 1
    row = {"agent_id": agent_id, "task_id": task_id, "scenario": scenario,
           "runs_counted": len(counted), "infra_excluded": infra,
           "pass_rate": wilson(passed, len(counted))}
    for m in METRICS:
        row[m] = describe(r.get(m) for r in counted)
    row["cost_confidence"] = conf
    return row


def sort_rows(rows: list[dict]) -> list[dict]:
    """Pass rate desc, then mean cost asc; nulls last in both."""
    def key(r):
        pr, cost = r["pass_rate"]["value"], r["cost"]["mean"]
        return (pr is None, -(pr or 0.0), cost is None, cost or 0.0, r["agent_id"], r["task_id"] or "")
    return sorted(rows, key=key)


def resilience_score(baseline: dict, scenario: dict) -> float | None:
    b, s = baseline.get("value"), scenario.get("value")
    if not b or s is None:
        return None
    return _r(s / b)
