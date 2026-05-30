"""Predictive models (Fase 2).

Baseline forecasters (random walk, momentum) live in ``baseline``; they are
the null hypotheses any later model must beat out-of-sample (CLAUDE.md).
"""

from __future__ import annotations

from src.models.baseline import (
    directional_accuracy,
    mean_absolute_error,
    momentum_forecast,
    random_walk_forecast,
    returns_from_prices,
    signal_from_forecast,
    strategy_returns,
)

__all__ = [
    "directional_accuracy",
    "mean_absolute_error",
    "momentum_forecast",
    "random_walk_forecast",
    "returns_from_prices",
    "signal_from_forecast",
    "strategy_returns",
]
