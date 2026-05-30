"""Walk-forward out-of-sample evaluation of a forecast (Fase 2 / 2.1).

The notebook 04 backtest built its out-of-sample return stream with an inline
helper. Reusing that logic for robustness sweeps (lookback grids, more assets)
is the moment to promote it to tested code rather than copy a prototype.

Given a causal forecast (knowable at ``t-1`` for the return at ``t``), this
collects the strategy's realized returns **only over the walk-forward test
windows**, in chronological order, with no overlap — so the reported metrics
never touch a period used to "develop" the signal. The forecast itself must
already be causal (e.g. ``momentum_forecast`` shifts); this module adds the
out-of-sample *selection*, not the causality.

No new modelling assumptions: it is plumbing over ``splits`` + ``models``.
Asset-class-agnostic (ADR-014): window sizes are in observations.
"""

from __future__ import annotations

from typing import cast

import pandas as pd

from src.backtest.costs import TransactionCostModel
from src.backtest.splits import walk_forward_splits
from src.models.baseline import signal_from_forecast, strategy_returns


def oos_strategy_returns(
    returns: pd.Series,
    forecast: pd.Series,
    *,
    train_size: int = 365,
    test_size: int = 90,
    expanding: bool = True,
    long_only: bool = True,
    cost_model: TransactionCostModel | None = None,
) -> pd.Series:
    """Concatenate net strategy returns over the walk-forward test windows.

    ``returns`` and ``forecast`` share the asset's index. The forecast is
    mapped to positions (``signal_from_forecast``), then for each fold the
    test-window slice of positions is applied to the test-window returns
    (``strategy_returns``, optionally charging turnover via ``cost_model``).
    The per-fold pieces are concatenated in order.

    Returns an empty float Series if the data is too short for any fold.
    """
    positions = signal_from_forecast(forecast, long_only=long_only)
    n = len(returns)
    pieces: list[pd.Series] = []
    for sp in walk_forward_splits(
        n, train_size=train_size, test_size=test_size, expanding=expanding
    ):
        test_idx = returns.index[sp.test_slice]
        pos_te = positions.reindex(test_idx)
        ret_te = returns.reindex(test_idx)
        pieces.append(strategy_returns(pos_te, ret_te, cost_model=cost_model))
    if not pieces:
        return pd.Series(dtype=float, name="strategy_return")
    return cast("pd.Series", pd.concat(pieces))


def oos_index_start(
    returns: pd.Series,
    *,
    train_size: int = 365,
    test_size: int = 90,
    expanding: bool = True,
) -> pd.Timestamp | None:
    """First out-of-sample timestamp (start of the earliest test window).

    Returns ``None`` if the series is too short for any fold. Useful to align
    passive benchmarks to the same OOS window the strategy is scored on.
    """
    splits = walk_forward_splits(
        len(returns), train_size=train_size, test_size=test_size, expanding=expanding
    )
    if not splits:
        return None
    return cast("pd.Timestamp", returns.index[splits[0].test_start])
