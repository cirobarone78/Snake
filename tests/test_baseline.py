"""Tests for baseline forecasters — causality, signals, net returns, metrics."""

from __future__ import annotations

import pandas as pd
import pytest

from src.backtest.costs import BINANCE_SPOT, SlippageModel, TransactionCostModel
from src.models import baseline as bl


def _series(values: list[float]) -> pd.Series:
    idx = pd.date_range("2020-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=idx)


# --- returns ---


def test_returns_from_prices() -> None:
    r = bl.returns_from_prices(_series([100.0, 110.0, 99.0]))
    assert list(r) == pytest.approx([0.10, -0.10])


# --- random walk ---


def test_random_walk_is_all_zero() -> None:
    r = _series([0.01, -0.02, 0.03])
    f = bl.random_walk_forecast(r)
    assert (f == 0.0).all()
    assert f.index.equals(r.index)


# --- momentum ---


def test_momentum_is_trailing_mean_shifted() -> None:
    r = _series([0.10, 0.20, 0.30, 0.40, 0.50])
    f = bl.momentum_forecast(r, lookback=2)
    # f[t] = mean(r[t-2:t]); first two undefined (NaN)
    assert pd.isna(f.iloc[0])
    assert pd.isna(f.iloc[1])
    # f[2] = mean(0.10, 0.20) = 0.15 ; f[3] = mean(0.20,0.30)=0.25
    assert f.iloc[2] == pytest.approx(0.15)
    assert f.iloc[3] == pytest.approx(0.25)
    assert f.iloc[4] == pytest.approx(0.35)


def test_momentum_rejects_bad_lookback() -> None:
    with pytest.raises(ValueError, match="lookback must be positive"):
        bl.momentum_forecast(_series([0.1]), lookback=0)


def test_momentum_is_causal() -> None:
    """Appending a future return must not change earlier forecasts."""
    base = _series([0.01, -0.02, 0.03, 0.04, -0.01, 0.02, 0.05])
    extended = pd.concat([base, _series([0.99]).rename(None)])
    extended.index = pd.date_range(
        "2020-01-01", periods=len(extended), freq="D", tz="UTC"
    )
    a = bl.momentum_forecast(base, lookback=3)
    b = bl.momentum_forecast(extended, lookback=3).iloc[: len(base)]
    pd.testing.assert_series_equal(a, b, check_names=False)


# --- signal ---


def test_signal_sign_mapping_long_only() -> None:
    f = _series([0.5, -0.5, 0.0, 0.3])
    sig = bl.signal_from_forecast(f, long_only=True)
    assert list(sig) == pytest.approx([1.0, 0.0, 0.0, 1.0])


def test_signal_allows_shorts_when_not_long_only() -> None:
    f = _series([0.5, -0.5, 0.0])
    sig = bl.signal_from_forecast(f, long_only=False)
    assert list(sig) == pytest.approx([1.0, -1.0, 0.0])


def test_signal_nan_becomes_flat() -> None:
    f = _series([float("nan"), 0.2])
    sig = bl.signal_from_forecast(f)
    assert sig.iloc[0] == pytest.approx(0.0)


# --- strategy returns ---


def test_strategy_returns_gross_no_costs() -> None:
    pos = _series([1.0, 1.0, 0.0])
    ret = _series([0.10, -0.05, 0.20])
    s = bl.strategy_returns(pos, ret)
    # gross = pos * ret = 0.10, -0.05, 0.0
    assert list(s) == pytest.approx([0.10, -0.05, 0.0])


def test_strategy_returns_charges_turnover() -> None:
    pos = _series([1.0, 1.0, 0.0])
    ret = _series([0.10, -0.05, 0.20])
    # zero-fee, zero-slippage cost model → costs vanish, equals gross
    free = TransactionCostModel(
        fee=type(BINANCE_SPOT)(maker_rate=0.0, taker_rate=0.0),
        slippage=SlippageModel(base_cost_bps=0.0),
    )
    s_free = bl.strategy_returns(pos, ret, cost_model=free)
    assert list(s_free) == pytest.approx([0.10, -0.05, 0.0])

    # with cost: entry at t0 (turnover 1) and exit at t2 (turnover 1) charged
    model = TransactionCostModel(
        fee=type(BINANCE_SPOT)(maker_rate=0.001, taker_rate=0.001),
        slippage=SlippageModel(base_cost_bps=0.0),
    )
    rate = model.cost(1.0)  # 0.001
    s = bl.strategy_returns(pos, ret, cost_model=model)
    # t0: 0.10 - 1*rate ; t1: -0.05 - 0 ; t2: 0.0 - 1*rate
    assert s.iloc[0] == pytest.approx(0.10 - rate)
    assert s.iloc[1] == pytest.approx(-0.05)
    assert s.iloc[2] == pytest.approx(0.0 - rate)


def test_random_walk_strategy_never_trades() -> None:
    ret = _series([0.10, -0.05, 0.20, 0.01])
    f = bl.random_walk_forecast(ret)
    pos = bl.signal_from_forecast(f)
    s = bl.strategy_returns(pos, ret)
    # always flat → zero return every period, even with costs
    assert (s == 0.0).all()


# --- forecast quality metrics ---


def test_directional_accuracy_perfect_and_excludes_flat() -> None:
    f = _series([0.1, -0.2, 0.0, 0.3])
    r = _series([0.05, -0.01, 0.10, 0.02])
    # decidable: indices 0,1,3 (index 2 forecast is flat) → all match → 1.0
    assert bl.directional_accuracy(f, r) == pytest.approx(1.0)


def test_directional_accuracy_random_walk_is_nan() -> None:
    r = _series([0.1, -0.2, 0.3])
    f = bl.random_walk_forecast(r)
    # all forecasts flat → no decidable periods → NaN
    assert pd.isna(bl.directional_accuracy(f, r))


def test_directional_accuracy_half() -> None:
    f = _series([0.1, 0.1, 0.1, 0.1])
    r = _series([0.1, -0.1, 0.1, -0.1])
    assert bl.directional_accuracy(f, r) == pytest.approx(0.5)


def test_mean_absolute_error() -> None:
    f = _series([0.0, 0.0, 0.0])
    r = _series([0.1, -0.2, 0.3])
    assert bl.mean_absolute_error(f, r) == pytest.approx(0.2)


def test_mae_random_walk_equals_mean_abs_return() -> None:
    r = _series([0.1, -0.2, 0.3, -0.4])
    f = bl.random_walk_forecast(r)
    assert bl.mean_absolute_error(f, r) == pytest.approx(r.abs().mean())
