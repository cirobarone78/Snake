# pyright: strict
"""Probability calibration and calibration scoring (WP3, ADR-034).

A model can order assets well and still lie about *how sure* it is. Ordering is
measured by the information coefficient; this module measures and fixes the other
half — whether "0.70" actually means "happens 70% of the time".

That distinction is the whole product promise of ADR-032: the system outputs a
probability with its uncertainty, never a "buy now". A miscalibrated 0.70 is
worse than useless, because a reader would size a position on it.

**Isotonic regression** maps raw scores to calibrated probabilities under a single
assumption — that the mapping is monotone (a higher score never means a lower
probability). It cannot reorder anything, so it never invents discrimination that
was not already there: it can only fix the *level*. That is why the IC is
unchanged by calibration while the Brier score can improve.

The non-negotiable rule (asserted in the tests): the calibrator is fit on the
**training fold only**. Fitting it on the test set would let the model peek at the
outcomes it is being scored on — the exact leak the walk-forward exists to prevent.

The Brier score is the primary metric of ADR-034: mean squared error between the
forecast probability and the realised 0/1 outcome. Lower is better; it rewards
being right *and* being honest about confidence, and it is the metric the
climatology baseline is genuinely hard to beat on.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

RELIABILITY_COLUMNS = [
    "bin", "lower", "upper", "n", "mean_predicted", "observed_frequency", "gap",
]


class IsotonicCalibrator:
    """Monotone score -> probability map, fit on train, applied to test.

    ``fit`` learns the map from training scores and outcomes; ``calibrate``
    applies it. An unfit calibrator passes scores through unchanged rather than
    raising, so a fold with too little data to calibrate degrades to the raw
    model instead of vanishing from the comparison.
    """

    def __init__(self, out_of_bounds: str = "clip") -> None:
        self.out_of_bounds = out_of_bounds
        self._model: IsotonicRegression | None = None

    @property
    def is_fitted(self) -> bool:
        return self._model is not None

    def fit(self, scores: pd.Series, outcomes: pd.Series) -> IsotonicCalibrator:
        """Learn the calibration map from **training** scores and outcomes."""
        s = scores.astype("float64")
        y = outcomes.astype("float64")
        ok = s.notna() & y.notna()
        x_arr = cast("pd.Series", s[ok]).to_numpy(dtype="float64")
        y_arr = cast("pd.Series", y[ok]).to_numpy(dtype="float64")
        # Isotonic on a constant score or a single class has nothing to learn:
        # leave the calibrator unfit so scores pass through untouched.
        if x_arr.size < 2 or np.unique(x_arr).size < 2 or np.unique(y_arr).size < 2:
            self._model = None
            return self
        model = IsotonicRegression(
            y_min=0.0, y_max=1.0, increasing=True, out_of_bounds=self.out_of_bounds
        )
        model.fit(x_arr, y_arr)
        self._model = model
        return self

    def calibrate(self, scores: pd.Series) -> pd.Series:
        """Apply the fitted map. NaN scores stay NaN; output is clipped to [0, 1]."""
        s = scores.astype("float64")
        if self._model is None:
            return s.clip(0.0, 1.0)
        out = pd.Series(np.nan, index=s.index, name="calibrated", dtype="float64")
        ok = s.notna()
        if not bool(ok.any()):
            return out
        vals = cast("np.ndarray", self._model.predict(
            cast("pd.Series", s[ok]).to_numpy(dtype="float64")
        ))
        out[ok] = np.clip(vals, 0.0, 1.0)
        return out


def _aligned(p: pd.Series, y: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Finite (probability, outcome) pairs as arrays, NaN rows dropped."""
    ps = p.astype("float64")
    ys = y.astype("float64")
    ok = ps.notna() & ys.notna()
    return (
        cast("pd.Series", ps[ok]).to_numpy(dtype="float64"),
        cast("pd.Series", ys[ok]).to_numpy(dtype="float64"),
    )


def brier_score(p: pd.Series, y: pd.Series) -> float:
    """Mean squared error of probabilistic forecasts. Lower is better.

    ``mean((p - y)^2)`` over rows where both are present. A constant forecast at
    the base rate scores ``rate * (1 - rate)`` — that is the climatology bar of
    ADR-034, and it is not a low one.
    """
    pa, ya = _aligned(p, y)
    if pa.size == 0:
        return float("nan")
    return float(np.mean((pa - ya) ** 2))


def brier_skill_score(p: pd.Series, y: pd.Series, reference: float) -> float:
    """Fractional improvement over a ``reference`` Brier score.

    ``1 - brier/reference``: positive means better than the reference, 0 means
    indistinguishable, negative means worse. Reported alongside the raw Brier
    because a difference of 0.003 is hard to read as either large or trivial.
    """
    b = brier_score(p, y)
    if not np.isfinite(b) or reference <= 0.0 or not np.isfinite(reference):
        return float("nan")
    return float(1.0 - b / reference)


def expected_calibration_error(p: pd.Series, y: pd.Series, bins: int = 10) -> float:
    """Weighted mean gap between predicted probability and observed frequency.

    Bins the forecasts, compares each bin's mean prediction to the realised rate,
    and averages the absolute gaps weighted by bin population. 0 is perfect
    calibration. Complements the Brier score, which mixes calibration and
    discrimination into one number and so cannot say *which* one is failing.
    """
    table = reliability_table(p, y, bins=bins)
    if table.empty:
        return float("nan")
    n = cast("pd.Series", table["n"]).to_numpy(dtype="float64")
    gap = cast("pd.Series", table["gap"]).to_numpy(dtype="float64")
    total = float(n.sum())
    if total <= 0.0:
        return float("nan")
    return float(np.sum(n * np.abs(gap)) / total)


def reliability_table(p: pd.Series, y: pd.Series, bins: int = 10) -> pd.DataFrame:
    """Per-bin predicted vs observed frequency — the calibration curve as a table.

    Equal-width bins over ``[0, 1]``. Empty bins are omitted rather than shown as
    zeros, which would read as "predicted 0.05, never happened" when in fact
    nothing was ever predicted there. ``gap = observed - mean_predicted``:
    negative means the model was overconfident in that band.
    """
    if bins <= 0:
        raise ValueError("bins must be positive")
    pa, ya = _aligned(p, y)
    if pa.size == 0:
        return pd.DataFrame(columns=RELIABILITY_COLUMNS)

    edges = np.linspace(0.0, 1.0, bins + 1)
    idx = np.clip(np.digitize(pa, edges[1:-1], right=False), 0, bins - 1)
    rows: list[dict[str, object]] = []
    for b in range(bins):
        sel = idx == b
        n = int(sel.sum())
        if n == 0:
            continue
        mean_p = float(pa[sel].mean())
        obs = float(ya[sel].mean())
        rows.append({
            "bin": b,
            "lower": float(edges[b]),
            "upper": float(edges[b + 1]),
            "n": n,
            "mean_predicted": mean_p,
            "observed_frequency": obs,
            "gap": obs - mean_p,
        })
    return pd.DataFrame(rows, columns=RELIABILITY_COLUMNS)
