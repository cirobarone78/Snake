"""Tests for walk-forward OOS evaluation — selection, alignment, costs."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest.costs import BINANCE_SPOT, SlippageModel, TransactionCostModel
from src.backtest.walkforward import oos_index_start, oos_strategy_returns
from src.models import baseline as bl


def _returns(n: int, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2018-01-01", periods=n, freq="D", tz="UTC")
    return pd.Series(rng.normal(0.001, 0.02, n), index=idx)


def test_too_short_returns_empty() -> None:
    r = _returns(100)  # < train_size + test_size
    f = bl.momentum_forecast(r, lookback=10)
    out = oos_strategy_returns(r, f, train_size=365, test_size=90)
    assert out.empty
    assert oos_index_start(r, train_size=365, test_size=90) is None


def test_oos_covers_only_test_windows() -> None:
    r = _returns(800)
    f = bl.momentum_forecast(r, lookback=30)
    out = oos_strategy_returns(r, f, train_size=365, test_size=90)
    start = oos_index_start(r, train_size=365, test_size=90)
    assert start is not None
    # first OOS return is at the start of the first test window (position 365)
    assert out.index.min() == start
    assert out.index.min() == r.index[365]
    # nothing before the first test window leaks in
    assert (out.index >= start).all()


def test_oos_windows_are_contiguous_and_nonoverlapping() -> None:
    r = _returns(800)
    f = bl.momentum_forecast(r, lookback=30)
    out = oos_strategy_returns(r, f, train_size=365, test_size=90)
    # default step == test_size -> tiled, no duplicate timestamps
    assert not out.index.has_duplicates
    assert out.index.is_monotonic_increasing


def test_random_walk_strategy_is_flat() -> None:
    r = _returns(800)
    f = bl.random_walk_forecast(r)
    out = oos_strategy_returns(r, f, train_size=365, test_size=90)
    # zero forecast -> long-only flat -> zero return every OOS period
    assert (out == 0.0).all()
    assert len(out) > 0


def test_costs_reduce_returns() -> None:
    r = _returns(800, seed=3)
    f = bl.momentum_forecast(r, lookback=30)
    gross = oos_strategy_returns(r, f, train_size=365, test_size=90)
    model = TransactionCostModel(fee=BINANCE_SPOT, slippage=SlippageModel(base_cost_bps=2.0))
    net = oos_strategy_returns(r, f, train_size=365, test_size=90, cost_model=model)
    assert gross.index.equals(net.index)
    # costs can only subtract, so cumulative net <= cumulative gross
    assert net.sum() <= gross.sum() + 1e-12
    # and on a trading strategy they strictly bite somewhere
    assert net.sum() < gross.sum()


def test_expanding_vs_rolling_same_oos_start() -> None:
    r = _returns(800)
    f = bl.momentum_forecast(r, lookback=30)
    exp = oos_strategy_returns(r, f, train_size=365, test_size=90, expanding=True)
    rol = oos_strategy_returns(r, f, train_size=365, test_size=90, expanding=False)
    # the OOS test windows are identical regardless of train mode
    assert exp.index.equals(rol.index)
