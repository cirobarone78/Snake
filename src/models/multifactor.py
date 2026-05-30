"""Multifactor directional classifier with walk-forward OOS evaluation (Fase 4).

The first "real" model of the project: a logistic regression that predicts
next-day direction from the multifactor design matrix (``src.features.dataset``).
It is deliberately the simplest credible ML model — per ROADMAP Fase 4, we climb
the complexity ladder (logistic -> gradient boosting -> ...) only if a simpler
rung shows out-of-sample edge over the Fase 2 baselines.

Honest evaluation is the whole point (CLAUDE.md):
- **Walk-forward only**: the model is fit on each split's train window and
  predicts its test window, reusing ``src.backtest.walk_forward_splits``. Test
  windows are strictly out-of-sample and tile the timeline once.
- **Standardisation is fit on train only**: the scaler sees train statistics,
  never test — otherwise the test distribution leaks into preprocessing.
- Predicted probabilities are turned into the same {0, +1} long-only positions
  as the baselines, so the result is directly comparable via
  ``src.backtest`` metrics and the cost model.

``scikit-learn`` is in the confirmed stack (ADR-009); it is a light, standard
dependency (not a deep-learning framework).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from src.backtest.splits import walk_forward_splits


@dataclass(frozen=True)
class WalkForwardResult:
    """Out-of-sample predictions stitched across all test windows.

    ``proba`` is the model's P(up) on each OOS day; ``prediction`` is the {0,1}
    class; ``target`` is the realised direction. All share one DatetimeIndex
    covering the union of test windows (chronological, no overlap).
    """

    proba: pd.Series
    prediction: pd.Series
    target: pd.Series

    @property
    def accuracy(self) -> float:
        """Directional accuracy over the OOS predictions (NaN if empty)."""
        if self.prediction.empty:
            return float("nan")
        return float((self.prediction == self.target).mean())


def fit_predict_walk_forward(
    x: pd.DataFrame,
    y: pd.Series,
    train_size: int,
    test_size: int,
    *,
    expanding: bool = True,
    C: float = 1.0,
) -> WalkForwardResult:
    """Fit a logistic regression walk-forward and collect OOS predictions.

    For each split: standardise on train, fit on train, predict the test window.
    The scaler and model never see test data at fit time. Test windows are
    concatenated into one OOS series. Returns empty series if the data is too
    short for even one split (a valid outcome, not an error).
    """
    x = x.sort_index()
    y = y.reindex(x.index)
    n = len(x)
    splits = walk_forward_splits(n, train_size=train_size, test_size=test_size, expanding=expanding)

    proba_parts: list[pd.Series] = []
    pred_parts: list[pd.Series] = []
    tgt_parts: list[pd.Series] = []

    x_values = x.to_numpy(dtype="float64")
    y_values = y.to_numpy(dtype="float64")

    for sp in splits:
        x_train = x_values[sp.train_slice]
        y_train = y_values[sp.train_slice]
        x_test = x_values[sp.test_slice]
        # a degenerate train window (one class only) can't fit a classifier
        if len(np.unique(y_train)) < 2:
            continue
        scaler = StandardScaler().fit(x_train)
        model = LogisticRegression(C=C, max_iter=1000)
        model.fit(scaler.transform(x_train), y_train)
        p_up = model.predict_proba(scaler.transform(x_test))[:, 1]
        test_index = x.index[sp.test_slice]
        proba_parts.append(pd.Series(p_up, index=test_index))
        pred_parts.append(pd.Series((p_up > 0.5).astype("float64"), index=test_index))
        tgt_parts.append(cast("pd.Series", y.iloc[sp.test_slice]))

    if not proba_parts:
        empty = pd.Series(dtype="float64")
        return WalkForwardResult(empty, empty.copy(), empty.copy())

    return WalkForwardResult(
        proba=pd.concat(proba_parts).rename("proba"),
        prediction=pd.concat(pred_parts).rename("prediction"),
        target=pd.concat(tgt_parts).rename("target"),
    )


def positions_from_predictions(prediction: pd.Series) -> pd.Series:
    """Map {0, 1} direction predictions to long-only positions {0.0, +1.0}.

    Same convention as the baselines (``signal_from_forecast`` long-only): go
    long when the model predicts "up", stay flat otherwise. The resulting
    position series is directly usable with ``strategy_returns`` and the cost
    model for a like-for-like comparison against Fase 2.
    """
    return cast("pd.Series", prediction.astype("float64")).rename("position")
