"""T-15: stats engine vs hand-computed goldens (docs/03 F-07). No DB needed."""
import math

import pytest

from api import stats

Z = stats.Z95


def approx(x):
    return pytest.approx(x, abs=1e-6)


# ---- Wilson ---------------------------------------------------------------------------------
def test_wilson_matches_hand_computation():
    # p=11/15, z=1.96: centre=(p+z²/2n)/(1+z²/n), half=z·sqrt(p(1-p)/n+z²/4n²)/(1+z²/n)
    r = stats.wilson(11, 15)
    assert (r["passed"], r["n"], r["value"]) == (11, 15, approx(0.733333))
    assert (r["ci_low"], r["ci_high"]) == (approx(0.480496), approx(0.891025))


def test_wilson_all_fail_and_all_pass_still_defined():
    zero = stats.wilson(0, 10)
    assert (zero["value"], zero["ci_low"]) == (0.0, 0.0)
    assert zero["ci_high"] == approx(Z * Z / (10 + Z * Z))           # 0.277533
    full = stats.wilson(10, 10)
    assert (full["value"], full["ci_high"]) == (1.0, 1.0)
    assert full["ci_low"] == approx(10 / (10 + Z * Z))               # 0.722467


def test_wilson_n0_is_null_never_zero_percent():
    assert stats.wilson(0, 0) == {"passed": 0, "n": 0, "value": None, "ci_low": None, "ci_high": None}


# ---- describe / bootstrap -------------------------------------------------------------------
def test_describe_mean_median_sample_std():
    d = stats.describe([1, 2, 3, 4])
    assert (d["n"], d["mean"], d["median"]) == (4, 2.5, 2.5)
    assert d["std"] == approx(math.sqrt(5 / 3))                      # sample std (n-1)
    assert d["ci_low"] <= d["mean"] <= d["ci_high"]
    assert 1 <= d["ci_low"] and d["ci_high"] <= 4


def test_describe_skips_nulls_and_odd_median():
    d = stats.describe([3, None, 1, 2])
    assert (d["n"], d["mean"], d["median"]) == (3, 2.0, 2.0)


def test_describe_n0_and_n1():
    assert stats.describe([]) == {"n": 0, "mean": None, "median": None, "std": None,
                                  "ci_low": None, "ci_high": None}
    assert stats.describe([None])["n"] == 0
    one = stats.describe([7.5])
    assert (one["n"], one["mean"], one["median"], one["std"], one["ci_low"], one["ci_high"]) == \
        (1, 7.5, 7.5, None, None, None)


def test_bootstrap_constant_sample_and_fixed_seed():
    assert stats.bootstrap_mean_ci([5, 5, 5]) == (5.0, 5.0)
    vals = [0.01, 0.02, 0.05, 0.03, 0.04, 0.02]
    assert stats.bootstrap_mean_ci(vals) == stats.bootstrap_mean_ci(vals)  # reproducible
    assert stats.bootstrap_mean_ci(vals) != stats.bootstrap_mean_ci(vals, seed=1)


def test_bootstrap_two_points_hand_computed():
    # [0, 1]: each resample mean is 0, 0.5 or 1; with 1000 resamples the 2.5% / 97.5%
    # percentiles land on the extremes.
    assert stats.bootstrap_mean_ci([0.0, 1.0]) == (0.0, 1.0)


# ---- result rows ----------------------------------------------------------------------------
def run(status, cost=None, steps=None, tool_calls=None, duration=None, conf="verified"):
    return {"status": status, "cost": cost, "steps": steps, "tool_calls": tool_calls,
            "duration": duration, "cost_confidence": conf}


def test_result_row_excludes_infra_and_counts_confidence():
    runs = [run("PASS", 0.01, 4, 5, 10.0), run("PASS", 0.03, 6, 7, 20.0, conf="estimated"),
            run("FAIL", 0.02, 5, 6, 30.0), run("INFRA_ERROR", 0.5, 99, 99, 999.0)]
    r = stats.result_row("a", None, "baseline", runs)
    assert (r["runs_counted"], r["infra_excluded"]) == (3, 1)
    assert (r["pass_rate"]["passed"], r["pass_rate"]["n"]) == (2, 3)
    assert r["cost"]["mean"] == approx(0.02) and r["steps"]["median"] == 5
    assert r["duration"]["mean"] == approx(20.0)
    assert r["cost_confidence"] == {"verified": 2, "estimated": 1}


def test_result_row_only_infra_gives_nulls():
    r = stats.result_row("a", "t", "baseline", [run("INFRA_ERROR")])
    assert r["runs_counted"] == 0 and r["infra_excluded"] == 1
    assert r["pass_rate"]["value"] is None and r["cost"]["mean"] is None


def test_sort_pass_rate_desc_then_cost_asc_nulls_last():
    def row(agent, pr, cost):
        return {"agent_id": agent, "task_id": None, "pass_rate": {"value": pr}, "cost": {"mean": cost}}
    rows = [row("d", None, 0.01), row("c", 0.5, None), row("b", 0.5, 0.02), row("a", 0.5, 0.01),
            row("e", 0.9, 0.5)]
    assert [r["agent_id"] for r in stats.sort_rows(rows)] == ["e", "a", "b", "c", "d"]


def test_resilience_score():
    assert stats.resilience_score({"value": 0.8}, {"value": 0.4}) == 0.5
    assert stats.resilience_score({"value": 0.0}, {"value": 0.4}) is None
    assert stats.resilience_score({"value": None}, {"value": 0.4}) is None
    assert stats.resilience_score({"value": 0.5}, {"value": None}) is None
