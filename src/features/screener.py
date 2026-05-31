"""Crypto category (narrative) rotation screener (Fase 6).

The user's goal, restated honestly: not predicting a single coin years ahead, but
spotting *which narratives are moving now* and flagging opportunities/risks at a
moment one could act on — the crypto analogue of equity sector rotation
("AI/memory/nuclear are running"). Categories (AI, RWA, gaming, L2, meme, ...)
are CoinGecko's sector map; this module ranks them by current strength.

Three honesty guards baked in (CLAUDE.md):

- **Micro-cap filter**: a $5M category at +400% is a pump, not rotation. We
  require a minimum market cap so the ranking reflects real money rotating.
- **Outlier-robust scoring**: a +422% category would dominate a z-score blend
  and bury genuine rotation. We standardise *by cross-sectional rank* (percentile
  within the snapshot), which is naturally outlier-proof — a pump just gets the
  top rank, not a score that dwarfs everyone.
- **Volume-aware**: strength blends the move with turnover (volume/market-cap),
  so a category up on real trading beats one drifting up on thin volume.

This screener describes the *present snapshot*. The probabilistic layer ("given
this state, what historically happened next") needs accumulated history and is a
separate, later step — this module only produces today's ranked picture, and the
accompanying ingestion accumulates the snapshots that will feed that layer.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd

# A category needs at least this market cap (USD) to count as "real rotation"
# rather than micro-cap pump noise. ~100M is a conservative screener floor.
DEFAULT_MIN_MARKET_CAP: float = 1e8

_OUT_COLS = [
    "category_id", "name", "market_cap", "volume_24h",
    "change_24h_pct", "top_coins", "turnover", "score", "signal",
]


def _rank_pct(values: np.ndarray) -> np.ndarray:
    """Cross-sectional percentile rank in ``[0, 1]`` (outlier-robust).

    Ties get their average rank; a single element or all-equal input -> 0.5
    (neutral). Unlike a z-score, an extreme outlier only ever reaches rank 1.0,
    so one pump cannot dominate the blended score. NaNs are ranked as the
    lowest (treated as weakest), which is fine for a strength ranking.
    """
    n = len(values)
    if n <= 1:
        return np.full(n, 0.5)
    order = np.argsort(np.argsort(values, kind="stable"), kind="stable").astype("float64")
    return order / (n - 1)


def _signal_label(score: float) -> str:
    """Map a composite score in [0,1] to a coarse label (0.5 = median category)."""
    if pd.isna(score):
        return "neutral"
    if score >= 0.85:
        return "hot"
    if score >= 0.65:
        return "warm"
    return "neutral"


def _cap_filter(categories: pd.DataFrame, min_market_cap: float) -> pd.DataFrame:
    mcap = categories["market_cap"].fillna(0.0).to_numpy(dtype="float64")
    return cast("pd.DataFrame", categories.loc[mcap >= min_market_cap].copy())


def screen_categories(
    categories: pd.DataFrame,
    min_market_cap: float = DEFAULT_MIN_MARKET_CAP,
    top_n: int = 10,
) -> pd.DataFrame:
    """Rank categories by a composite, outlier-robust current-strength score.

    Expects the frame from ``CoinGeckoSource.fetch_categories``: columns
    ``category_id, name, market_cap, volume_24h, change_24h_pct, top_coins``.

    ``score = mean(rank_pct(change_24h_pct), rank_pct(turnover))`` in ``[0, 1]``,
    where ``rank_pct`` is the cross-sectional percentile within the cap-filtered
    snapshot and ``turnover = volume_24h / market_cap``. Returns the top
    ``top_n`` by score with ``turnover``, ``score`` and a ``signal`` label
    (``hot`` >= 0.85, ``warm`` >= 0.65, else ``neutral``). Pure, no network.
    """
    if categories.empty:
        return pd.DataFrame(columns=_OUT_COLS)
    df = _cap_filter(categories, min_market_cap)
    if df.empty:
        return pd.DataFrame(columns=_OUT_COLS)

    mcap = df["market_cap"].to_numpy(dtype="float64")
    vol = df["volume_24h"].fillna(0.0).to_numpy(dtype="float64")
    change = df["change_24h_pct"].to_numpy(dtype="float64")
    turnover = np.divide(vol, mcap, out=np.zeros_like(vol), where=mcap > 0)

    df["turnover"] = turnover
    df["score"] = (_rank_pct(change) + _rank_pct(turnover)) / 2.0
    df = cast("pd.DataFrame", df.sort_values("score", ascending=False, na_position="last"))
    df["signal"] = [_signal_label(float(s)) for s in df["score"].to_numpy()]
    df.index = pd.RangeIndex(start=1, stop=len(df) + 1, name="rank")
    keep = [c for c in _OUT_COLS if c in df.columns]
    return cast("pd.DataFrame", df[keep].head(top_n))


def screen_movers(
    categories: pd.DataFrame,
    min_market_cap: float = DEFAULT_MIN_MARKET_CAP,
    n: int = 5,
) -> dict[str, pd.DataFrame]:
    """Top gainers and losers by cap-weighted 24h move (cap-filtered).

    Returns ``{"gainers": ..., "losers": ...}``, each a frame of ``n`` rows with
    ``name, market_cap, change_24h_pct, top_coins``. The "risks now" side
    (losers) matters as much as opportunities — the user asked for both.
    """
    out_cols = ["name", "market_cap", "change_24h_pct", "top_coins"]
    if categories.empty:
        empty = pd.DataFrame(columns=out_cols)
        return {"gainers": empty, "losers": empty.copy()}

    df = _cap_filter(categories, min_market_cap)
    has_change = df["change_24h_pct"].notna().to_numpy()
    df = cast("pd.DataFrame", df.loc[has_change])
    ranked = cast("pd.DataFrame", df.sort_values("change_24h_pct", ascending=False))
    gainers = cast("pd.DataFrame", ranked.head(n)[out_cols].reset_index(drop=True))
    losers = cast("pd.DataFrame", ranked.tail(n)[out_cols].iloc[::-1].reset_index(drop=True))
    return {"gainers": gainers, "losers": losers}
