"""X4 / T-30: every frontend mock fixture must validate against the live API response models.

Catches contract drift between frontend/src/mocks/fixtures.ts (Dev-C) and api/models.py (Dev-A).
Skipped when `node` is unavailable. Needs Node >= 22.6 (--experimental-strip-types).
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from api import models

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def fixtures():
    if not shutil.which("node"):
        pytest.skip("node not installed")
    out = subprocess.run(
        ["node", "--experimental-strip-types", str(ROOT / "tests/contracts/dump_fixtures.mts")],
        capture_output=True, text=True, cwd=ROOT, check=True,
    ).stdout
    return json.loads(out)


def test_all_fixture_objects_match_api_models(fixtures):
    checked = 0
    for fx in fixtures.values():
        if fx["benchmark"]:
            models.Benchmark.model_validate(fx["benchmark"])
            checked += 1
        for a in fx["catalog"]["agents"]:
            models.Agent.model_validate(a); checked += 1
        for t in fx["catalog"]["tasks"]:
            models.TaskSummary.model_validate(t); checked += 1
        for r in fx["results"] + fx["compareResults"]:
            models.ResultRow.model_validate(r); checked += 1
        for r in fx["resilience"]:
            models.ResilienceRow.model_validate(r); checked += 1
        for r in fx["runs"]:
            models.RunDetail.model_validate(r); checked += 1
        for e in fx["events"]:
            models.Event.model_validate(e); checked += 1
    assert checked > 50, f"suspiciously few fixture objects checked: {checked}"
