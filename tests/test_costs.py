"""Tests for the transaction cost model — fees, slippage, spread proxy."""

from __future__ import annotations

import pandas as pd
import pytest

from src.backtest.costs import (
    BINANCE_SPOT,
    KRAKEN_SPOT,
    FeeModel,
    SlippageModel,
    TransactionCostModel,
    estimate_half_spread_bps,
)

# --- fees ---


def test_fee_maker_vs_taker() -> None:
    fm = FeeModel(maker_rate=0.001, taker_rate=0.002)
    assert fm.fee(10_000) == pytest.approx(20.0)  # taker by default
    assert fm.fee(10_000, maker=True) == pytest.approx(10.0)


def test_fee_is_sign_agnostic() -> None:
    fm = FeeModel(maker_rate=0.001, taker_rate=0.001)
    assert fm.fee(-10_000) == pytest.approx(fm.fee(10_000))


def test_reference_schedules() -> None:
    assert BINANCE_SPOT.taker_rate == pytest.approx(0.0010)
    assert KRAKEN_SPOT.maker_rate == pytest.approx(0.0016)
    assert KRAKEN_SPOT.taker_rate == pytest.approx(0.0026)
    # Kraken is the more expensive venue (ADR-012).
    assert KRAKEN_SPOT.taker_rate > BINANCE_SPOT.taker_rate


def test_fee_rejects_negative() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        FeeModel(maker_rate=-0.001, taker_rate=0.001)


# --- slippage ---


def test_slippage_floor_applies_when_spread_below_floor() -> None:
    sm = SlippageModel(base_cost_bps=2.0)
    # spread 1 bp < floor 2 bp → floor wins
    assert sm.cost(10_000, half_spread_bps=1.0) == pytest.approx(2.0)


def test_slippage_uses_spread_when_above_floor() -> None:
    sm = SlippageModel(base_cost_bps=2.0)
    assert sm.cost(10_000, half_spread_bps=5.0) == pytest.approx(5.0)


def test_slippage_market_impact_scales_with_size() -> None:
    sm = SlippageModel(base_cost_bps=2.0, impact_coeff=0.1)
    # size_adj = 1 + 0.1 * (10_000 / 100_000) = 1.01
    assert sm.cost(10_000, half_spread_bps=2.0, avg_daily_volume=100_000) == pytest.approx(
        2.0 * 1.01
    )


def test_slippage_impact_ignored_when_coeff_zero() -> None:
    sm = SlippageModel(base_cost_bps=2.0, impact_coeff=0.0)
    with_adv = sm.cost(10_000, half_spread_bps=2.0, avg_daily_volume=100_000)
    without_adv = sm.cost(10_000, half_spread_bps=2.0)
    assert with_adv == pytest.approx(without_adv)


def test_slippage_rejects_negative_inputs() -> None:
    with pytest.raises(ValueError, match="base_cost_bps"):
        SlippageModel(base_cost_bps=-1.0)
    with pytest.raises(ValueError, match="impact_coeff"):
        SlippageModel(impact_coeff=-1.0)
    with pytest.raises(ValueError, match="half_spread_bps"):
        SlippageModel().cost(10_000, half_spread_bps=-1.0)


def test_slippage_positive_impact_requires_positive_volume() -> None:
    sm = SlippageModel(impact_coeff=0.1)
    with pytest.raises(ValueError, match="avg_daily_volume"):
        sm.cost(10_000, half_spread_bps=2.0, avg_daily_volume=-5.0)


# --- combined ---


def test_transaction_cost_is_fee_plus_slippage() -> None:
    model = TransactionCostModel(fee=BINANCE_SPOT, slippage=SlippageModel(base_cost_bps=2.0))
    # fee: 10_000 * 0.001 = 10 ; slippage floor 2 bp on 10_000 = 2 → 12
    assert model.cost(10_000, half_spread_bps=1.0) == pytest.approx(12.0)


def test_transaction_cost_default_slippage() -> None:
    model = TransactionCostModel(fee=KRAKEN_SPOT)
    # default SlippageModel floor 2 bp; taker fee 0.26%
    expected = 10_000 * 0.0026 + 10_000 * 2.0 * 1e-4
    assert model.cost(10_000) == pytest.approx(expected)


# --- spread proxy ---


def _ohlc(highs: list[float], lows: list[float], closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=len(closes), freq="D", tz="UTC")
    return pd.DataFrame({"high": highs, "low": lows, "close": closes}, index=idx)


def test_estimate_half_spread_uses_lower_quantile() -> None:
    # ranges/close: 0.02, 0.04, 0.01, 0.03 ; quantile 0.0 → rolling min
    df = _ohlc(
        highs=[101.0, 102.0, 100.5, 101.5],
        lows=[99.0, 98.0, 99.5, 98.5],
        closes=[100.0, 100.0, 100.0, 100.0],
    )
    half = estimate_half_spread_bps(df, window=4, quantile=0.0)
    # last point: min range 0.01 → half 0.005 → 50 bps
    assert half.iloc[-1] == pytest.approx(50.0)


def test_estimate_half_spread_validation() -> None:
    good = _ohlc([101.0], [99.0], [100.0])
    with pytest.raises(ValueError, match="quantile must be"):
        estimate_half_spread_bps(good, quantile=1.5)
    with pytest.raises(ValueError, match="window must be"):
        estimate_half_spread_bps(good, window=0)
    bad = good.drop(columns=["low"])
    with pytest.raises(ValueError, match="missing"):
        estimate_half_spread_bps(bad)


def test_estimate_half_spread_feeds_slippage() -> None:
    df = _ohlc([101.0, 102.0], [99.0, 98.0], [100.0, 100.0])
    spread_bps = float(estimate_half_spread_bps(df, window=2, quantile=0.0).iloc[-1])
    cost = SlippageModel(base_cost_bps=0.0).cost(10_000, half_spread_bps=spread_bps)
    assert cost == pytest.approx(10_000 * spread_bps * 1e-4)
