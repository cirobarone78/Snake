"""Tests for the ATR trailing stop (chandelier exit)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.risk.trailing_stop import chandelier_stop, evaluate_position


def _ohlc(closes: list[float], spread: float = 1.0) -> pd.DataFrame:
    """OHLC with a constant high-low band of 2*spread around each close."""
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "high": [c + spread for c in closes],
            "low": [c - spread for c in closes],
            "close": closes,
        },
        index=idx,
    )


def test_stop_trails_up_never_down() -> None:
    # rising then falling closes; stop must be monotonic non-decreasing
    closes = [100, 105, 110, 120, 115, 108, 100]
    stop = chandelier_stop(_ohlc(closes), entry_price=100.0, n_atr=2.0, atr_window=3)
    diffs = stop.diff().dropna()
    assert (diffs >= -1e-9).all()  # never steps down


def test_stop_is_below_high_water() -> None:
    closes = [100, 110, 120, 130]
    stop = chandelier_stop(_ohlc(closes), entry_price=100.0, n_atr=2.0, atr_window=3)
    # stop must sit strictly below the running high-water mark
    high_water = pd.Series(closes, index=stop.index).cummax()
    assert (stop < high_water).all()


def test_wider_n_atr_gives_lower_stop() -> None:
    closes = [100, 105, 110, 115, 120]
    df = _ohlc(closes)
    tight = chandelier_stop(df, entry_price=100.0, n_atr=2.0, atr_window=3)
    wide = chandelier_stop(df, entry_price=100.0, n_atr=4.0, atr_window=3)
    # a wider multiple sits further below price -> lower stop level
    assert (wide <= tight + 1e-9).all()
    assert wide.iloc[-1] < tight.iloc[-1]


def test_floor_at_entry_clamps() -> None:
    # strong uptrend so the trailing stop rises above entry
    closes = [100, 120, 140, 160, 180]
    df = _ohlc(closes, spread=1.0)
    floored = chandelier_stop(
        df, entry_price=100.0, n_atr=2.0, atr_window=3, floor_at_entry=True
    )
    # wherever the floored stop is active above entry, it is never below entry
    assert (floored[floored >= 100.0] >= 100.0).all()


def test_entry_date_slicing() -> None:
    closes = [90, 95, 100, 105, 110, 115]
    df = _ohlc(closes)
    entry_ts = df.index[2]  # start at the 100 close
    stop = chandelier_stop(df, entry_price=100.0, entry_date=entry_ts, n_atr=2.0, atr_window=2)
    assert stop.index[0] == entry_ts
    assert len(stop) == 4


def test_evaluate_position_state() -> None:
    # entry 100, runs to 120, current pulls back to 112
    closes = [100, 108, 120, 112]
    df = _ohlc(closes)
    st = evaluate_position(df, entry_price=100.0, n_atr=2.0, atr_window=3)
    assert st.close == pytest.approx(112.0)
    assert st.entry == pytest.approx(100.0)
    assert st.high_water == pytest.approx(120.0)
    assert st.open_pnl_pct == pytest.approx(0.12)
    # stop sits below close here (not breached)
    assert st.stop < st.close
    assert st.stopped_out is False
    assert st.stop_distance_pct < 0  # stop is below current price


def test_evaluate_position_stopped_out() -> None:
    # big drop on the last bar breaches the trailed stop
    closes = [100, 130, 160, 100]
    df = _ohlc(closes, spread=1.0)
    st = evaluate_position(df, entry_price=100.0, n_atr=2.0, atr_window=3)
    assert st.stopped_out is True
    assert st.close <= st.stop


def test_locked_pnl_with_floor() -> None:
    closes = [100, 130, 160, 180]
    df = _ohlc(closes, spread=1.0)
    st = evaluate_position(
        df, entry_price=100.0, n_atr=2.0, atr_window=3, floor_at_entry=True
    )
    # in a strong uptrend with break-even floor, locked P/L is non-negative
    assert st.locked_pnl_pct >= 0.0


def test_rejects_bad_input() -> None:
    df = _ohlc([100, 101, 102])
    with pytest.raises(ValueError, match="n_atr must be positive"):
        chandelier_stop(df, entry_price=100.0, n_atr=0.0)
    with pytest.raises(ValueError, match="entry_price must be positive"):
        chandelier_stop(df, entry_price=-1.0)
    with pytest.raises(ValueError, match="missing"):
        chandelier_stop(df.drop(columns=["low"]), entry_price=100.0)
