"""Offline tests for halving-cycle alignment analysis (Fase 5). No network."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.cycle_analysis import (
    analyse_cycle,
    compare_cycles,
    days_since_last_halving,
)


def _synthetic_cycle(halving: pd.Timestamp, peak_day: int, bottom_day: int) -> pd.Series:
    """Build a price series that rises to a peak then falls to a bottom."""
    idx = pd.date_range(halving, periods=1200, freq="D", tz="UTC")
    price = np.full(len(idx), 100.0)
    for i in range(len(idx)):
        if i <= peak_day:
            price[i] = 100.0 + (900.0 * i / peak_day)  # 100 -> 1000 at peak
        elif i <= bottom_day:
            frac = (i - peak_day) / (bottom_day - peak_day)
            price[i] = 1000.0 - (800.0 * frac)  # 1000 -> 200 at bottom
        else:
            price[i] = 200.0 + (i - bottom_day) * 0.5
    return pd.Series(price, index=idx)


def test_analyse_cycle_finds_peak_and_bottom() -> None:
    h = pd.Timestamp("2020-05-11", tz="UTC")
    close = _synthetic_cycle(h, peak_day=540, bottom_day=900)
    stats = analyse_cycle(close, h, phase_days=775)
    assert stats is not None
    assert abs(stats.peak_price - 1000.0) < 1.0
    assert stats.peak_days_after == 540
    assert abs(stats.bottom_price - 200.0) < 1.0
    assert stats.bottom_days_after == 900
    # at day 775 we are past the peak, in the decline -> negative drawdown
    assert stats.drawdown_from_peak_pct is not None
    assert stats.drawdown_from_peak_pct < 0


def test_analyse_cycle_drawdown_value() -> None:
    h = pd.Timestamp("2020-05-11", tz="UTC")
    close = _synthetic_cycle(h, peak_day=500, bottom_day=800)
    stats = analyse_cycle(close, h, phase_days=650)
    assert stats is not None
    # at day 650 (halfway peak->bottom): price ~600, peak 1000 -> ~-40%
    assert -55 < stats.drawdown_from_peak_pct < -25


def test_analyse_cycle_no_data_returns_none() -> None:
    h = pd.Timestamp("2030-01-01", tz="UTC")  # future, no data
    close = _synthetic_cycle(pd.Timestamp("2020-05-11", tz="UTC"), 500, 800)
    assert analyse_cycle(close, h, phase_days=775) is None


def test_days_since_last_halving() -> None:
    today = pd.Timestamp("2026-06-04", tz="UTC")
    d = days_since_last_halving(today)
    # last halving 2024-04-20 -> ~775 days
    assert 770 <= d <= 780


def test_compare_cycles_same_phase() -> None:
    # two cycles with the same shape -> at the same phase, same drawdown
    h1 = pd.Timestamp("2016-07-09", tz="UTC")
    h2 = pd.Timestamp("2020-05-11", tz="UTC")
    s1 = _synthetic_cycle(h1, 540, 900)
    s2 = _synthetic_cycle(h2, 540, 900)
    close = pd.concat([s1, s2]).sort_index()
    today = h2 + pd.Timedelta(days=700)
    stats = compare_cycles(close, today, halvings=[h1, h2])
    # both cycles evaluated at phase 700, same shape -> same drawdown sign
    assert len(stats) == 2
    assert all(s.phase_days == 700 for s in stats)
    assert all(s.drawdown_from_peak_pct is not None for s in stats)
