"""Versioned token prices (docs/07 section 8)."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Price:
    input_per_1m: float
    output_per_1m: float
    effective_from: dt.date


class Pricing:
    def __init__(self, version: str, models: dict[str, list[Price]]):
        self.version = version
        self.models = models

    @classmethod
    def load(cls, path: str | Path) -> Pricing:
        doc = yaml.safe_load(Path(path).read_text(encoding="utf8")) or {}
        models: dict[str, list[Price]] = {}
        for name, entries in (doc.get("models") or {}).items():
            # One mapping per model (07 section 8) or a list of them for price changes over time.
            for e in entries if isinstance(entries, list) else [entries]:
                eff = e["effective_from"]
                eff = eff if isinstance(eff, dt.date) else dt.date.fromisoformat(str(eff))
                models.setdefault(name, []).append(
                    Price(float(e["input_per_1m_tokens"]), float(e["output_per_1m_tokens"]), eff))
        for prices in models.values():
            prices.sort(key=lambda p: p.effective_from)
        return cls(str(doc.get("version", "unknown")), models)

    def price_for(self, model: str | None, on: dt.date) -> Price | None:
        """Latest entry for `model` whose effective_from is on or before `on`."""
        best = None
        for p in self.models.get(model or "", []):
            if p.effective_from <= on:
                best = p
        return best

    def cost(self, model: str | None, on: dt.date, tokens_in: int, tokens_out: int) -> float | None:
        p = self.price_for(model, on)
        if p is None:
            return None
        return round((tokens_in * p.input_per_1m + tokens_out * p.output_per_1m) / 1_000_000, 6)
