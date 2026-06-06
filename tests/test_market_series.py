"""Offline tests for the market price-series export. No network."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.market_series import build_market_series, sparkline_values


def _series(start: float, end: float, n: int = 120) -> pd.Series:
    idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")
    return pd.Series(np.linspace(start, end, n), index=idx)


def test_build_market_series_shape_and_change() -> None:
    payload = build_market_series(
        {"BTC": _series(100, 200)}, names={"BTC": "Bitcoin"}, window=60,
        generated_at="2026-06-05T00:00:00Z",
    )
    assert payload["title"] == "Andamento di mercato"
    s = payload["series"][0]
    assert s["symbol"] == "BTC" and s["name"] == "Bitcoin"
    assert len(s["points"]) == 60  # trimmed to window
    assert set(s["points"][0]) == {"t", "v"}
    # change over the trimmed window is positive (ramp up)
    assert s["change_pct"] is not None and s["change_pct"] > 0
    assert s["last"] == s["points"][-1]["v"]


def test_build_market_series_skips_empty() -> None:
    payload = build_market_series({"X": pd.Series(dtype="float64")})
    assert payload["series"] == []


def test_sparkline_values_trims_and_rounds() -> None:
    vals = sparkline_values(_series(1.0, 2.0, n=100), window=20)
    assert len(vals) == 20
    assert all(isinstance(v, float) for v in vals)
