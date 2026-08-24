"""DCA advisor: which satellite to buy with this month's small slice.

The user's plan: a fixed monthly budget split into a **core** (BTC, ETH) whose
allocation never changes, plus a small **satellite sleeve** (SOL / LINK / POL)
where a single asset is picked each month. This module ranks the sleeve.

**What this is not.** It is not a forecast of which asset will rise. Fase 5 of
this project found no directional daily edge on this universe, and the rotation
study (``conditional_outcomes``) found that *chasing the strongest* momentum is
if anything mildly harmful at a 63-day horizon. So the ranking here deliberately
contains **no bet on direction**. It answers a narrower, mechanical question:

    Given a target allocation and a fixed budget, which purchase moves the
    portfolio closest to its own plan, at the best relative entry?

Two components, both computable from prices alone and both causal:

1. **Weight gap** — how far each asset sits *below* its target share of the
   sleeve, in percentage points. This is plain rebalancing: after a leg runs up
   it is overweight, so the next contribution goes elsewhere. Deterministic, no
   prediction involved.
2. **Relative discount** — where the price sits inside its own trailing range
   (0 = at the ``lookback`` low, 1 = at the high), ranked across the sleeve.
   Buying the laggard is mean-reversion, and is the *opposite* of the momentum
   chase the conditional-outcome study rejected.

The two are blended on **cross-sectional rank percentiles** (the outlier-robust
trick from ``screener.py``): one asset down 80% cannot dominate the blend, it
just takes the top rank.

Honesty guards (CLAUDE.md):
- The output is a *ranking under a stated rule*, never "this will go up".
- The edge such a rule can produce is a **cost-basis** effect, not alpha, and it
  is small. ``dca_backtest`` measures it against the naive alternatives and
  reports the answer whatever it is.
- With ``holdings_units`` unknown the weight-gap term is undefined; the module
  degrades to the discount term alone rather than inventing a position.

Pure functions over pandas, asset-class-agnostic (ADR-014): the sleeve is just a
panel of close-price columns.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd

# Trailing window for the "where in its own range" discount. ~6 months: long
# enough to span a drawdown, short enough that a 2021 high does not define
# "cheap" forever.
DEFAULT_LOOKBACK: int = 180

# Blend of the two components, and why the default is 1.0 (rebalancing only).
#
# ``dca_backtest`` ran both terms over 2020-04 -> 2026-08 with real monthly cash
# flows. The discount term looked excellent in-sample (96th percentile against
# 200 random-picking seeds) and then came **last** in the out-of-sample half —
# the classic in-sample mirage, so it does not get to drive the default. The
# weight-gap term needs no such validation: it is arithmetic, not a bet. It is
# therefore the whole default score, and the discount only ever breaks an exact
# tie (see ``advise``). Callers who want the tilt can pass a lower gap_weight,
# knowing it is unvalidated.
DEFAULT_GAP_WEIGHT: float = 1.0

_OUT_COLS = [
    "symbol", "price", "weight_now", "weight_target", "gap_pp",
    "discount", "gap_rank", "discount_rank", "score", "rank", "reason",
]


def _rank_pct(values: np.ndarray) -> np.ndarray:
    """Cross-sectional percentile rank in ``[0, 1]`` (outlier-robust).

    Same construction as ``screener._rank_pct``: an extreme value only ever
    reaches 1.0, so a single collapsed asset cannot swamp the blended score.
    NaNs rank lowest. A single element (or all-equal input) -> 0.5 (neutral).
    """
    n = len(values)
    if n <= 1:
        return np.full(n, 0.5)
    finite = np.where(np.isnan(values), -np.inf, values)
    if np.all(finite == finite[0]):
        return np.full(n, 0.5)
    order = np.argsort(np.argsort(finite, kind="stable"), kind="stable").astype("float64")
    return order / (n - 1)


def align_timestamp(index: pd.Index, when: pd.Timestamp | str) -> pd.Timestamp:
    """``when`` as a Timestamp carrying ``index``'s timezone awareness.

    Comparing a tz-naive bound against a tz-aware index raises in pandas, and a
    date bound is exactly the kind of argument a caller passes as a bare string.
    Localises (or strips) to match rather than making the caller care.
    """
    ts = cast("pd.Timestamp", pd.Timestamp(when))
    tz = getattr(index, "tz", None)
    if tz is not None and ts.tzinfo is None:
        return cast("pd.Timestamp", ts.tz_localize(tz))
    if tz is None and ts.tzinfo is not None:
        return cast("pd.Timestamp", ts.tz_localize(None))
    return ts


def _as_of_slice(panel_close: pd.DataFrame, as_of: pd.Timestamp | str | None) -> pd.DataFrame:
    """Panel truncated at ``as_of`` inclusive (no look-ahead), sorted by date."""
    panel = cast("pd.DataFrame", panel_close.sort_index())
    if as_of is None:
        return panel
    cutoff = align_timestamp(panel.index, as_of)
    return cast("pd.DataFrame", panel.loc[panel.index <= cutoff])


def relative_discount(
    panel_close: pd.DataFrame,
    lookback: int = DEFAULT_LOOKBACK,
    as_of: pd.Timestamp | str | None = None,
) -> pd.Series:
    """Position of each asset inside its own trailing range, in ``[0, 1]``.

    ``0`` = trading at the ``lookback``-day low, ``1`` = at the high. Uses only
    bars up to ``as_of`` (causal). Assets with no data in the window are NaN —
    never filled with a neutral value, so a dead feed stays visible as missing.
    """
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    panel = _as_of_slice(panel_close, as_of)
    if panel.empty:
        return pd.Series(dtype="float64")
    window = cast("pd.DataFrame", panel.tail(lookback))
    last = window.ffill().iloc[-1]
    low = window.min()
    high = window.max()
    span = high - low
    # A flat series (span 0) has no meaningful position in its range -> 0.5.
    pos = (last - low) / span.where(span > 0)
    return cast("pd.Series", pos.where(span > 0, 0.5).astype("float64"))


def portfolio_weights(
    panel_close: pd.DataFrame,
    holdings_units: dict[str, float],
    as_of: pd.Timestamp | str | None = None,
) -> pd.Series:
    """Current value share of each sleeve asset, summing to 1 (0 if empty).

    ``holdings_units`` is units held (coins, not euro). Assets absent from the
    mapping count as zero units — the natural reading of "not bought yet".
    """
    panel = _as_of_slice(panel_close, as_of)
    if panel.empty:
        return pd.Series(0.0, index=panel_close.columns, dtype="float64")
    last = panel.ffill().iloc[-1]
    units = pd.Series(
        {c: float(holdings_units.get(c, 0.0)) for c in panel.columns}, dtype="float64"
    )
    value = cast("pd.Series", units * last)
    total = float(value.sum())
    if not np.isfinite(total) or total <= 0:
        return pd.Series(0.0, index=panel.columns, dtype="float64")
    return cast("pd.Series", value / total)


def _reason(gap_pp: float | None, discount: float | None, is_pick: bool) -> str:
    """Machine-readable reason code (the Italian wording lives in the report)."""
    if not is_pick:
        return "not_selected"
    if gap_pp is not None and gap_pp >= 5.0:
        return "underweight_vs_target"
    if discount is not None and discount <= 0.35:
        return "cheapest_in_range"
    if gap_pp is not None and gap_pp > 0:
        return "mildly_underweight"
    return "best_blend"


def advise(
    panel_close: pd.DataFrame,
    target_weights: dict[str, float] | None = None,
    holdings_units: dict[str, float] | None = None,
    lookback: int = DEFAULT_LOOKBACK,
    gap_weight: float = DEFAULT_GAP_WEIGHT,
    as_of: pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Rank the sleeve assets for this contribution; row 0 is the pick.

    ``target_weights`` defaults to equal weight across the sleeve. When
    ``holdings_units`` is ``None`` the weight-gap term is undefined and the
    ranking falls back to the discount term alone (``gap_pp``/``weight_now``
    reported as NaN, never invented).

    Output columns: ``symbol, price, weight_now, weight_target, gap_pp,
    discount, gap_rank, discount_rank, score, rank, reason``. Index 1-based
    by rank, best first.
    """
    if not 0.0 <= gap_weight <= 1.0:
        raise ValueError("gap_weight must be in [0, 1]")
    symbols = list(panel_close.columns)
    if not symbols:
        return pd.DataFrame(columns=_OUT_COLS)

    panel = _as_of_slice(panel_close, as_of)
    if panel.empty:
        return pd.DataFrame(columns=_OUT_COLS)
    price = panel.ffill().iloc[-1]

    if target_weights:
        total_target = sum(max(0.0, float(v)) for v in target_weights.values())
        targets = pd.Series(
            {s: max(0.0, float(target_weights.get(s, 0.0))) for s in symbols}, dtype="float64"
        )
        targets = targets / total_target if total_target > 0 else targets
    else:
        targets = pd.Series(1.0 / len(symbols), index=symbols, dtype="float64")

    discount = relative_discount(panel_close, lookback=lookback, as_of=as_of).reindex(symbols)
    # Cheap (low position in range) should score high -> invert the rank.
    discount_rank = pd.Series(
        1.0 - _rank_pct(discount.to_numpy(dtype="float64")), index=symbols, dtype="float64"
    )

    if holdings_units is None:
        weight_now = pd.Series(np.nan, index=symbols, dtype="float64")
        gap_pp = pd.Series(np.nan, index=symbols, dtype="float64")
        gap_rank = pd.Series(np.nan, index=symbols, dtype="float64")
        score = discount_rank
    else:
        weight_now = portfolio_weights(panel_close, holdings_units, as_of=as_of).reindex(symbols)
        gap_pp = cast("pd.Series", (targets - weight_now) * 100.0)
        gap_rank = pd.Series(
            _rank_pct(gap_pp.to_numpy(dtype="float64")), index=symbols, dtype="float64"
        )
        score = gap_weight * gap_rank + (1.0 - gap_weight) * discount_rank

    out = pd.DataFrame(
        {
            "symbol": symbols,
            "price": [float(price.get(s, np.nan)) for s in symbols],
            "weight_now": weight_now.to_numpy(),
            "weight_target": targets.to_numpy(),
            "gap_pp": gap_pp.to_numpy(),
            "discount": discount.to_numpy(),
            "gap_rank": gap_rank.to_numpy(),
            "discount_rank": discount_rank.to_numpy(),
            "score": score.to_numpy(),
        }
    )
    # Deterministic order: score desc, then the discount rank as tiebreak, then
    # symbol. A tie never flips between runs (a flipping "pick of the day" would
    # be noise presented as a signal), and when the weight gaps genuinely tie the
    # cheaper leg wins — the one use of an OOS-refuted signal that costs nothing.
    out = out.sort_values(
        ["score", "discount_rank", "symbol"], ascending=[False, False, True], kind="stable"
    )
    out["rank"] = np.arange(1, len(out) + 1)
    out["reason"] = [
        _reason(
            None if pd.isna(r["gap_pp"]) else float(r["gap_pp"]),
            None if pd.isna(r["discount"]) else float(r["discount"]),
            int(r["rank"]) == 1,
        )
        for r in out.to_dict("records")
    ]
    out.index = pd.RangeIndex(start=1, stop=len(out) + 1, name="rank")
    return cast("pd.DataFrame", out[_OUT_COLS])


def pick(
    panel_close: pd.DataFrame,
    target_weights: dict[str, float] | None = None,
    holdings_units: dict[str, float] | None = None,
    lookback: int = DEFAULT_LOOKBACK,
    gap_weight: float = DEFAULT_GAP_WEIGHT,
    as_of: pd.Timestamp | str | None = None,
) -> str | None:
    """Top-ranked symbol from :func:`advise`, or ``None`` on an empty panel."""
    ranked = advise(
        panel_close,
        target_weights=target_weights,
        holdings_units=holdings_units,
        lookback=lookback,
        gap_weight=gap_weight,
        as_of=as_of,
    )
    return None if ranked.empty else str(ranked.iloc[0]["symbol"])
