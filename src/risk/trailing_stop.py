"""ATR-based trailing stop / chandelier exit (risk management, equity & beyond).

A position exit rule that adapts to volatility instead of a fixed percentage.
The stop trails the highest price reached since entry, set ``n_atr`` multiples
of the Average True Range below it — so it widens in turbulent periods and
tightens in calm ones, and it only ever ratchets up, never down.

This is the "chandelier exit" (Chuck LeBeau). It is a **risk-management
overlay**, not a forecast: it answers "if I'm already in, where do I get out to
protect the position?", which is exactly the user-facing question this serves.
Per VISION/CLAUDE.md the system produces inputs, not decisions, and never
promises outcomes — a stop level is a rule, not a prediction, and a gap can
fill worse than the level (no guarantee of execution price).

Causal by construction (no look-ahead): the stop at day ``t`` uses only the
high-water mark and ATR up to and including ``t``. Asset-class-agnostic
(ADR-014): ATR window is in observations; works on any OHLC series.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pandas as pd

from src.features.indicators import atr


def _localize_entry(entry_date: str | pd.Timestamp, index: pd.Index) -> pd.Timestamp:
    """Coerce ``entry_date`` to a Timestamp matching the frame's tz, if any."""
    ts = pd.Timestamp(entry_date)
    if ts is pd.NaT:
        raise ValueError(f"entry_date is not a valid timestamp: {entry_date!r}")
    idx = cast("pd.DatetimeIndex", index)
    if ts.tzinfo is None and idx.tz is not None:
        ts = ts.tz_localize(idx.tz)
    return cast("pd.Timestamp", ts)


@dataclass(frozen=True)
class TrailingStopState:
    """The current trailing-stop picture for an open position.

    All prices in the instrument's own units. ``stop`` is the level to exit
    at; ``stopped_out`` is True if ``close`` has already breached it.
    """

    as_of: pd.Timestamp
    close: float
    entry: float
    high_water: float          # highest close since entry
    atr: float
    stop: float                # current trailing stop level
    n_atr: float
    stopped_out: bool

    @property
    def open_pnl_pct(self) -> float:
        """Open profit/loss vs entry, as a fraction."""
        return self.close / self.entry - 1.0

    @property
    def stop_distance_pct(self) -> float:
        """Distance from current close down to the stop, as a fraction."""
        return self.stop / self.close - 1.0

    @property
    def locked_pnl_pct(self) -> float:
        """P/L locked in if stopped out now (can be negative if stop < entry)."""
        return self.stop / self.entry - 1.0


def chandelier_stop(
    ohlc: pd.DataFrame,
    entry_price: float,
    entry_date: str | pd.Timestamp | None = None,
    n_atr: float = 3.0,
    atr_window: int = 14,
    floor_at_entry: bool = False,
) -> pd.Series:
    """Trailing stop series from ``entry_date`` onward (chandelier exit).

    ``stop[t] = high_water[t] - n_atr * ATR[t]``, where ``high_water[t]`` is the
    highest close from entry to ``t``. The stop is then made monotonic
    (cummax) so it never steps down. With ``floor_at_entry`` the stop is
    clamped to be at least ``entry_price`` once it would naturally reach it
    (a break-even ratchet).

    Returns a Series indexed from the entry date onward. Raises if the OHLC is
    missing required columns or the entry date is out of range.
    """
    needed = ("high", "low", "close")
    missing = [c for c in needed if c not in ohlc.columns]
    if missing:
        raise ValueError(f"chandelier_stop needs {list(needed)}; missing {missing}")
    if n_atr <= 0:
        raise ValueError("n_atr must be positive")
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")

    df = ohlc.sort_index()
    atr_series = atr(df, window=atr_window)

    if entry_date is not None:
        ts = _localize_entry(entry_date, df.index)
        df = df.loc[ts:]
        atr_series = atr_series.loc[ts:]
    if df.empty:
        raise ValueError("no data at or after entry_date")

    high_water = df["close"].cummax()
    raw_stop = high_water - n_atr * atr_series
    # Make the stop monotonic non-decreasing: it ratchets up, never down.
    trailing = raw_stop.cummax()
    if floor_at_entry:
        # Once the trailing stop reaches entry, never let it fall back below it.
        reached = trailing >= entry_price
        trailing = trailing.where(~reached, trailing.clip(lower=entry_price))
    return cast("pd.Series", trailing).rename(f"chandelier_{n_atr}atr")


def evaluate_position(
    ohlc: pd.DataFrame,
    entry_price: float,
    entry_date: str | pd.Timestamp | None = None,
    n_atr: float = 3.0,
    atr_window: int = 14,
    floor_at_entry: bool = False,
) -> TrailingStopState:
    """Snapshot the trailing-stop state as of the latest available bar.

    Convenience wrapper around ``chandelier_stop`` that returns the current
    actionable picture (stop level, distance, locked P/L, whether the last
    close has already breached the stop).
    """
    stop_series = chandelier_stop(
        ohlc,
        entry_price=entry_price,
        entry_date=entry_date,
        n_atr=n_atr,
        atr_window=atr_window,
        floor_at_entry=floor_at_entry,
    )
    df = ohlc.sort_index()
    if entry_date is not None:
        ts = _localize_entry(entry_date, df.index)
        df = df.loc[ts:]
    atr_series = atr(ohlc.sort_index(), window=atr_window).loc[df.index]

    last_ts = df.index[-1]
    last_close = float(df["close"].iloc[-1])
    high_water = float(df["close"].cummax().iloc[-1])
    stop = float(stop_series.iloc[-1])
    return TrailingStopState(
        as_of=cast("pd.Timestamp", last_ts),
        close=last_close,
        entry=entry_price,
        high_water=high_water,
        atr=float(atr_series.iloc[-1]),
        stop=stop,
        n_atr=n_atr,
        stopped_out=last_close <= stop,
    )
