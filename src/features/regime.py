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


class VolRegime(StrEnum):
    """Coarse volatility regime, classified causally from trailing realised vol."""

    HIGH = "high_vol"
    LOW = "low_vol"
    UNKNOWN = "unknown"  # vol or its trailing baseline not yet defined (warm-up)


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


def classify_vol_regime(
    returns: pd.Series, vol_window: int = 30, baseline_window: int = 180
) -> pd.Series:
    """Label each timestamp high/low volatility, causally (no look-ahead).

    Trailing realised volatility ``vol[t] = std(returns[t-vol_window+1 : t])`` is
    compared to its own trailing **median** over ``baseline_window`` (shifted by
    one so day ``t`` is not in its own baseline). ``high_vol`` when current vol
    exceeds the baseline median, else ``low_vol``. A relative (self-referential)
    threshold keeps it asset-class-agnostic — BTC and an equity index have very
    different absolute vol, but each is "high" relative to its own recent norm.

    Warm-up points (vol or baseline undefined) are ``unknown`` and excluded
    downstream rather than guessed.
    """
    if vol_window <= 1:
        raise ValueError("vol_window must be > 1")
    if baseline_window <= 0:
        raise ValueError("baseline_window must be positive")
    r = returns.dropna()
    vol = cast("pd.Series", r.rolling(vol_window).std(ddof=0))
    # baseline uses vol values strictly before t (shift 1) to avoid self-inclusion
    baseline = cast("pd.Series", vol.rolling(baseline_window).median()).shift(1)
    labels = pd.Series(VolRegime.UNKNOWN.value, index=r.index, name="vol_regime")
    defined = vol.notna() & baseline.notna()
    is_high = defined & (vol > baseline)
    is_low = defined & (vol <= baseline)
    labels = labels.mask(is_high, VolRegime.HIGH.value)
    labels = labels.mask(is_low, VolRegime.LOW.value)
    return cast("pd.Series", labels)


def combine_regimes(trend: pd.Series, vol: pd.Series) -> pd.Series:
    """Cross trend (bull/bear) and vol (high/low) into a 4-state regime label.

    Labels like ``bull_low_vol`` / ``bear_high_vol``. Any timestamp where either
    component is ``unknown`` (warm-up) becomes ``unknown``. Aligned on the common
    index. Useful to test whether the *combination* (e.g. bear+high-vol = crash)
    carries more conditioning information than either axis alone.
    """
    t_aligned, v_aligned = trend.align(vol, join="inner")
    out = pd.Series("unknown", index=t_aligned.index, name="regime_4state")
    known = (t_aligned != Regime.UNKNOWN.value) & (v_aligned != VolRegime.UNKNOWN.value)
    combined = t_aligned.astype(str) + "_" + v_aligned.astype(str)
    out = out.mask(known, combined)
    return cast("pd.Series", out)


def summarize_by_regime(
    returns: pd.Series,
    regime: pd.Series,
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR,
) -> dict[str, PerformanceSummary]:
    """Compute the full metric set within each regime, plus the full sample.

    ``regime`` is aligned to ``returns`` on their common index. Every distinct
    label except ``unknown`` (warm-up) gets its own summary; the ``'full'`` key
    holds the undecomposed summary, so callers can see at a glance how much the
    average hides. Works for any label scheme — trend (bull/bear), vol
    (high_vol/low_vol), or the 4-state combination.

    The regime label must be the one **in effect for that return's period**.
    Since the classifiers are causal (use data up to ``t``) and a return at
    ``t`` spans ``t-1 -> t``, aligning on the same index attributes each return
    to the regime knowable at its close — no look-ahead.
    """
    r_aligned, g = returns.align(regime, join="inner")
    r = cast("pd.Series", r_aligned.dropna())
    g = g.reindex(r.index)

    out: dict[str, PerformanceSummary] = {"full": summarize(r, periods_per_year=periods_per_year)}
    labels = [str(x) for x in pd.unique(g) if str(x) != "unknown"]
    for label in sorted(labels):
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
