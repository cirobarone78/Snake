"""Halving-cycle alignment analysis: where are we vs past cycles? (Fase 5).

Bitcoin's ~4-year halving cycle is the most-cited recurring pattern in crypto.
The user's point is sound: a pattern that repeats is *information*, not noise —
and the right scientific response is to make it **measurable and reproducible**,
neither dismissing nor overselling it.

This module aligns each historical halving cycle to a common clock — "days since
the halving" — so any two cycles can be compared at the *same phase*. It then
reports, per cycle:

- the price at the halving,
- the cycle **peak** (max within ~18 months after) and how many days after the
  halving it occurred,
- the price at an arbitrary phase (e.g. "today's days-since-halving") and the
  drawdown from that cycle's peak,
- the cycle **bottom** (min from the peak to the next halving) and its timing.

Honest caveats baked into the docstrings (CLAUDE.md, VISION #1): there are only
**3-4 completed cycles**, so this is pattern *description*, not a statistically
validated forecast. Three points cannot prove a law. It tells you *where you are
in a recurring structure*, which is genuinely useful context — not what price
does tomorrow.

Pure functions over a price Series; no network, unit-testable offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pandas as pd

# Bitcoin halving dates (UTC). Past = realised facts; the last may be the
# protocol-scheduled estimate. Kept here (not imported) so the analysis is
# self-contained and matches src.features.cycles.HALVING_DATES.
HALVING_DATES: list[pd.Timestamp] = [
    cast("pd.Timestamp", pd.Timestamp("2012-11-28", tz="UTC")),
    cast("pd.Timestamp", pd.Timestamp("2016-07-09", tz="UTC")),
    cast("pd.Timestamp", pd.Timestamp("2020-05-11", tz="UTC")),
    cast("pd.Timestamp", pd.Timestamp("2024-04-20", tz="UTC")),
]

# Window (days after halving) within which the cycle top historically forms.
PEAK_WINDOW_DAYS = 550
# Upper bound (days after halving) to search for the cycle bottom.
CYCLE_END_DAYS = 1400


@dataclass(frozen=True)
class CycleStats:
    """One halving cycle, aligned to its own 'days since halving' clock."""

    halving_date: pd.Timestamp
    price_at_halving: float
    peak_price: float
    peak_days_after: int  # days from halving to the cycle peak
    bottom_price: float
    bottom_days_after: int  # days from halving to the cycle bottom
    # state at a chosen phase (e.g. today's days-since-halving):
    phase_days: int
    price_at_phase: float | None
    drawdown_from_peak_pct: float | None  # at phase_days, vs this cycle's peak


def _price_on_or_before(close: pd.Series, when: pd.Timestamp) -> float | None:
    sub = cast("pd.Series", close[close.index <= when])
    return float(sub.iloc[-1]) if len(sub) else None


def analyse_cycle(
    close: pd.Series,
    halving_date: pd.Timestamp,
    phase_days: int,
    *,
    peak_window_days: int = PEAK_WINDOW_DAYS,
    cycle_end_days: int = CYCLE_END_DAYS,
) -> CycleStats | None:
    """Compute aligned stats for one cycle, or ``None`` if no data after halving.

    ``phase_days`` is the point on the days-since-halving clock to report (use
    "today's days since the last halving" to compare every past cycle to *now*).
    """
    close = cast("pd.Series", close.sort_index())
    at_halving = cast("pd.Series", close[close.index >= halving_date]).head(1)
    if at_halving.empty:
        return None
    price_at_halving = float(at_halving.iloc[0])

    # peak: max within peak_window_days after the halving
    peak_seg = cast(
        "pd.Series",
        close[
            (close.index >= halving_date)
            & (close.index <= halving_date + pd.Timedelta(days=peak_window_days))
        ],
    )
    if peak_seg.empty:
        return None
    peak_price = float(peak_seg.max())
    peak_date = cast("pd.Timestamp", peak_seg.idxmax())
    peak_days_after = int((peak_date - halving_date).days)

    # bottom: min from peak to cycle_end_days after halving (may be ongoing)
    bot_seg = cast(
        "pd.Series",
        close[
            (close.index >= peak_date)
            & (close.index <= halving_date + pd.Timedelta(days=cycle_end_days))
        ],
    )
    bottom_price = float(bot_seg.min()) if len(bot_seg) else peak_price
    bottom_date = cast("pd.Timestamp", bot_seg.idxmin()) if len(bot_seg) else peak_date
    bottom_days_after = int((bottom_date - halving_date).days)

    # state at the chosen phase
    phase_date = cast("pd.Timestamp", halving_date + pd.Timedelta(days=phase_days))
    price_at_phase = _price_on_or_before(close, phase_date)
    drawdown = (price_at_phase / peak_price - 1.0) * 100.0 if price_at_phase is not None else None

    return CycleStats(
        halving_date=halving_date,
        price_at_halving=price_at_halving,
        peak_price=peak_price,
        peak_days_after=peak_days_after,
        bottom_price=bottom_price,
        bottom_days_after=bottom_days_after,
        phase_days=phase_days,
        price_at_phase=price_at_phase,
        drawdown_from_peak_pct=drawdown,
    )


def days_since_last_halving(today: pd.Timestamp, halvings: list[pd.Timestamp] | None = None) -> int:
    """Days from the most recent halving on/before ``today`` (the current phase)."""
    hs = sorted(halvings or HALVING_DATES)
    past = [h for h in hs if h <= today]
    if not past:
        raise ValueError("today is before the first known halving")
    return int((today - past[-1]).days)


def compare_cycles(
    close: pd.Series,
    today: pd.Timestamp,
    halvings: list[pd.Timestamp] | None = None,
) -> list[CycleStats]:
    """Analyse every halving cycle at the *current* phase (today's days-since).

    Returns one ``CycleStats`` per halving that has data, all evaluated at the
    same ``phase_days`` = today's days since the last halving — so past cycles
    are directly comparable to where we are now.
    """
    hs = sorted(halvings or HALVING_DATES)
    phase = days_since_last_halving(today, hs)
    out: list[CycleStats] = []
    for h in hs:
        stats = analyse_cycle(close, h, phase)
        if stats is not None:
            out.append(stats)
    return out
