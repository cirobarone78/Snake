"""Tests for walk-forward splitting — no-look-ahead invariant and modes."""

from __future__ import annotations

import pandas as pd
import pytest

from src.backtest.splits import Split, split_frame, walk_forward_splits


def test_rolling_windows_slide_forward() -> None:
    splits = walk_forward_splits(n_samples=10, train_size=4, test_size=2, step=2)
    assert len(splits) == 3
    # rolling: fixed-size train window moving with the test window
    assert [(s.train_start, s.train_end) for s in splits] == [(0, 4), (2, 6), (4, 8)]
    assert [(s.test_start, s.test_end) for s in splits] == [(4, 6), (6, 8), (8, 10)]


def test_expanding_windows_anchor_at_zero() -> None:
    splits = walk_forward_splits(
        n_samples=10, train_size=4, test_size=2, step=2, expanding=True
    )
    assert all(s.train_start == 0 for s in splits)
    assert [s.train_end for s in splits] == [4, 6, 8]
    assert [(s.test_start, s.test_end) for s in splits] == [(4, 6), (6, 8), (8, 10)]


def test_step_defaults_to_test_size() -> None:
    default_step = walk_forward_splits(n_samples=10, train_size=4, test_size=2)
    explicit_step = walk_forward_splits(n_samples=10, train_size=4, test_size=2, step=2)
    assert default_step == explicit_step


def test_no_lookahead_test_always_after_train() -> None:
    for s in walk_forward_splits(n_samples=20, train_size=6, test_size=3, step=1):
        assert s.test_start >= s.train_end  # the cardinal invariant


def test_too_short_returns_no_splits() -> None:
    assert walk_forward_splits(n_samples=3, train_size=4, test_size=2) == []


def test_invalid_params_raise() -> None:
    with pytest.raises(ValueError, match="n_samples must be positive"):
        walk_forward_splits(n_samples=0, train_size=4, test_size=2)
    with pytest.raises(ValueError, match="must be positive"):
        walk_forward_splits(n_samples=10, train_size=0, test_size=2)
    with pytest.raises(ValueError, match="step must be positive"):
        walk_forward_splits(n_samples=10, train_size=4, test_size=2, step=0)


def test_split_rejects_lookahead_construction() -> None:
    with pytest.raises(ValueError, match="look-ahead"):
        Split(train_start=0, train_end=5, test_start=3, test_end=7)


def test_split_rejects_empty_windows() -> None:
    with pytest.raises(ValueError, match="empty train"):
        Split(train_start=4, train_end=4, test_start=4, test_end=6)
    with pytest.raises(ValueError, match="empty test"):
        Split(train_start=0, train_end=4, test_start=4, test_end=4)


def test_split_frame_slices_by_position() -> None:
    idx = pd.date_range("2020-01-01", periods=10, freq="D", tz="UTC")
    data = pd.Series(range(10), index=idx)
    split = Split(train_start=0, train_end=4, test_start=4, test_end=6)
    train, test = split_frame(data, split)
    assert list(train) == [0, 1, 2, 3]
    assert list(test) == [4, 5]
    # train and test never share an index entry
    assert set(train.index).isdisjoint(set(test.index))
