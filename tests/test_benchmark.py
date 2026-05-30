"""Tests for passive benchmarks — buy-and-hold and DCA."""

from __future__ import annotations

import pandas as pd
import pytest

from src.backtest.benchmark import (
    buy_and_hold_equity,
    buy_and_hold_returns,
    dca_equity,
)


def _prices(values: list[float]) -> pd.Series:
    idx = pd.date_range("2020-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=idx)


def test_buy_and_hold_equity_scales_with_price() -> None:
    eq = buy_and_hold_equity(_prices([100.0, 110.0, 121.0]), initial_capital=1000.0)
    assert list(eq) == pytest.approx([1000.0, 1100.0, 1210.0])


def test_buy_and_hold_returns_are_pct_change() -> None:
    r = buy_and_hold_returns(_prices([100.0, 110.0, 121.0]))
    assert list(r) == pytest.approx([0.1, 0.1])


def test_buy_and_hold_empty() -> None:
    assert buy_and_hold_equity(_prices([])).empty


def test_dca_buys_every_period() -> None:
    df = dca_equity(_prices([10.0, 20.0, 40.0, 80.0]), contribution=100.0, every=1)
    assert list(df["invested"]) == pytest.approx([100.0, 200.0, 300.0, 400.0])
    assert list(df["units"]) == pytest.approx([10.0, 15.0, 17.5, 18.75])
    assert list(df["equity"]) == pytest.approx([100.0, 300.0, 700.0, 1500.0])


def test_dca_respects_cadence() -> None:
    # Buys only at positions 0 and 2.
    df = dca_equity(_prices([10.0, 20.0, 40.0, 80.0]), contribution=100.0, every=2)
    assert list(df["invested"]) == pytest.approx([100.0, 100.0, 200.0, 200.0])
    assert list(df["units"]) == pytest.approx([10.0, 10.0, 12.5, 12.5])
    assert list(df["equity"]) == pytest.approx([100.0, 200.0, 500.0, 1000.0])


def test_dca_equity_feeds_metrics_via_pct_change() -> None:
    df = dca_equity(_prices([10.0, 20.0, 40.0, 80.0]), contribution=100.0, every=2)
    returns = df["equity"].pct_change().dropna()
    assert len(returns) == 3  # one fewer than the equity curve


def test_dca_invalid_params_raise() -> None:
    with pytest.raises(ValueError, match="contribution must be positive"):
        dca_equity(_prices([10.0, 20.0]), contribution=0.0)
    with pytest.raises(ValueError, match="every must be positive"):
        dca_equity(_prices([10.0, 20.0]), contribution=100.0, every=0)


def test_dca_empty_prices() -> None:
    df = dca_equity(_prices([]), contribution=100.0)
    assert df.empty
    assert list(df.columns) == ["invested", "units", "equity"]
