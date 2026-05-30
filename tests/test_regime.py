"""Tests for regime classification and regime-aware metric decomposition."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features.regime import (
    Regime,
    classify_regime,
    regime_fractions,
    summarize_by_regime,
)


def _series(values: list[float]) -> pd.Series:
    idx = pd.date_range("2020-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=idx)


# --- classify_regime ---


def test_classify_warmup_is_unknown() -> None:
    prices = _series([float(i) for i in range(1, 11)])
    reg = classify_regime(prices, window=5)
    # first window-1 = 4 points have no SMA -> unknown
    assert (reg.iloc[:4] == Regime.UNKNOWN.value).all()
    assert (reg.iloc[4:] != Regime.UNKNOWN.value).all()


def test_classify_rising_series_is_bull() -> None:
    # strictly increasing -> price is always at/above its trailing SMA
    prices = _series([float(i) for i in range(1, 21)])
    reg = classify_regime(prices, window=5)
    decided = reg[reg != Regime.UNKNOWN.value]
    assert (decided == Regime.BULL.value).all()


def test_classify_falling_series_is_bear() -> None:
    prices = _series([float(i) for i in range(20, 0, -1)])
    reg = classify_regime(prices, window=5)
    decided = reg[reg != Regime.UNKNOWN.value]
    assert (decided == Regime.BEAR.value).all()


def test_classify_is_causal() -> None:
    """Appending a future price must not change earlier regime labels."""
    base = _series([10, 11, 12, 11, 13, 14, 13, 15, 16, 14, 17, 18])
    extended = pd.concat([base, _series([999.0]).rename(None)])
    extended.index = pd.date_range(
        "2020-01-01", periods=len(extended), freq="D", tz="UTC"
    )
    a = classify_regime(base, window=4)
    b = classify_regime(extended, window=4).iloc[: len(base)]
    pd.testing.assert_series_equal(a, b, check_names=False)


def test_classify_rejects_bad_window() -> None:
    with pytest.raises(ValueError, match="window must be positive"):
        classify_regime(_series([1.0, 2.0]), window=0)


# --- summarize_by_regime ---


def test_summarize_by_regime_keys() -> None:
    prices = _series([float(i) for i in range(1, 60)])
    returns = prices.pct_change().dropna()
    reg = classify_regime(prices, window=10)
    out = summarize_by_regime(returns, reg)
    assert "full" in out
    # strictly rising -> only bull decided, no bear segment
    assert "bull" in out
    assert "bear" not in out


def test_summarize_by_regime_separates_bull_and_bear() -> None:
    # up then down: both regimes present
    up = [float(i) for i in range(1, 41)]
    down = [float(i) for i in range(40, 0, -1)]
    prices = _series(up + down)
    returns = prices.pct_change().dropna()
    reg = classify_regime(prices, window=10)
    out = summarize_by_regime(returns, reg)
    assert "bull" in out and "bear" in out
    # bull segment had positive returns, bear negative
    assert out["bull"].total_return > 0
    assert out["bear"].total_return < 0
    # full sample period count >= sum makes sense (unknown dropped)
    assert out["full"].n_periods >= out["bull"].n_periods + out["bear"].n_periods


def test_summarize_by_regime_excludes_unknown() -> None:
    prices = _series([float(i) for i in range(1, 30)])
    returns = prices.pct_change().dropna()
    reg = classify_regime(prices, window=10)
    out = summarize_by_regime(returns, reg)
    # bull periods must be fewer than full (warm-up unknown dropped)
    assert out["bull"].n_periods < out["full"].n_periods


# --- regime_fractions ---


def test_regime_fractions_sum_to_one() -> None:
    up = [float(i) for i in range(1, 31)]
    down = [float(i) for i in range(30, 0, -1)]
    prices = _series(up + down)
    reg = classify_regime(prices, window=10)
    fr = regime_fractions(reg)
    assert fr[Regime.BULL.value] + fr[Regime.BEAR.value] == pytest.approx(1.0)
    assert 0.0 < fr[Regime.BULL.value] < 1.0


def test_regime_fractions_all_unknown_is_nan() -> None:
    prices = _series([1.0, 2.0, 3.0])
    reg = classify_regime(prices, window=10)  # window > len -> all unknown
    fr = regime_fractions(reg)
    assert np.isnan(fr[Regime.BULL.value])
    assert np.isnan(fr[Regime.BEAR.value])
