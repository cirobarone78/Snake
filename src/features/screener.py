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
  within the snapshot), which is naturally outlier-proof — the standard approach
  in cross-sectional factor models. A pump just gets the top rank, not a score
  that dwarfs everyone.
- **Volume-aware**: strength blends the move with turnover (volume/market-cap),
  so a category up on real trading beats one drifting up on thin volume.

This screener describes the *present snapshot*. The probabilistic layer ("given
this state, what historically happened next") needs accumulated history and is a
separate, later step — this module only produces today's ranked picture, and the
accompanying ingestion accumulates the snapshots that will feed that layer.
"""

from __future__ import annotations

from typing import cast

import pandas as pd

# A category needs at least this market cap (USD) to count as "real rotation"
# rather than micro-cap pump noise. ~100M is a conservative screener floor.
DEFAULT_MIN_MARKET_CAP: float = 1e8

_OUT_COLS = [
    "category_id", "name", "market_cap", "volume_24h",
    "change_24h_pct", "turnover", "score", "signal",
]


def _rank_pct(s: pd.Series) -> pd.Series:
    """Cross-sectional percentile rank in ``[0, 1]`` (outlier-robust).

    Ties averaged; a single row or all-equal column -> 0.5 (neutral). NaNs keep
    NaN. Unlike a z-score, an extreme outlier only ever reaches rank 1.0, so one
    pump cannot dominate the blended score.
    """
    if len(s) <= 1:
        return pd.Series(0.5, index=s.index)
    return cast("pd.Series", s.rank(pct=True, na_option="keep"))


def _signal_label(score: float) -> str:
    """Map a composite score in [0,1] to a coarse label.

    Score is the average of two percentile ranks, so 0.5 is the median category.
    """
    if pd.isna(score):
        return "neutral"
    if score >= 0.85:
        return "hot"
    if score >= 0.65:
        return "warm"
    return "neutral"


def _prepare(categories: pd.DataFrame, min_market_cap: float) -> pd.DataFrame:
    """Cap-filter and add the ``turnover`` column. Returns a copy (may be empty)."""
    df = categories.copy()
    df = df[df["market_cap"].fillna(0.0) >= min_market_cap]
    if df.empty:
        return df
    mcap = df["market_cap"].where(df["market_cap"] > 0)
    df["turnover"] = df["volume_24h"].fillna(0.0) / mcap
    return df


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
    snapshot. Returns the top ``top_n`` by score with ``turnover``, ``score`` and
    a ``signal`` label (``hot`` >= 0.85, ``warm`` >= 0.65, else ``neutral``).
    Pure function, no network.
    """
    if categories.empty:
        return pd.DataFrame(columns=_OUT_COLS)
    df = _prepare(categories, min_market_cap)
    if df.empty:
        return pd.DataFrame(columns=_OUT_COLS)

    df["score"] = (_rank_pct(df["change_24h_pct"]) + _rank_pct(df["turnover"])) / 2.0
    df = df.sort_values("score", ascending=False, na_position="last")
    df["signal"] = df["score"].map(_signal_label)
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

    df = categories.copy()
    df = df[df["market_cap"].fillna(0.0) >= min_market_cap]
    df = df[df["change_24h_pct"].notna()]
    ranked = df.sort_values("change_24h_pct", ascending=False)
    gainers = cast("pd.DataFrame", ranked.head(n)[out_cols].reset_index(drop=True))
    losers = cast("pd.DataFrame", ranked.tail(n)[out_cols].iloc[::-1].reset_index(drop=True))
    return {"gainers": gainers, "losers": losers}
