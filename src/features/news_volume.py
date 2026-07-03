"""News coverage volume as an event signal (Fase 7 backlog D2, ADR-028 follow-up).

The *amount* of coverage often marks an event more reliably than its sentiment:
a headline-count spike says "something happened here" even when the wording is
neutral or mixed. This module measures, per news source, the daily headline
count against its own trailing baseline and flags abnormal coverage days —
complementing (not replacing) the sentiment-based attribution.

Same causality convention as ``move_attribution``: the baseline at day ``t``
uses counts up to ``t-1`` (shifted), so a spike day never inflates its own
baseline. Days with no headlines count as zero — missing calendar days are
filled in before computing the baseline, otherwise thin feeds would bias the
mean upward. Pure functions over DataFrames; unit-testable offline.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

import pandas as pd

from src.features.move_attribution import AbnormalMove


def daily_news_volume(news: pd.DataFrame, sources: set[str] | str) -> pd.Series:
    """Headline count per UTC day for one source (or a set of sources).

    ``news`` is the history frame (``published`` tz-aware index, ``source``
    column). Calendar days with no headlines are filled with 0 across the
    observed span, so downstream baselines see the real cadence of the feed.
    Returns an empty Series when nothing matches.
    """
    wanted = [sources] if isinstance(sources, str) else sorted(sources)
    if news.empty:
        return pd.Series(dtype=float, name="news_count")
    mask = cast("pd.Series", news["source"].isin(wanted))
    subset = cast("pd.DataFrame", news[mask])
    if subset.empty:
        return pd.Series(dtype=float, name="news_count")
    # .normalize() is a delegated method the type stubs don't surface.
    days = cast("pd.DatetimeIndex", cast("Any", subset.index).normalize())
    counts = cast("pd.Series", pd.Series(1.0, index=days).groupby(level=0).sum())
    counts_idx = cast("pd.DatetimeIndex", counts.index)
    full = pd.date_range(counts_idx.min(), counts_idx.max(), freq="D", tz=counts_idx.tz)
    return cast("pd.Series", counts.reindex(full, fill_value=0.0)).rename("news_count")


def volume_zscore(counts: pd.Series, window: int = 30) -> pd.Series:
    """Causal z-score of daily counts vs their trailing baseline (shifted).

    Unlike price returns, headline counts are Poisson-like and can have a
    *perfectly steady* baseline (std = 0) — on which a burst is the most
    obvious spike imaginable, yet a plain z would be undefined. The scale is
    therefore ``max(sample std, sqrt(mean), 1)``: the Poisson noise floor for
    a feed of that size, never below one headline. Warm-up days (no baseline
    yet) stay NaN.
    """
    c = cast("pd.Series", counts.sort_index())
    mean = cast("pd.Series", c.rolling(window).mean()).shift(1)
    std = cast("pd.Series", c.rolling(window).std(ddof=0)).shift(1)
    poisson_floor = cast("pd.Series", cast("pd.Series", mean.clip(lower=1.0)) ** 0.5)
    # Elementwise max(std, floor); NaN baseline propagates (warm-up undefined).
    scale = cast("pd.Series", std.where(std >= poisson_floor, poisson_floor))
    return cast("pd.Series", (c - mean) / scale)


def detect_volume_spikes(
    counts: pd.Series,
    window: int = 30,
    z_threshold: float = 2.5,
    min_count: int = 5,
) -> pd.DataFrame:
    """Days whose headline count is abnormally high vs the trailing baseline.

    ``min_count`` is an absolute floor: on a thin feed, 3 headlines against a
    0.4/day baseline is a huge z but no real "spike" — we require a minimum
    amount of coverage before calling it one. Returns a frame indexed by date
    with ``count`` and ``zscore`` for spike days only.
    """
    if min_count < 0:
        raise ValueError("min_count must be non-negative")
    z = volume_zscore(counts, window=window)
    mask = cast("pd.Series", (z >= z_threshold) & (counts >= min_count) & z.notna())
    idx = cast("Any", z.index[mask])
    out = pd.DataFrame(
        {
            "count": counts.reindex(idx).to_numpy(),
            "zscore": z.reindex(idx).to_numpy(),
        },
        index=idx,
    )
    out.index.name = "date"
    return out


def annotate_moves_with_coverage(
    moves: list[AbnormalMove],
    counts: pd.Series,
    window: int = 30,
    z_threshold: float = 2.5,
    min_count: int = 5,
) -> list[AbnormalMove]:
    """Attach same-day coverage stats to each move.

    For every move, records ``coverage = {count, zscore, spike}`` for the move's
    day. A price move accompanied by a coverage spike is a stronger "something
    happened" marker than either signal alone. Moves keep their identity —
    frozen dataclasses are copied via ``replace`` with the extra annotation
    stored on the ``coverage`` field.
    """
    if not moves:
        return moves
    z = volume_zscore(counts, window=window)
    out: list[AbnormalMove] = []
    for m in moves:
        day = m.date.normalize()
        count = float(cast("float", counts.loc[day])) if day in counts.index else 0.0
        zval = cast("float", z.loc[day]) if day in z.index else float("nan")
        zf = float(zval) if pd.notna(zval) else None
        coverage: dict[str, object] = {
            "count": int(count),
            "zscore": round(zf, 2) if zf is not None else None,
            "spike": bool(zf is not None and zf >= z_threshold and count >= min_count),
        }
        out.append(replace(m, coverage=coverage))
    return out
