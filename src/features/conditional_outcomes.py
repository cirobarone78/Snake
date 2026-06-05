"""Conditional outcome study: "given this rotation state, what happened next?".

This is the **probabilistic layer** the rotation screeners deliberately deferred
(see ``screener.py``): not predicting a single asset, but estimating — from
history — the *distribution of forward returns conditional on a rotation state*.

Rather than wait weeks for live snapshots to accumulate, we reconstruct the state
**point-in-time from years of prices**:

1. **State** at each date = the asset's trailing ``lookback`` momentum, **ranked
   cross-sectionally** within its universe that day, bucketed (weak / mid /
   strong). Optionally enriched with extra per-date states (e.g. a market regime
   bull/bearxvol, or the crypto halving phase) so "state" is the full situation,
   not momentum alone. Cross-sectional ranking and momentum use only data up to
   the date → no look-ahead in defining the state.
2. **Outcome** = the forward simple return over ``horizon`` days, realised strictly
   *after* the state is known.
3. **Conditioning** = pool ``(date, asset)`` observations and summarise the
   forward-return distribution per state, against the unconditional baseline.

Honesty guards (CLAUDE.md, VISION #1):
- With ``step=1`` the reported ``n`` counts observations, **not** independent
  samples: daily observations with a multi-day ``horizon`` overlap, so
  autocorrelation inflates the effective sample. Use ``step=horizon`` for
  **non-overlapping** windows when you want an honest count, and ``split_by_date``
  for an **out-of-sample** check that a bucket edge is not in-sample noise.
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
    step: int = 1,
    extra_states: dict[str, pd.Series] | None = None,
) -> pd.DataFrame:
    """Long-form ``(date, symbol, bucket, fwd_ret)`` observations, point-in-time.

    ``panel_close`` is a date-indexed frame of close prices, one column per asset
    in the rotation universe. For each sampled date we rank the assets by trailing
    ``lookback`` momentum into ``n_buckets`` cross-sectional buckets (ties broken
    deterministically), and attach the forward ``horizon`` return.

    ``step`` subsamples the dates (every ``step``-th): ``step=horizon`` yields
    **non-overlapping** forward windows, so ``n`` counts near-independent samples.
    ``extra_states`` maps a column name to a date-indexed label Series (e.g. a
    market regime); each is looked up per date and attached (``"unknown"`` when the
    date is missing), enriching the state beyond momentum alone.

    Dates with fewer than ``n_buckets`` valid assets are skipped. No look-ahead:
    the bucket uses momentum up to the date, the outcome is realised after it.
    """
    if step <= 0:
        raise ValueError("step must be positive")
    panel = cast("pd.DataFrame", panel_close.sort_index()).astype("float64")
    mom = panel / panel.shift(lookback) - 1.0
    fwd = panel.shift(-horizon) / panel - 1.0
    labels = bucket_labels(n_buckets)
    extra = extra_states or {}
    base_cols = ["date", "symbol", "bucket", "fwd_ret"]

    rows: list[dict[str, object]] = []
    for date in panel.index[::step]:
        mom_row = cast("pd.Series", mom.loc[date]).dropna()
        if len(mom_row) < n_buckets:
            continue
        # Rank-then-qcut so equal momenta never crash qcut on duplicate edges.
        ranks = cast("pd.Series", mom_row.rank(method="first"))
        buckets = pd.qcut(ranks, n_buckets, labels=labels)
        extra_vals = {name: _label_at(ser, date) for name, ser in extra.items()}
        for sym in mom_row.index:
            f = fwd.at[date, sym]
            if pd.notna(f):
                row: dict[str, object] = {
                    "date": date,
                    "symbol": sym,
                    "bucket": str(buckets[sym]),
                    "fwd_ret": float(cast("float", f)),
                }
                row.update(extra_vals)
                rows.append(row)
    return pd.DataFrame(rows, columns=base_cols + list(extra.keys()))


def _label_at(series: pd.Series, date: object) -> str:
    """Label of ``series`` at ``date``, ``"unknown"`` if absent/NaN."""
    if date in series.index:
        val = series.loc[date]
        if not pd.isna(val):
            return str(val)
    return "unknown"


def conditional_outcome_table(
    observations: pd.DataFrame,
    state_col: str | list[str] = "bucket",
    fwd_col: str = "fwd_ret",
    labels: list[str] | None = None,
) -> pd.DataFrame:
    """Summarise the forward-return distribution per state, vs an ALL baseline.

    Given long-form ``observations`` (one row per ``(date, asset)`` with a state
    label and a forward return), returns one row per state plus a final ``ALL``
    row (unconditional), with: ``n``, ``mean_fwd_pct``, ``median_fwd_pct``,
    ``hit_rate`` (share of positive outcomes), ``std_fwd_pct``, and the 25th/75th
    forward-return percentiles.

    ``state_col`` may be a single column or a list (then the state is the combined
    label, e.g. momentum bucket x regime). For a single column, ``labels`` orders
    the rows (weak->strong reads naturally); otherwise states are ordered by first
    appearance. Empty input -> empty typed frame.
    """
    if observations.empty:
        return pd.DataFrame(columns=_TABLE_COLS)

    cols = [state_col] if isinstance(state_col, str) else list(state_col)
    composite = observations[cols].astype(str).agg(" | ".join, axis=1)
    if len(cols) == 1 and labels is not None:
        states = labels
    else:
        states = list(dict.fromkeys(cast("list[str]", composite.tolist())))

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

    fwd = cast("pd.Series", observations[fwd_col]).astype("float64")
    rows: list[dict[str, object]] = []
    for state in states:
        vals = cast("pd.Series", fwd[composite == state]).to_numpy(dtype="float64")
        if vals.size:
            rows.append(_summary(str(state), vals))
    rows.append(_summary("ALL", fwd.to_numpy(dtype="float64")))
    return pd.DataFrame(rows, columns=_TABLE_COLS)


def rotation_outcomes(
    panel_close: pd.DataFrame,
    lookback: int = 21,
    horizon: int = 21,
    n_buckets: int = 3,
    step: int = 1,
) -> pd.DataFrame:
    """End-to-end: build point-in-time rotation observations and condition them.

    Convenience wrapper = ``conditional_outcome_table(rotation_observations(...))``,
    with the bucket order preserved weak->strong. Answers, for the given universe:
    "when an asset is in momentum bucket B, what was the forward ``horizon`` return
    distribution, vs the unconditional baseline?". Pass ``step=horizon`` for a
    non-overlapping (honest-``n``) version.
    """
    obs = rotation_observations(
        panel_close, lookback=lookback, horizon=horizon, n_buckets=n_buckets, step=step
    )
    return conditional_outcome_table(obs, labels=bucket_labels(n_buckets))


def split_by_date(
    observations: pd.DataFrame,
    train_frac: float = 0.5,
    date_col: str = "date",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chronological out-of-sample split of observations into (train, test).

    Splits at the ``train_frac`` quantile of the **distinct dates**, so all
    observations sharing a date stay on the same side and the test set is strictly
    later than the train set — the honest way to ask "does a bucket edge measured
    in-sample survive out-of-sample?". Empty or degenerate input -> two empties.
    """
    if observations.empty or not 0.0 < train_frac < 1.0:
        empty = observations.iloc[0:0]
        return empty, empty.copy()
    dates = cast("pd.Series", observations[date_col])
    unique_sorted = pd.Index(sorted(pd.unique(dates)))
    cutoff = unique_sorted[min(int(len(unique_sorted) * train_frac), len(unique_sorted) - 1)]
    train = cast("pd.DataFrame", observations[dates < cutoff])
    test = cast("pd.DataFrame", observations[dates >= cutoff])
    return train, test


def state_ranking(table: pd.DataFrame, by: str = "hit_rate") -> list[str]:
    """States (excluding ``ALL``) ordered best-first by ``by`` (default hit_rate).

    Used to compare a train ranking against a test ranking: if the order is stable,
    the conditioning carries signal; if it reshuffles, it was in-sample noise.
    """
    if table.empty:
        return []
    conditioned = cast("pd.DataFrame", table[table["state"] != "ALL"])
    ranked = cast("pd.DataFrame", conditioned.sort_values(by=by, ascending=False))
    return [str(s) for s in ranked["state"].tolist()]
