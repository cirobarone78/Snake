"""Offline tests for the multifactor walk-forward classifier (Fase 4). No network."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.models.multifactor import (
    WalkForwardResult,
    fit_predict_walk_forward,
    positions_from_predictions,
)


def _xy(n: int = 300, learnable: bool = True, seed: int = 0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    f1 = rng.normal(size=n)
    f2 = rng.normal(size=n)
    x = pd.DataFrame({"f1": f1, "f2": f2}, index=idx)
    if learnable:
        # target is a deterministic function of the features -> model must learn it
        y = pd.Series((f1 + f2 > 0).astype("float64"), index=idx, name="target")
    else:
        y = pd.Series(rng.integers(0, 2, n).astype("float64"), index=idx, name="target")
    return x, y


def test_walk_forward_is_out_of_sample() -> None:
    x, y = _xy(learnable=True)
    res = fit_predict_walk_forward(x, y, train_size=100, test_size=30)
    # OOS predictions exist and cover non-overlapping test windows after train
    assert len(res.prediction) > 0
    assert res.prediction.index.is_monotonic_increasing
    assert not res.prediction.index.has_duplicates
    # first prediction starts no earlier than the first train window end
    assert res.prediction.index.min() >= x.index[100]


def test_learnable_signal_beats_coinflip() -> None:
    x, y = _xy(learnable=True)
    res = fit_predict_walk_forward(x, y, train_size=120, test_size=30)
    # a deterministic target must be recovered well out-of-sample
    assert res.accuracy > 0.9


def test_noise_is_near_coinflip() -> None:
    x, y = _xy(learnable=False, seed=3)
    res = fit_predict_walk_forward(x, y, train_size=120, test_size=30)
    # pure noise: accuracy should sit near 0.5, never suspiciously high
    assert 0.35 < res.accuracy < 0.65


def test_too_short_returns_empty() -> None:
    x, y = _xy(n=20)
    res = fit_predict_walk_forward(x, y, train_size=100, test_size=30)
    assert isinstance(res, WalkForwardResult)
    assert res.prediction.empty
    assert np.isnan(res.accuracy)


def test_single_class_train_window_skipped() -> None:
    # all-up target in the first train window -> that split is skipped, no crash
    n = 200
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    x = pd.DataFrame({"f1": np.arange(n, dtype="float64")}, index=idx)
    y = pd.Series(np.r_[np.ones(120), np.zeros(80)], index=idx, name="target")
    res = fit_predict_walk_forward(x, y, train_size=100, test_size=20)
    # does not raise; may yield fewer/zero predictions depending on class balance
    assert isinstance(res, WalkForwardResult)


def test_positions_from_predictions_long_only() -> None:
    pred = pd.Series(
        [1.0, 0.0, 1.0],
        index=pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC"),
    )
    pos = positions_from_predictions(pred)
    assert pos.tolist() == [1.0, 0.0, 1.0]
    assert pos.name == "position"
