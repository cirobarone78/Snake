"""Metrics for a cross-sectional ranking signal (WP3, ADR-034).

Portfolio metrics (`metrics.py`) answer "what did this return stream do?".
These answer the prior question: *did the ordering carry information?* — which
you can ask without ever forming a portfolio, and which is far harder to fool
yourself about.

The information coefficient is the cross-sectional correlation between predicted
rank and realised outcome, computed **per date and then averaged**. Pooling all
(date, symbol) pairs into one correlation instead would let a few days with wide
dispersion dominate, and would confuse "ranks well within a day" with "knows
which days are good" — two very different claims, only the first of which a
cross-sectional ranker makes.

Spearman (rank correlation) is the headline: the signal's job is to order, not to
predict magnitudes, and rank correlation is robust to the fat tails that make
Pearson jumpy on daily returns. Both are reported, because a large gap between
them is itself diagnostic — it means a few extreme outcomes are driving Pearson.

The top-minus-bottom spread turns the ordering into the crudest possible
portfolio: long the top quintile, short the bottom, equal-weighted. It is
deliberately naive — no risk model, no position sizing — because its purpose is
to answer "is there anything here at all?" before anyone builds something
sophisticated on top. Costs are charged on turnover, and H3 requires the spread
to survive them in *both* OOS halves.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd

from src.backtest.costs import TransactionCostModel

IC_COLUMNS = ["date", "n", "spearman", "pearson"]


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation via numpy. NaN when either side is constant."""
    if a.size < 2 or np.std(a) == 0.0 or np.std(b) == 0.0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman correlation = Pearson on average-tied ranks.

    Computed here rather than pulled from scipy: scipy is present only as a
    transitive dependency of scikit-learn, and decision D11 rules out adding
    dependencies in this phase. Average ranks give the standard tie correction,
    so this matches ``scipy.stats.spearmanr`` on the cases we use.
    """
    ra = pd.Series(a).rank(method="average").to_numpy(dtype="float64")
    rb = pd.Series(b).rank(method="average").to_numpy(dtype="float64")
    return _pearson(ra, rb)


def _per_date_ic(
    dates: pd.Series, predicted: pd.Series, realised: pd.Series, min_names: int
) -> pd.DataFrame:
    frame = pd.DataFrame({
        "date": dates.to_numpy(),
        "pred": predicted.to_numpy(dtype="float64"),
        "real": realised.to_numpy(dtype="float64"),
    }).dropna()
    rows: list[dict[str, object]] = []
    for date, group in frame.groupby("date", sort=True):
        n = len(group)
        if n < min_names:
            continue
        p = group["pred"].to_numpy(dtype="float64")
        r = group["real"].to_numpy(dtype="float64")
        # A day where every prediction (or every outcome) is identical has no
        # ordering to score: correlation is undefined, not zero.
        if np.unique(p).size < 2 or np.unique(r).size < 2:
            continue
        rows.append({
            "date": date,
            "n": n,
            "spearman": _spearman(p, r),
            "pearson": _pearson(p, r),
        })
    return pd.DataFrame(rows, columns=IC_COLUMNS)


def information_coefficient(
    dates: pd.Series,
    predicted: pd.Series,
    realised: pd.Series,
    min_names: int = 5,
) -> dict[str, float]:
    """Mean per-date rank/linear correlation between prediction and outcome.

    Returns ``spearman``, ``pearson``, ``spearman_std``, ``n_dates`` and
    ``spearman_t`` — a t-statistic on the mean daily IC (``mean / (std/sqrt(n))``).

    Read the t-statistic with care: consecutive dates share overlapping forward
    windows, so the daily ICs are autocorrelated and the effective sample is
    smaller than ``n_dates``. It is a rough guide to "is this distinguishable
    from zero", deliberately not a p-value.
    """
    table = _per_date_ic(dates, predicted, realised, min_names)
    if table.empty:
        return {
            "spearman": float("nan"), "pearson": float("nan"),
            "spearman_std": float("nan"), "spearman_t": float("nan"), "n_dates": 0.0,
        }
    sp = table["spearman"].to_numpy(dtype="float64")
    pe = table["pearson"].to_numpy(dtype="float64")
    mean_sp = float(np.mean(sp))
    std_sp = float(np.std(sp, ddof=1)) if sp.size > 1 else float("nan")
    t = (
        mean_sp / (std_sp / np.sqrt(sp.size))
        if sp.size > 1 and std_sp > 0.0
        else float("nan")
    )
    return {
        "spearman": mean_sp,
        "pearson": float(np.mean(pe)),
        "spearman_std": std_sp,
        "spearman_t": float(t),
        "n_dates": float(sp.size),
    }


def ic_series(
    dates: pd.Series, predicted: pd.Series, realised: pd.Series, min_names: int = 5
) -> pd.DataFrame:
    """Per-date IC table — the raw material behind ``information_coefficient``."""
    return _per_date_ic(dates, predicted, realised, min_names)


def hit_rate_outperform(predicted: pd.Series, outcomes: pd.Series, threshold: float = 0.5) -> float:
    """Share of correct directional calls at ``threshold``.

    Diagnostic only: a hit rate says nothing about calibration (a model can be
    right 55% of the time while claiming 90% confidence) and nothing about
    magnitude. The Brier score is the metric that matters; this is here because
    it is the number a human reads first.
    """
    p = predicted.astype("float64")
    y = outcomes.astype("float64")
    ok = p.notna() & y.notna()
    if not bool(ok.any()):
        return float("nan")
    calls = (cast("pd.Series", p[ok]) >= threshold).to_numpy()
    truth = cast("pd.Series", y[ok]).to_numpy(dtype="float64") > 0.5
    return float(np.mean(calls == truth))


def top_minus_bottom(
    dates: pd.Series,
    ranks: pd.Series,
    returns: pd.Series,
    q: float = 0.2,
    costs: TransactionCostModel | None = None,
    turnover: float = 2.0,
) -> pd.DataFrame:
    """Per-date long-top / short-bottom quintile spread, gross and net of costs.

    For each date: average ``returns`` of the top ``q`` fraction by rank, minus
    the average of the bottom ``q``. Equal weights, no risk model — the crudest
    read on whether the ordering separates winners from losers.

    ``costs`` charges a round trip on notional ``turnover`` (default 2.0 = fully
    replacing both legs) using the project's cost model. This is a deliberately
    pessimistic charge for a weekly rebalance that would in practice keep some
    names: **it makes H3 harder to pass, not easier**, which is the direction an
    honest test should err in.

    Returns columns ``date, n, gross, cost, net``. Dates with too few names for
    two disjoint buckets are skipped.
    """
    if not 0.0 < q <= 0.5:
        raise ValueError("q must be in (0, 0.5]")
    frame = pd.DataFrame({
        "date": dates.to_numpy(),
        "rank": ranks.to_numpy(dtype="float64"),
        "ret": returns.to_numpy(dtype="float64"),
    }).dropna()

    rows: list[dict[str, object]] = []
    for date, group in frame.groupby("date", sort=True):
        n = len(group)
        k = int(np.floor(n * q))
        if k < 1 or 2 * k > n:
            continue
        ordered = cast("pd.DataFrame", group.sort_values("rank"))
        bottom = float(ordered["ret"].to_numpy(dtype="float64")[:k].mean())
        top = float(ordered["ret"].to_numpy(dtype="float64")[-k:].mean())
        gross = top - bottom
        cost = costs.cost(turnover) if costs is not None else 0.0
        rows.append({
            "date": date, "n": n, "gross": gross, "cost": cost, "net": gross - cost,
        })
    return pd.DataFrame(rows, columns=["date", "n", "gross", "cost", "net"])


def summarize_spread(spread: pd.DataFrame, column: str = "net") -> dict[str, float]:
    """Mean, std, t-statistic and share of positive periods for a spread series.

    Same caveat as the IC t-statistic: overlapping forward windows inflate the
    effective sample, so ``t`` is indicative, not inferential.
    """
    if spread.empty or column not in spread.columns:
        return {"mean": float("nan"), "std": float("nan"), "t": float("nan"),
                "positive_share": float("nan"), "n": 0.0}
    vals = spread[column].to_numpy(dtype="float64")
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return {"mean": float("nan"), "std": float("nan"), "t": float("nan"),
                "positive_share": float("nan"), "n": 0.0}
    mean = float(np.mean(vals))
    std = float(np.std(vals, ddof=1)) if vals.size > 1 else float("nan")
    t = mean / (std / np.sqrt(vals.size)) if vals.size > 1 and std > 0.0 else float("nan")
    return {
        "mean": mean, "std": std, "t": float(t),
        "positive_share": float(np.mean(vals > 0.0)), "n": float(vals.size),
    }
