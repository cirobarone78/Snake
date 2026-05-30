"""Tests for technical indicators — known values, bounds, no-look-ahead."""

from __future__ import annotations

import pandas as pd
import pytest

from src.features import indicators as ind


def _series(values: list[float]) -> pd.Series:
    idx = pd.date_range("2020-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=idx)


def _ohlc(
    highs: list[float], lows: list[float], closes: list[float], volumes: list[float]
) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=len(closes), freq="D", tz="UTC")
    return pd.DataFrame(
        {"high": highs, "low": lows, "close": closes, "volume": volumes}, index=idx
    )


# --- SMA / EMA ---


def test_sma_known_values() -> None:
    s = ind.sma(_series([1.0, 2.0, 3.0, 4.0]), window=2)
    assert pd.isna(s.iloc[0])  # window not full yet
    assert list(s.iloc[1:]) == pytest.approx([1.5, 2.5, 3.5])
    assert s.name == "sma_2"


def test_ema_first_value_is_seed() -> None:
    # adjust=False → first EMA equals the first price.
    e = ind.ema(_series([10.0, 20.0, 30.0]), window=2)
    assert e.iloc[0] == pytest.approx(10.0)
    assert e.name == "ema_2"


def test_moving_averages_reject_bad_window() -> None:
    with pytest.raises(ValueError, match="window must be positive"):
        ind.sma(_series([1.0]), window=0)
    with pytest.raises(ValueError, match="window must be positive"):
        ind.ema(_series([1.0]), window=-1)


# --- MACD ---


def test_macd_columns_and_hist_identity() -> None:
    df = ind.macd(_series([float(i) for i in range(40)]))
    assert list(df.columns) == ["macd", "signal", "hist"]
    # hist must equal macd - signal everywhere it is defined
    assert (df["hist"] - (df["macd"] - df["signal"])).abs().max() == pytest.approx(0.0)


def test_macd_rejects_bad_params() -> None:
    with pytest.raises(ValueError, match="0 < fast < slow"):
        ind.macd(_series([1.0, 2.0]), fast=26, slow=12)
    with pytest.raises(ValueError, match="signal must be positive"):
        ind.macd(_series([1.0, 2.0]), signal=0)


# --- RSI ---


def test_rsi_all_gains_is_100() -> None:
    r = ind.rsi(_series([float(i) for i in range(1, 20)]), window=14)
    assert r.iloc[-1] == pytest.approx(100.0)


def test_rsi_all_losses_is_0() -> None:
    r = ind.rsi(_series([float(i) for i in range(20, 1, -1)]), window=14)
    assert r.iloc[-1] == pytest.approx(0.0)


def test_rsi_flat_series_is_50() -> None:
    # No gains and no losses → neutral 50, not NaN.
    r = ind.rsi(_series([100.0] * 20), window=14)
    assert r.iloc[-1] == pytest.approx(50.0)


def test_rsi_bounded_0_100() -> None:
    prices = _series([100.0, 102.0, 101.0, 105.0, 103.0, 108.0, 104.0, 110.0])
    r = ind.rsi(prices, window=5).dropna()
    assert (r >= 0.0).all()
    assert (r <= 100.0).all()


# --- Bollinger ---


def test_bollinger_bands_structure() -> None:
    prices = _series([float(i) for i in range(30)])
    bb = ind.bollinger_bands(prices, window=20, num_std=2.0)
    assert list(bb.columns) == ["mid", "upper", "lower"]
    valid = bb.dropna()
    assert (valid["upper"] >= valid["mid"]).all()
    assert (valid["mid"] >= valid["lower"]).all()


def test_bollinger_zero_std_collapses_bands() -> None:
    bb = ind.bollinger_bands(_series([100.0] * 25), window=20, num_std=2.0)
    last = bb.iloc[-1]
    assert last["upper"] == pytest.approx(last["lower"])
    assert last["mid"] == pytest.approx(100.0)


def test_bollinger_rejects_bad_params() -> None:
    with pytest.raises(ValueError, match="num_std must be non-negative"):
        ind.bollinger_bands(_series([1.0]), num_std=-1.0)


# --- ATR ---


def test_atr_constant_range() -> None:
    # high-low is a constant 2.0 and closes are flat → ATR converges to 2.0.
    df = _ohlc(
        highs=[101.0] * 20, lows=[99.0] * 20, closes=[100.0] * 20, volumes=[1.0] * 20
    )
    a = ind.atr(df, window=14)
    assert a.iloc[-1] == pytest.approx(2.0)
    assert a.name == "atr_14"


def test_atr_requires_columns() -> None:
    df = pd.DataFrame({"high": [1.0], "low": [0.5]})
    with pytest.raises(ValueError, match="missing columns"):
        ind.atr(df)


# --- OBV ---


def test_obv_signs_volume_by_direction() -> None:
    df = _ohlc(
        highs=[0, 0, 0, 0],
        lows=[0, 0, 0, 0],
        closes=[10.0, 11.0, 10.0, 10.0],
        volumes=[100.0, 200.0, 50.0, 30.0],
    )
    o = ind.obv(df)
    # day0 seed 0; up +200 → 200; down -50 → 150; flat +0 → 150
    assert list(o) == pytest.approx([0.0, 200.0, 150.0, 150.0])
    assert o.name == "obv"


def test_obv_requires_columns() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        ind.obv(pd.DataFrame({"close": [1.0]}))


# --- no-look-ahead contract ---


def test_indicators_are_causal() -> None:
    """Appending a future bar must not change earlier indicator values."""
    base = _series([float(i) for i in [10, 11, 12, 11, 13, 12, 14, 15, 13, 16]])
    extended = pd.concat([base, _series([99.0]).rename(None)])
    # rebuild a clean continuous index for the extended series
    extended.index = pd.date_range(
        "2020-01-01", periods=len(extended), freq="D", tz="UTC"
    )

    for fn in (
        lambda s: ind.sma(s, 3),
        lambda s: ind.ema(s, 3),
        lambda s: ind.rsi(s, 4),
        lambda s: ind.macd(s, 3, 6, 2)["macd"],
        lambda s: ind.bollinger_bands(s, 3)["upper"],
    ):
        a = fn(base)
        b = fn(extended).iloc[: len(base)]
        pd.testing.assert_series_equal(a, b, check_names=False)
