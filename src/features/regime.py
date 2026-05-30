"""Market-regime classification and regime-aware metric decomposition (Fase 2).

The baseline backtest (notebook 04) produced a result that demands a closer
look: momentum beats buy-and-hold on BTC/ETH *not* by predicting direction
(accuracy ~50%) but by sitting flat during crashes — a **defensive**, not a
predictive, edge. Full-sample metrics hide this. Fase 1 already flagged that
regimes exist and are unstable (rolling correlations std 0.12-0.17). So a
full-OOS Sharpe is an average over structurally different worlds.

This module splits a return stream by **market regime** (bull / bear) and
reports metrics within each, to answer: *where* does a strategy earn or lose?

Causality (no look-ahead, CLAUDE.md non-negotiable): the regime label at time
``t`` uses only prices up to ``t``. We classify on the position of price
relative to its own trailing moving average — a backward-looking filter.
A point is **bull** when ``close[t] >= SMA(close, window)[t]``, else **bear**.
The leading ``window-1`` points (SMA undefined) are labelled ``unknown`` and
excluded from per-regime metrics rather than guessed.

This is intentionally a *simple, transparent* regime proxy, not a
regime-switching model (HMM/Markov is a Fase 5 candidate, ADR/ROADMAP). It is
enough to decompose baseline performance honestly; it does not claim to detect
turning points in real time.

Asset-class-agnostic (ADR-014): the window is in observations.
"""

from __future__ import annotations

from enum import StrEnum
from typing import cast

import pandas as pd

from src.backtest.metrics import DEFAULT_PERIODS_PER_YEAR, PerformanceSummary, summarize


class Regime(StrEnum):
    """Coarse market regime, classified causally from trailing price action."""

    BULL = "bull"
    BEAR = "bear"
    UNKNOWN = "unknown"  # SMA not yet defined (warm-up); excluded from metrics


def classify_regime(prices: pd.Series, window: int = 200) -> pd.Series:
    """Label each timestamp bull/bear by price vs its trailing SMA (causal).

    ``bull`` when ``close[t] >= SMA(window)[t]``, else ``bear``. The SMA at
    ``t`` averages the last ``window`` closes up to and including ``t`` — it
    never uses future prices. Warm-up points (SMA NaN) are ``unknown``.

    The default window (200) is the conventional long-term trend filter; it is
    a transparent proxy, deliberately not tuned on the data.
    """
    if window <= 0:
        raise ValueError("window must be positive")
    p = prices.dropna()
    sma = cast("pd.Series", p.rolling(window).mean())
    labels = pd.Series(Regime.UNKNOWN.value, index=p.index, name="regime")
    defined = sma.notna()
    is_bull = defined & (p >= sma)
    is_bear = defined & (p < sma)
    labels = labels.mask(is_bull, Regime.BULL.value)
    labels = labels.mask(is_bear, Regime.BEAR.value)
    return cast("pd.Series", labels)


def summarize_by_regime(
    returns: pd.Series,
    regime: pd.Series,
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR,
) -> dict[str, PerformanceSummary]:
    """Compute the full metric set within each regime, plus the full sample.

    ``regime`` is aligned to ``returns`` on their common index. Only ``bull``
    and ``bear`` segments are reported per-regime (``unknown`` warm-up points
    are dropped). The ``'full'`` key holds the undecomposed summary, so callers
    can see at a glance how much the average hides.

    The regime label must be the one **in effect for that return's period**.
    Since ``classify_regime`` is causal (uses prices up to ``t``) and a return
    at ``t`` spans ``t-1 -> t``, aligning on the same index attributes each
    return to the regime knowable at its close — no look-ahead.
    """
    r_aligned, g = returns.align(regime, join="inner")
    r = cast("pd.Series", r_aligned.dropna())
    g = g.reindex(r.index)

    out: dict[str, PerformanceSummary] = {
        "full": summarize(r, periods_per_year=periods_per_year)
    }
    for label in (Regime.BULL.value, Regime.BEAR.value):
        seg = cast("pd.Series", r[g == label])
        if len(seg) > 0:
            out[label] = summarize(seg, periods_per_year=periods_per_year)
    return out


def regime_fractions(regime: pd.Series) -> dict[str, float]:
    """Fraction of (known) periods spent in each regime.

    ``unknown`` warm-up points are excluded from the denominator so the bull
    and bear fractions sum to 1 over the classified range.
    """
    known = regime[regime != Regime.UNKNOWN.value]
    n = len(known)
    if n == 0:
        return {Regime.BULL.value: float("nan"), Regime.BEAR.value: float("nan")}
    return {
        Regime.BULL.value: float((known == Regime.BULL.value).sum()) / n,
        Regime.BEAR.value: float((known == Regime.BEAR.value).sum()) / n,
    }
