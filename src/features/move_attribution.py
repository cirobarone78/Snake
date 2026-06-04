"""Associate abrupt price moves with their candidate triggering events (Fase 3).

The user's intuition is largely right: a sharp one-day move usually has an
identifiable catalyst. This module, given an asset's price history and the news
history we already collect, does three honest things:

1. **Detect** the abnormal moves — days whose return is an outlier vs the asset's
   own recent volatility (a z-score on returns), so "abrupt" is measured, not
   eyeballed.
2. **Classify** each move as *market-wide* or *asset-specific* by comparing it to
   a market reference (e.g. BTC for crypto): if the whole market moved the same
   way that day, the trigger is macro/market, not the single coin.
3. **Associate** the news published in a window around the move, ranked by
   relevance (recency to the move + sentiment magnitude aligned with the move's
   direction). Asset-named news is weighted above generic market news.

Honesty guardrails baked in (CLAUDE.md, VISION #1): this returns **candidate**
events ranked by plausibility — *association is not causation*. Some crashes are
driven by leverage/liquidations with no public headline; the tool says "here are
the likely catalysts", never "here is the proven cause". Pure functions over
DataFrames; unit-testable offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import pandas as pd


@dataclass(frozen=True)
class AbnormalMove:
    """One day where an asset moved abnormally vs its own recent volatility."""

    date: pd.Timestamp
    return_pct: float
    zscore: float  # how many std devs from the trailing mean return
    market_return_pct: float | None  # same-day move of the market reference
    classification: str  # "market-wide" | "asset-specific" | "unknown"
    candidate_events: list[dict[str, object]] = field(default_factory=list)


def _f(value: object) -> float:
    """Cast a (stub-ambiguous) pandas scalar to float."""
    return float(cast("float", value))


def detect_abnormal_moves(
    close: pd.Series,
    vol_window: int = 30,
    z_threshold: float = 2.5,
) -> pd.DataFrame:
    """Flag days whose daily return is an outlier vs trailing volatility.

    The z-score at day ``t`` uses the trailing ``vol_window`` returns **ending at
    ``t-1``** (shifted), so the move's own day does not inflate its baseline — no
    look-ahead into the abnormality test. Returns a frame indexed by date with
    ``return_pct`` and ``zscore`` for the flagged days only (|z| >= threshold).
    """
    ret = cast("pd.Series", cast("pd.Series", close.sort_index()).pct_change())
    mean = cast("pd.Series", ret.rolling(vol_window).mean()).shift(1)
    std = cast("pd.Series", ret.rolling(vol_window).std(ddof=0)).shift(1)
    z = (ret - mean) / std.where(std > 0)
    flagged = z[z.abs() >= z_threshold].dropna()
    out = pd.DataFrame(
        {
            "return_pct": (ret.reindex(flagged.index) * 100.0).to_numpy(),
            "zscore": flagged.to_numpy(),
        },
        index=flagged.index,
    )
    out.index.name = "date"
    return out


def classify_move(
    move_return_pct: float,
    market_return_pct: float | None,
    market_threshold_pct: float = 3.0,
    agreement_ratio: float = 0.5,
) -> str:
    """Label a move ``market-wide`` / ``asset-specific`` / ``unknown``.

    If the market reference moved meaningfully *in the same direction* that day
    (>= ``market_threshold_pct`` and at least ``agreement_ratio`` of the asset's
    move), the trigger is market-wide. If the market barely moved, it is
    asset-specific. ``None`` market data -> ``unknown``.
    """
    if market_return_pct is None or pd.isna(market_return_pct):
        return "unknown"
    same_direction = (move_return_pct > 0) == (market_return_pct > 0)
    big_market = abs(market_return_pct) >= market_threshold_pct
    market_explains = abs(market_return_pct) >= abs(move_return_pct) * agreement_ratio
    if same_direction and big_market and market_explains:
        return "market-wide"
    return "asset-specific"


def _relevance(
    published: pd.Timestamp,
    move_date: pd.Timestamp,
    sentiment: float,
    move_is_up: bool,
    is_asset_specific_source: bool,
    window_days: int,
) -> float:
    """Score a news item's plausibility as a trigger for the move (higher=better)."""
    # recency: published within [move-window, move]; closer = higher (1.0 .. 0)
    delta_days = (move_date.normalize() - published.normalize()).days
    if delta_days < 0 or delta_days > window_days:
        return 0.0
    recency = 1.0 - (delta_days / (window_days + 1))
    # sentiment aligned with the move direction (up move + positive news, etc.)
    aligned = sentiment if move_is_up else -sentiment
    sentiment_score = max(aligned, 0.0)  # only count news that "fits" the move
    # asset-named news weighted above generic market news
    source_w = 1.0 if is_asset_specific_source else 0.6
    return source_w * (0.6 * recency + 0.4 * sentiment_score)


