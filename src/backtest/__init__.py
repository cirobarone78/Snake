"""Backtesting evaluation harness (Fase 2).

This package is the *evaluation infrastructure* that must exist before any
model: metrics, walk-forward splitting and passive benchmarks. Per ROADMAP
Fase 2, building this first is what makes every later result trustworthy.

Design choices (engine: custom — ADR-009 left this open to Fase 2):
- Custom implementation for total control over no-look-ahead and cost
  modelling, instead of a vectorised library.
- Asset-class-agnostic (ADR-014): annualization and calendars are
  parameters, never hardcoded.
"""

from __future__ import annotations

from src.backtest.benchmark import (
    buy_and_hold_equity,
    buy_and_hold_returns,
    dca_equity,
)
from src.backtest.costs import (
    BINANCE_SPOT,
    KRAKEN_SPOT,
    FeeModel,
    SlippageModel,
    TransactionCostModel,
    estimate_half_spread_bps,
)
from src.backtest.metrics import (
    PerformanceSummary,
    annualized_return,
    annualized_volatility,
    calmar_ratio,
    drawdown_series,
    equity_curve,
    hit_rate,
    max_drawdown,
    max_drawdown_duration,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    summarize,
    time_underwater,
    total_return,
)
from src.backtest.splits import Split, split_frame, walk_forward_splits

__all__ = [
    "BINANCE_SPOT",
    "KRAKEN_SPOT",
    "FeeModel",
    "PerformanceSummary",
    "SlippageModel",
    "Split",
    "TransactionCostModel",
    "annualized_return",
    "annualized_volatility",
    "buy_and_hold_equity",
    "buy_and_hold_returns",
    "calmar_ratio",
    "dca_equity",
    "drawdown_series",
    "equity_curve",
    "estimate_half_spread_bps",
    "hit_rate",
    "max_drawdown",
    "max_drawdown_duration",
    "profit_factor",
    "sharpe_ratio",
    "sortino_ratio",
    "split_frame",
    "summarize",
    "time_underwater",
    "total_return",
    "walk_forward_splits",
]
