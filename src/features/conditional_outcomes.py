"""Conditional outcome study: "given this rotation state, what happened next?".

This is the **probabilistic layer** the rotation screeners deliberately deferred
(see ``screener.py``): not predicting a single asset, but estimating — from
history — the *distribution of forward returns conditional on a rotation state*.

Rather than wait weeks for live snapshots to accumulate, we reconstruct the state
**point-in-time from years of prices**:

1. **State** at each date = the asset's trailing ``lookback`` momentum, **ranked
   cross-sectionally** within its universe that day, bucketed (weak / mid /
   strong). Cross-sectional ranking uses only that day's data, and momentum uses
   only past prices → no look-ahead in defining the state.
2. **Outcome** = the forward simple return over ``horizon`` days, realised strictly
   *after* the state is known.
3. **Conditioning** = pool all ``(date, asset)`` observations and summarise the
   forward-return distribution per bucket, against the unconditional baseline.

Honesty guards (CLAUDE.md, VISION #1):
- The reported ``n`` counts observations, **not** independent samples: daily
  observations with a multi-day ``horizon`` overlap, so autocorrelation inflates
  the effective sample. Treat bucket differences as *indicative*, not significant,
  until checked on non-overlapping windows / out-of-sample.
- Pooling across assets assumes a shared conditional distribution (a
  simplification, stated, not proven).
- This estimates *probabilities from the past*, never a promise about the future.

Pure functions over pandas; unit-testable offline, asset-class-agnostic (ADR-014:
the universe is just a panel of close-price columns — equity sectors or crypto).
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd

# Default bucket labels, ordered weakest -> strongest momentum.
_DEFAULT_LABELS_3 = ["weak", "mid", "strong"]

_TABLE_COLS = [
    "state", "n", "mean_fwd_pct", "median_fwd_pct",
    "hit_rate", "std_fwd_pct", "p25_fwd_pct", "p75_fwd_pct",
]


def bucket_labels(n_buckets: int) -> list[str]:
    """Ordered weak->strong labels for ``n_buckets`` (3 -> weak/mid/strong)."""
    if n_buckets == 3:
        return list(_DEFAULT_LABELS_3)
    return [f"b{i + 1}" for i in range(n_buckets)]


def forward_return(close: pd.Series, horizon: int) -> pd.Series:
    """Forward simple return over ``horizon`` periods, indexed at the state date.

    ``fwd[t] = close[t + horizon] / close[t] - 1``. The last ``horizon`` points are
    NaN (the future isn't realised yet) — never back-filled.
    """
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    s = cast("pd.Series", close.sort_index()).astype("float64")
    return cast("pd.Series", s.shift(-horizon) / s - 1.0)


def momentum(close: pd.Series, lookback: int) -> pd.Series:
    """Trailing ``lookback`` simple return (causal): ``close[t]/close[t-lookback]-1``."""
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    s = cast("pd.Series", close.sort_index()).astype("float64")
    return cast("pd.Series", s / s.shift(lookback) - 1.0)


def rotation_observations(
    panel_close: pd.DataFrame,
    lookback: int = 21,
    horizon: int = 21,
    n_buckets: int = 3,
) -> pd.DataFrame:
    """Long-form ``(date, symbol, bucket, fwd_ret)`` observations, point-in-time.

    ``panel_close`` is a date-indexed frame of close prices, one column per asset
    in the rotation universe. For each date we rank the assets by trailing
    ``lookback`` momentum into ``n_buckets`` cross-sectional buckets (ties broken
    deterministically), and attach the forward ``horizon`` return. Dates with
    fewer than ``n_buckets`` valid assets are skipped. No look-ahead: the bucket
    uses momentum up to the date, the outcome is realised after it.
    """
    panel = cast("pd.DataFrame", panel_close.sort_index()).astype("float64")
    mom = panel / panel.shift(lookback) - 1.0
    fwd = panel.shift(-horizon) / panel - 1.0
    labels = bucket_labels(n_buckets)

    rows: list[dict[str, object]] = []
    for date in panel.index:
        mom_row = cast("pd.Series", mom.loc[date]).dropna()
        if len(mom_row) < n_buckets:
            continue
        # Rank-then-qcut so equal momenta never crash qcut on duplicate edges.
        ranks = cast("pd.Series", mom_row.rank(method="first"))
        buckets = pd.qcut(ranks, n_buckets, labels=labels)
        for sym in mom_row.index:
            f = fwd.at[date, sym]
            if pd.notna(f):
                rows.append(
                    {
                        "date": date,
                        "symbol": sym,
                        "bucket": str(buckets[sym]),
                        "fwd_ret": float(cast("float", f)),
                    }
                )
    return pd.DataFrame(rows, columns=["date", "symbol", "bucket", "fwd_ret"])


def conditional_outcome_table(
    observations: pd.DataFrame,
    state_col: str = "bucket",
    fwd_col: str = "fwd_ret",
    labels: list[str] | None = None,
) -> pd.DataFrame:
    """Summarise the forward-return distribution per state, vs an ALL baseline.

    Given long-form ``observations`` (one row per ``(date, asset)`` with a state
    label and a forward return), returns one row per state plus a final ``ALL``
    row (unconditional), with: ``n``, ``mean_fwd_pct``, ``median_fwd_pct``,
    ``hit_rate`` (share of positive outcomes), ``std_fwd_pct``, and the 25th/75th
    forward-return percentiles. States are ordered by ``labels`` when given (so
    weak->strong reads naturally), else by first appearance. Empty input -> empty
    typed frame.
    """
    if observations.empty:
        return pd.DataFrame(columns=_TABLE_COLS)

    def _summary(state: str, vals: np.ndarray) -> dict[str, object]:
        return {
            "state": state,
            "n": int(vals.size),
            "mean_fwd_pct": float(np.mean(vals) * 100.0),
            "median_fwd_pct": float(np.median(vals) * 100.0),
            "hit_rate": float(np.mean(vals > 0.0)),
            "std_fwd_pct": float(np.std(vals, ddof=0) * 100.0),
            "p25_fwd_pct": float(np.percentile(vals, 25) * 100.0),
            "p75_fwd_pct": float(np.percentile(vals, 75) * 100.0),
        }

    states = labels if labels is not None else list(
        dict.fromkeys(observations[state_col].astype(str).tolist())
    )
    rows: list[dict[str, object]] = []
    for state in states:
        mask = observations[state_col].astype(str) == state
        vals = observations.loc[mask, fwd_col].to_numpy(dtype="float64")
        if vals.size:
            rows.append(_summary(state, vals))
    rows.append(_summary("ALL", observations[fwd_col].to_numpy(dtype="float64")))
    return pd.DataFrame(rows, columns=_TABLE_COLS)


def rotation_outcomes(
    panel_close: pd.DataFrame,
    lookback: int = 21,
    horizon: int = 21,
    n_buckets: int = 3,
) -> pd.DataFrame:
    """End-to-end: build point-in-time rotation observations and condition them.

    Convenience wrapper = ``conditional_outcome_table(rotation_observations(...))``,
    with the bucket order preserved weak->strong. Answers, for the given universe:
    "when an asset is in momentum bucket B, what was the forward ``horizon`` return
    distribution, vs the unconditional baseline?"
    """
    obs = rotation_observations(
        panel_close, lookback=lookback, horizon=horizon, n_buckets=n_buckets
    )
    return conditional_outcome_table(obs, labels=bucket_labels(n_buckets))