def associate_events(
    move_date: pd.Timestamp,
    move_return_pct: float,
    news: pd.DataFrame,
    asset_source: str | None = None,
    window_days: int = 3,
    top_k: int = 5,
) -> list[dict[str, object]]:
    """Rank news around ``move_date`` as candidate triggers (most plausible first).

    ``news`` is the history frame (``published`` index, columns ``source, title,
    url, sentiment``). ``asset_source`` (e.g. ``googlenews_btc``) marks which
    source is asset-specific so it is up-weighted. Returns up to ``top_k`` dicts
    with ``published, source, title, url, sentiment, relevance``.
    """
    if news.empty:
        return []
    move_is_up = move_return_pct > 0
    lo = move_date.normalize() - pd.Timedelta(days=window_days)
    hi = move_date.normalize() + pd.Timedelta(days=1)
    window = cast("pd.DataFrame", news[(news.index >= lo) & (news.index < hi)])
    rows: list[dict[str, object]] = []
    for published, r in window.iterrows():
        source = str(r["source"])
        is_asset = asset_source is not None and source == asset_source
        rel = _relevance(
            cast("pd.Timestamp", published),
            move_date,
            _f(r["sentiment"]),
            move_is_up,
            is_asset,
            window_days,
        )
        if rel <= 0.0:
            continue
        rows.append(
            {
                "published": str(published)[:16],
                "source": source,
                "title": str(r["title"]),
                "url": str(r["url"]),
                "sentiment": round(_f(r["sentiment"]), 3),
                "relevance": round(rel, 3),
            }
        )
    rows.sort(key=lambda d: d["relevance"], reverse=True)  # type: ignore[arg-type,return-value]
    return rows[:top_k]


def attribute_moves(
    close: pd.Series,
    news: pd.DataFrame,
    asset_source: str | None = None,
    market_close: pd.Series | None = None,
    vol_window: int = 30,
    z_threshold: float = 2.5,
    window_days: int = 3,
    top_k: int = 5,
) -> list[AbnormalMove]:
    """End-to-end: detect abnormal moves and attach classification + candidate news.

    ``market_close`` is an optional market reference series (e.g. BTC) used to
    tell market-wide moves from asset-specific ones. Returns one ``AbnormalMove``
    per flagged day, newest first.
    """
    flagged = detect_abnormal_moves(close, vol_window=vol_window, z_threshold=z_threshold)
    market_ret = (
        cast("pd.Series", cast("pd.Series", market_close.sort_index()).pct_change())
        if market_close is not None
        else None
    )

    moves: list[AbnormalMove] = []
    for date, row in flagged.iterrows():
        d = cast("pd.Timestamp", date)
        mkt_pct: float | None = None
        if market_ret is not None and d in market_ret.index:
            val = market_ret.loc[d]
            mkt_pct = float(val) * 100.0 if pd.notna(val) else None
        classification = classify_move(_f(row["return_pct"]), mkt_pct)
        events = associate_events(
            d, _f(row["return_pct"]), news, asset_source, window_days, top_k
        )
        moves.append(
            AbnormalMove(
                date=d,
                return_pct=_f(row["return_pct"]),
                zscore=_f(row["zscore"]),
                market_return_pct=mkt_pct,
                classification=classification,
                candidate_events=events,
            )
        )
    moves.sort(key=lambda m: m.date, reverse=True)
    return moves
