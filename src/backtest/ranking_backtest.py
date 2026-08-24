"""Walk-forward evaluation of the ranking models (WP3, ADR-034).

Pure orchestration over the WP2 panel: no fetching, no file writing, no report
formatting — those live in the CLI. Keeping the evaluation itself a pure function
is what lets the whole protocol be tested offline on synthetic data, which is the
only way to know the *harness* is honest before trusting what it says about the
models.

The protocol is the one frozen in ADR-034 before any result was seen:

1. Sample the panel weekly (Mondays, decision D5) — the decision frequency of the
   paper portfolio, so the backtest measures the thing WP4 would actually trade.
2. Walk forward over **dates**, not rows: a fold boundary must never cut a
   cross-section in half, or the same day would be partly train and partly test.
3. Embargo the last ``horizon`` trading days of each training window, because
   their labels resolve inside the test window.
4. Fit the model and the isotonic calibrator on the training fold only.
5. Score the test fold, and keep every prediction so the two OOS halves can be
   evaluated separately (H3 requires the sign to hold in both, not on average).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import numpy as np
import pandas as pd

from src.backtest.splits import walk_forward_splits
from src.models.calibration import IsotonicCalibrator
from src.models.etf_ranker import RankerModel

# One trading week; the embargo is expressed in weekly samples, so a 20-session
# horizon is 4 weekly steps.
SESSIONS_PER_WEEK = 5


@dataclass
class FoldResult:
    """Out-of-sample predictions of one model on one fold."""

    fold: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    n_train: int
    predictions: pd.DataFrame = field(repr=False)


def weekly_sample(panel: pd.DataFrame, weekday: int = 0) -> pd.DataFrame:
    """Keep the cross-sections falling on ``weekday`` (0 = Monday, decision D5).

    A US market holiday on a Monday simply removes that week: no forward-fill,
    because a decision that could not have been taken should not be scored.
    """
    dates = cast("pd.Series", panel["date"])
    keep = dates.dt.weekday == weekday
    return cast("pd.DataFrame", panel[keep]).reset_index(drop=True)


def _unique_dates(panel: pd.DataFrame) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(pd.unique(cast("pd.Series", panel["date"]))))


def walk_forward_predict(
    panel: pd.DataFrame,
    model: RankerModel,
    target: str,
    train_weeks: int,
    test_weeks: int,
    embargo_weeks: int,
    calibrate: bool = True,
) -> list[FoldResult]:
    """Run ``model`` across walk-forward folds, returning per-fold OOS predictions.

    Splits are computed over the **distinct dates** so a cross-section is never
    torn between train and test. Each fold's output frame carries the raw score,
    the calibrated probability, the within-date rank and the realised target, so
    every downstream metric reads from the same rows.
    """
    dates = _unique_dates(panel)
    splits = walk_forward_splits(
        len(dates), train_size=train_weeks, test_size=test_weeks, embargo=embargo_weeks
    )
    results: list[FoldResult] = []
    for i, split in enumerate(splits):
        train_dates = cast("pd.DatetimeIndex", dates[split.train_slice])
        test_dates = cast("pd.DatetimeIndex", dates[split.test_slice])
        col = cast("pd.Series", panel["date"])
        train = cast("pd.DataFrame", panel[col.isin(pd.Series(train_dates))])
        test = cast("pd.DataFrame", panel[col.isin(pd.Series(test_dates))])
        y_train = cast("pd.Series", train[target])
        if train.empty or test.empty or y_train.notna().sum() == 0:
            continue

        model.fit(train, y_train)
        raw_test = model.predict_proba(test)

        proba = raw_test
        if calibrate and model.calibratable:
            # The calibrator sees train scores and train outcomes only.
            cal = IsotonicCalibrator().fit(model.predict_proba(train), y_train)
            proba = cal.calibrate(raw_test)

        preds = pd.DataFrame({
            "date": cast("pd.Series", test["date"]).to_numpy(),
            "symbol": cast("pd.Series", test["symbol"]).to_numpy(),
            "score": raw_test.to_numpy(dtype="float64"),
            "proba": proba.to_numpy(dtype="float64"),
            "target": cast("pd.Series", test[target]).to_numpy(dtype="float64"),
        })
        preds["rank"] = preds.groupby("date")["score"].rank(pct=True, method="average")
        results.append(
            FoldResult(
                fold=i,
                train_start=cast("pd.Timestamp", train_dates[0]),
                train_end=cast("pd.Timestamp", train_dates[-1]),
                test_start=cast("pd.Timestamp", test_dates[0]),
                test_end=cast("pd.Timestamp", test_dates[-1]),
                n_train=len(train), predictions=preds,
            )
        )
    return results


def concat_predictions(folds: list[FoldResult]) -> pd.DataFrame:
    """Stack every fold's OOS predictions into one chronological frame."""
    if not folds:
        return pd.DataFrame(columns=["date", "symbol", "score", "proba", "target", "rank", "fold"])
    parts: list[pd.DataFrame] = []
    for f in folds:
        block = f.predictions.copy()
        block["fold"] = f.fold
        parts.append(block)
    out = pd.concat(parts, ignore_index=True)
    return out.sort_values(["date", "symbol"]).reset_index(drop=True)


def split_halves(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chronological halves of the OOS period, split on distinct dates.

    H3 is judged on both halves separately: a spread that is positive only
    because one regime carried it is not a stable edge, and averaging would hide
    exactly that.
    """
    if predictions.empty:
        return predictions, predictions.copy()
    dates = _unique_dates(predictions)
    cutoff = dates[len(dates) // 2]
    col = cast("pd.Series", predictions["date"])
    first = cast("pd.DataFrame", predictions[col < cutoff])
    second = cast("pd.DataFrame", predictions[col >= cutoff])
    return first, second


def realised_excess(panel: pd.DataFrame, predictions: pd.DataFrame, column: str) -> pd.Series:
    """Attach the realised excess return to each prediction row.

    Kept separate from the target so a *binary* target (outperform) can still be
    scored on the *continuous* outcome, which is what the top-minus-bottom spread
    needs.
    """
    key = cast("pd.DataFrame", panel[["date", "symbol", column]])
    left = cast("pd.DataFrame", predictions[["date", "symbol"]])
    merged = left.merge(key, on=["date", "symbol"], how="left")
    values = cast("pd.Series", merged[column]).to_numpy(dtype="float64")
    return pd.Series(values, index=predictions.index, name=column)


def fold_summary(folds: list[FoldResult]) -> pd.DataFrame:
    """One row per fold: window boundaries and sizes, for the report's audit trail."""
    if not folds:
        return pd.DataFrame(columns=["fold", "train_start", "train_end", "test_start", "test_end", "n_train", "n_test"])
    return pd.DataFrame([
        {
            "fold": f.fold,
            "train_start": str(f.train_start)[:10], "train_end": str(f.train_end)[:10],
            "test_start": str(f.test_start)[:10], "test_end": str(f.test_end)[:10],
            "n_train": f.n_train, "n_test": len(f.predictions),
        }
        for f in folds
    ])


def embargo_gap_days(folds: list[FoldResult]) -> list[int]:
    """Calendar days between each fold's last train date and first test date.

    Reported in the audit trail so a reader can verify the embargo actually
    happened rather than taking the parameter's word for it.
    """
    return [int((f.test_start - f.train_end) / np.timedelta64(1, "D")) for f in folds]
