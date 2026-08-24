"""Walk-forward splitting for time-series backtesting (Fase 2).

The cardinal rule of honest backtesting: never let the model see the
future. A walk-forward scheme enforces this *structurally* — every test
window sits strictly after its training window, in chronological order, with
no shuffling and no overlap between a split's train and test segments. This
is the antidote to the look-ahead bias flagged as non-negotiable in
CLAUDE.md.

Two modes:
- rolling: a fixed-size training window that slides forward
- expanding: a training window anchored at t0 that grows over time

Chronological order alone is *not* enough when the target looks forward. If the
label at ``t`` is realised over the next ``h`` observations, the last ``h`` rows
of a training window carry outcomes that happen inside the test window: the model
is scored on a period it was partly trained on. The ``embargo`` parameter drops
that overlap (a *purge*, in Lopez de Prado's terms), so ``embargo = h`` is the
right setting for an ``h``-step-ahead target. It defaults to 0 — the historical
behaviour, correct for a one-step target — and must be set deliberately.

The module is index-agnostic: it operates on integer positions over
``n_samples`` and leaves it to the caller to map positions back to a
DatetimeIndex (``split_frame``). That keeps it usable for any asset class
and any frequency (ADR-014).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Split:
    """One train/test fold, as integer positions with exclusive ends.

    The no-look-ahead invariant (``test_start >= train_end``) is checked at
    construction: a test window may never start before its train window ends.
    """

    train_start: int
    train_end: int  # exclusive
    test_start: int
    test_end: int  # exclusive

    def __post_init__(self) -> None:
        if self.train_start < 0 or self.test_start < 0:
            raise ValueError("split positions must be non-negative")
        if self.train_end <= self.train_start:
            raise ValueError("empty train window")
        if self.test_end <= self.test_start:
            raise ValueError("empty test window")
        if self.test_start < self.train_end:
            raise ValueError("test window overlaps train window (look-ahead)")

    @property
    def embargo(self) -> int:
        """Observations skipped between the end of train and the start of test."""
        return self.test_start - self.train_end

    @property
    def train_slice(self) -> slice:
        return slice(self.train_start, self.train_end)

    @property
    def test_slice(self) -> slice:
        return slice(self.test_start, self.test_end)


def walk_forward_splits(
    n_samples: int,
    train_size: int,
    test_size: int,
    step: int | None = None,
    *,
    expanding: bool = False,
    embargo: int = 0,
) -> list[Split]:
    """Generate walk-forward folds over ``n_samples`` ordered observations.

    Parameters
    ----------
    n_samples:
        Total number of observations (assumed already in chronological order).
    train_size:
        Number of observations in each training window. In ``expanding`` mode
        this is the size of the *first* training window; it grows thereafter.
    test_size:
        Number of observations in each (out-of-sample) test window.
    step:
        Distance between consecutive test windows. Defaults to ``test_size``
        (contiguous, non-overlapping test segments that tile the timeline).
    expanding:
        If True, each training window starts at position 0 and grows; if
        False (default), training is a fixed-size rolling window.
    embargo:
        Observations dropped from the **end of each training window**, so the
        test window starts ``embargo`` positions after the last training row.
        Set it to the target horizon ``h`` when the label at ``t`` is realised
        over ``(t, t+h]``: otherwise the final ``h`` training labels resolve
        inside the test period and the fold is contaminated. Default 0 keeps
        the original behaviour. The embargoed rows are dropped, never handed to
        the test set — the test window's position is unchanged, so folds tile
        the timeline exactly as before and only the train window shrinks.

    Returns
    -------
    A list of ``Split`` folds. Empty if the data is too short for even one
    train+test pair (this is a valid outcome, not an error).
    """
    if n_samples <= 0:
        raise ValueError("n_samples must be positive")
    if train_size <= 0 or test_size <= 0:
        raise ValueError("train_size and test_size must be positive")
    if embargo < 0:
        raise ValueError("embargo must be non-negative")
    step = test_size if step is None else step
    if step <= 0:
        raise ValueError("step must be positive")

    splits: list[Split] = []
    test_start = train_size
    while test_start + test_size <= n_samples:
        train_start = 0 if expanding else test_start - train_size
        train_end = test_start - embargo
        # An embargo wider than the training window leaves nothing to fit on:
        # skip the fold rather than emit a degenerate one.
        if train_end > train_start:
            splits.append(
                Split(
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_start + test_size,
                )
            )
        test_start += step
    return splits


def split_frame(
    data: pd.DataFrame | pd.Series, split: Split
) -> tuple[pd.DataFrame | pd.Series, pd.DataFrame | pd.Series]:
    """Slice ``data`` into ``(train, test)`` by positional split.

    Uses ``.iloc`` so it works regardless of the index type (DatetimeIndex,
    RangeIndex, ...). The caller is responsible for passing data already in
    chronological order.
    """
    return data.iloc[split.train_slice], data.iloc[split.test_slice]
