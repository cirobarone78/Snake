"""Equity sector/theme rotation screener (Fase 8).

The equity analogue of the crypto category screener: given recent OHLCV for a
set of sector/theme ETFs, rank which sectors are strongest *now* and which are
weakest (risks). Same honesty guards as the crypto one (CLAUDE.md):

- **Outlier-robust scoring**: cross-sectional percentile rank, so one ETF with a
  freak move can't dominate.
- **Multi-horizon strength**: blends 5-day and 21-day (≈1 month) momentum, so a
  one-day spike doesn't masquerade as rotation; ~1 month is where sector
  rotation actually shows.

Pure functions over pandas; the snapshot frame is built by ``build_sector_frame``
from a dict of per-symbol close-price Series (fetched elsewhere, so this stays
network-free and testable offline).
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd

_OUT_COLS = ["symbol", "name", "ret_5d_pct", "ret_21d_pct", "score", "signal"]


def _rank_pct(values: np.ndarray) -> np.ndarray:
    """Cross-sectional percentile rank in ``[0, 1]`` (outlier-robust)."""
    n = len(values)
    if n <= 1:
        return np.full(n, 0.5)
    order = np.argsort(np.argsort(values, kind="stable"), kind="stable").astype("float64")
    return order / (n - 1)


def _signal_label(score: float) -> str:
    if pd.isna(score):
        return "neutral"
    if score >= 0.85:
        return "hot"
    if score >= 0.65:
        return "warm"
    if score <= 0.15:
        return "weak"
    return "neutral"


def build_sector_frame(
    closes: dict[str, pd.Series],
    names: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Build a current-strength snapshot from per-symbol close-price Series.

    ``closes`` maps symbol -> a chronological close Series (daily). For each we
    compute 5-day and 21-day trailing returns (causal: last vs N bars ago).
    Symbols with too little history are skipped. Returns a frame with
    ``symbol, name, ret_5d_pct, ret_21d_pct`` (one row per symbol). Empty input
    -> empty frame.
    """
    names = names or {}
    rows: list[dict[str, object]] = []
    for symbol, close in closes.items():
        s = close.dropna()
        if len(s) < 22:
            continue
        last = float(s.iloc[-1])
        ret_5d = (last / float(s.iloc[-6]) - 1.0) * 100.0
        ret_21d = (last / float(s.iloc[-22]) - 1.0) * 100.0
        rows.append(
            {
                "symbol": symbol,
                "name": names.get(symbol, symbol),
                "ret_5d_pct": ret_5d,
                "ret_21d_pct": ret_21d,
            }
        )
    return pd.DataFrame(rows, columns=["symbol", "name", "ret_5d_pct", "ret_21d_pct"])


def screen_sectors(frame: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Rank sectors by composite strength (5d + 21d momentum, rank-based).

    ``score = mean(rank_pct(ret_5d), rank_pct(ret_21d))`` in ``[0, 1]``. Adds a
    ``signal`` label (hot/warm/neutral/weak) and returns the top ``top_n`` by
    score. Pure, no network. Empty input -> empty typed frame.
    """
    if frame.empty:
        return pd.DataFrame(columns=_OUT_COLS)
    df = frame.copy()
    r5 = df["ret_5d_pct"].to_numpy(dtype="float64")
    r21 = df["ret_21d_pct"].to_numpy(dtype="float64")
    df["score"] = (_rank_pct(r5) + _rank_pct(r21)) / 2.0
    df = cast("pd.DataFrame", df.sort_values("score", ascending=False))
    df["signal"] = [_signal_label(float(s)) for s in df["score"].to_numpy()]
    df.index = pd.RangeIndex(start=1, stop=len(df) + 1, name="rank")
    return cast("pd.DataFrame", df[_OUT_COLS].head(top_n))
