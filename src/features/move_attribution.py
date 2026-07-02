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
    severity: str = "major"  # "major" | "notable" (lower-confidence tier)
    candidate_events: list[dict[str, object]] = field(default_factory=list)


def _f(value: object) -> float:
    """Cast a (stub-ambiguous) pandas scalar to float."""
    return float(cast("float", value))


def detect_abnormal_moves(
    close: pd.Series,
    vol_window: int = 30,
    z_threshold: float = 2.5,
    return_floor_pct: float | None = None,
    notable_z: float | None = None,
) -> pd.DataFrame:
    """Flag days whose daily return is an outlier — by z-score OR absolute size.

    The z-score at day ``t`` uses the trailing ``vol_window`` returns **ending at
    ``t-1``** (shifted), so the move's own day does not inflate its baseline — no
    look-ahead into the abnormality test.

    A z-only trigger self-blinds in sustained high-volatility regimes (volatility
    clustering inflates the rolling std, so a -3% day in a bear market scores as
    "normal"). Two optional triggers fix that:

    - ``return_floor_pct``: also flag any day with ``|return| >=`` this many
      percent regardless of z (severity ``major``). Regime-robust catch-all.
    - ``notable_z``: also flag days with ``notable_z <= |z| < z_threshold`` as
      severity ``notable`` — a lower-confidence tier so consumers can always show
      the most recent noteworthy action, ranked, instead of all-or-nothing.

    Returns a frame indexed by date with ``return_pct``, ``zscore`` and
    ``severity`` for the flagged days only. Days without a defined z (warm-up)
    are never flagged, keeping the abnormality test honest.
    """
    if notable_z is not None and notable_z >= z_threshold:
        raise ValueError("notable_z must be below z_threshold")
    ret = cast("pd.Series", cast("pd.Series", close.sort_index()).pct_change())
    mean = cast("pd.Series", ret.rolling(vol_window).mean()).shift(1)
    std = cast("pd.Series", ret.rolling(vol_window).std(ddof=0)).shift(1)
    z = (ret - mean) / std.where(std > 0)

    abs_z = z.abs()
    major = abs_z >= z_threshold
    if return_floor_pct is not None:
        major = major | ((ret.abs() * 100.0) >= return_floor_pct)
    notable = (
        (abs_z >= notable_z) & ~major if notable_z is not None else pd.Series(False, index=z.index)
    )
    flagged_mask = cast("pd.Series", (major | notable) & z.notna())

    idx = z.index[flagged_mask]
    out = pd.DataFrame(
        {
            "return_pct": (ret.reindex(idx) * 100.0).to_numpy(),
            "zscore": z.reindex(idx).to_numpy(),
            "severity": ["major" if m else "notable" for m in major.reindex(idx)],
        },
        index=idx,
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
    source_weight: float,
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
    return source_weight * (0.6 * recency + 0.4 * sentiment_score)


def associate_events(
    move_date: pd.Timestamp,
    move_return_pct: float,
    news: pd.DataFrame,
    asset_source: str | None = None,
    window_days: int = 3,
    top_k: int = 5,
    market_sources: set[str] | None = None,
    classification: str = "asset-specific",
) -> list[dict[str, object]]:
    """Rank news around ``move_date`` as candidate triggers (most plausible first).

    ``news`` is the history frame (``published`` index, columns ``source, title,
    url, sentiment``). ``asset_source`` (e.g. ``googlenews_btc``) marks which
    source is asset-specific so it is up-weighted. For **market-wide** moves, the
    ``market_sources`` (world / geopolitics / macro feeds) are up-weighted to the
    same level as the asset source: on a day the whole market moved, a Fed or
    geopolitics headline is at least as plausible a catalyst as a coin headline.
    Returns up to ``top_k`` dicts with ``published, source, title, url,
    sentiment, relevance``.
    """
    if news.empty:
        return []
    move_is_up = move_return_pct > 0
    is_market_wide = classification == "market-wide"
    lo = move_date.normalize() - pd.Timedelta(days=window_days)
    hi = move_date.normalize() + pd.Timedelta(days=1)
    window = cast("pd.DataFrame", news[(news.index >= lo) & (news.index < hi)])
    rows: list[dict[str, object]] = []
    for published, r in window.iterrows():
        source = str(r["source"])
        if (asset_source is not None and source == asset_source) or (is_market_wide and market_sources is not None and source in market_sources):
            source_w = 1.0
        else:
            source_w = 0.6
        rel = _relevance(
            cast("pd.Timestamp", published),
            move_date,
            _f(r["sentiment"]),
            move_is_up,
            source_w,
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
    market_threshold_pct: float = 3.0,
    return_floor_pct: float | None = None,
    notable_z: float | None = None,
    market_sources: set[str] | None = None,
) -> list[AbnormalMove]:
    """End-to-end: detect abnormal moves and attach classification + candidate news.

    ``market_close`` is an optional market reference series (e.g. BTC for crypto,
    the S&P 500 for equities) used to tell market-wide moves from asset-specific
    ones. ``market_threshold_pct`` is the size a market-reference day must reach to
    count as "the whole market moved" — ~3% fits crypto, ~1% fits equities.
    ``return_floor_pct`` / ``notable_z`` extend the trigger (see
    ``detect_abnormal_moves``); ``market_sources`` are the world/macro feeds
    up-weighted on market-wide days (see ``associate_events``). Returns one
    ``AbnormalMove`` per flagged day, newest first.
    """
    flagged = detect_abnormal_moves(
        close,
        vol_window=vol_window,
        z_threshold=z_threshold,
        return_floor_pct=return_floor_pct,
        notable_z=notable_z,
    )
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
        classification = classify_move(
            _f(row["return_pct"]), mkt_pct, market_threshold_pct=market_threshold_pct
        )
        events = associate_events(
            d,
            _f(row["return_pct"]),
            news,
            asset_source,
            window_days,
            top_k,
            market_sources=market_sources,
            classification=classification,
        )
        moves.append(
            AbnormalMove(
                date=d,
                return_pct=_f(row["return_pct"]),
                zscore=_f(row["zscore"]),
                market_return_pct=mkt_pct,
                classification=classification,
                severity=str(row["severity"]),
                candidate_events=events,
            )
        )
    moves.sort(key=lambda m: m.date, reverse=True)
    return moves


def market_pulse(close: pd.Series, vol_window: int = 30, recent_days: int = 10) -> dict[str, object]:
    """Today's picture for a market benchmark: last return, z, recent max |z|.

    Feeds the dashboard "polso del mercato": when no move crosses the event
    thresholds for days, this is what turns silence into information ("calm
    market, max |z| over the last N days = X") instead of looking like a stale
    pipeline. Same causal z construction as ``detect_abnormal_moves``.
    """
    sorted_close = cast("pd.Series", close.sort_index())
    ret = cast("pd.Series", sorted_close.pct_change())
    mean = cast("pd.Series", ret.rolling(vol_window).mean()).shift(1)
    std = cast("pd.Series", ret.rolling(vol_window).std(ddof=0)).shift(1)
    z = (ret - mean) / std.where(std > 0)
    last_ret = ret.iloc[-1] if len(ret) else float("nan")
    last_z = z.iloc[-1] if len(z) else float("nan")
    recent_max = z.iloc[-recent_days:].abs().max() if len(z) else float("nan")
    last_ts = cast("pd.Timestamp", sorted_close.index[-1]) if len(sorted_close) else None
    return {
        "date": str(last_ts.date()) if last_ts is not None else None,
        "return_pct": round(float(last_ret) * 100.0, 2) if pd.notna(last_ret) else None,
        "zscore": round(float(last_z), 2) if pd.notna(last_z) else None,
        "max_abs_z_recent": round(float(recent_max), 2) if pd.notna(recent_max) else None,
        "recent_days": recent_days,
    }
