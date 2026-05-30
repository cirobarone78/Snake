"""Baseline forecasting models (Fase 2).

The point of a baseline is to be the bar every later model must clear. Per
CLAUDE.md, a single backtest proves nothing; these naive forecasters are the
null hypotheses against which any "real" signal must show out-of-sample edge.

Two baselines here (ARIMA, the third in ROADMAP Fase 2, lands once
``statsmodels`` is added — kept out for now to avoid a heavy dependency):

- **Random walk**: the martingale null. Best guess for next return is zero
  (price is a random walk → no exploitable drift). It is the "do nothing"
  forecast; a strategy built on it never takes a position.
- **Momentum**: drift persists. Forecast next return as the trailing mean of
  realized returns over a lookback window.

Causality contract (no look-ahead, CLAUDE.md non-negotiable): a forecast
``f[t]`` for the return realized at ``t`` uses only returns strictly *before*
``t``. So ``f[t]`` is knowable at the close of ``t-1`` and a position taken on
it legitimately earns ``return[t]`` — no shifting needed downstream.

Asset-class-agnostic (ADR-014): lookbacks are in observations; nothing here
assumes a calendar.
"""

from __future__ import annotations

from typing import cast

import pandas as pd

from src.backtest.costs import TransactionCostModel


def returns_from_prices(prices: pd.Series) -> pd.Series:
    """Periodic simple returns from a price series (drops the undefined t0)."""
    return cast("pd.Series", prices.dropna().pct_change()).dropna()


def random_walk_forecast(returns: pd.Series) -> pd.Series:
    """Martingale null: predict zero return for every period.

    Returned series is aligned to ``returns`` and filled with 0.0 — the
    forecast carries no information by construction. This is the bar momentum
    (and later ARIMA) must beat on directional accuracy and forecast error.
    """
    return pd.Series(0.0, index=returns.index, name="rw_forecast")


def momentum_forecast(returns: pd.Series, lookback: int = 30) -> pd.Series:
    """Predict next return as the trailing mean of the last ``lookback`` returns.

    ``f[t] = mean(returns[t-lookback : t])`` — the ``shift(1)`` makes the
    window end at ``t-1``, so ``f[t]`` never sees ``return[t]``. Leading
    positions where the window is not yet full are ``NaN``.
    """
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    rolling_mean = cast("pd.Series", returns.rolling(lookback).mean())
    trailing = rolling_mean.shift(1)
    return cast("pd.Series", trailing).rename(f"mom_forecast_{lookback}")


def signal_from_forecast(forecast: pd.Series, long_only: bool = True) -> pd.Series:
    """Map a return forecast to a position in {-1, 0, +1} by its sign.

    ``long_only`` (default) clips shorts to flat — the realistic constraint
    for the spot-only implementation phase (no shorting on the venues in
    ADR-012). NaN forecasts (warm-up) become flat (0).
    """
    f = forecast.fillna(0.0)
    pos = f.gt(0.0).astype(float) - f.lt(0.0).astype(float)
    if long_only:
        pos = pos.clip(lower=0.0)
    return cast("pd.Series", pos).rename("position")


def strategy_returns(
    positions: pd.Series,
    asset_returns: pd.Series,
    cost_model: TransactionCostModel | None = None,
) -> pd.Series:
    """Net periodic returns of holding ``positions`` against ``asset_returns``.

    ``positions[t]`` is decided at the close of ``t-1`` (the forecast is
    causal) and earns ``asset_returns[t]`` — so no shift is applied here; the
    causality lives in how the forecast/position was built.

    When a ``cost_model`` is given, turnover is charged: at each period the
    traded notional is ``|positions[t] - positions[t-1]|`` (entering from flat
    at the start), and the cost rate per unit notional is taken as
    ``cost_model.cost(1.0)`` (fee + slippage floor). The cost is subtracted
    from that period's return. Positions are interpreted as fractions of a
    unit notional, so returns and costs share the same scale.
    """
    pos, ret = positions.align(asset_returns, join="inner")
    gross = pos * ret
    if cost_model is None:
        return cast("pd.Series", gross.dropna()).rename("strategy_return")

    # Turnover: |Δposition|, with the first period entering from flat (0).
    turnover = pos.diff()
    turnover.iloc[0] = pos.iloc[0]
    cost_rate = cost_model.cost(1.0)
    net = gross - turnover.abs() * cost_rate
    return cast("pd.Series", net.dropna()).rename("strategy_return")


def directional_accuracy(forecast: pd.Series, realized: pd.Series) -> float:
    """Fraction of periods where ``sign(forecast)`` matches ``sign(realized)``.

    Periods where either side is zero or NaN are excluded (a zero forecast —
    e.g. the random walk — makes no directional call). Returns NaN if there
    are no decidable periods.
    """
    f, r = forecast.align(realized, join="inner")
    f_sign = f.gt(0.0).astype(int) - f.lt(0.0).astype(int)
    r_sign = r.gt(0.0).astype(int) - r.lt(0.0).astype(int)
    decidable = cast("pd.Series", (f_sign != 0) & (r_sign != 0))
    n = int(decidable.sum())
    if n == 0:
        return float("nan")
    hits = int(cast("pd.Series", (f_sign == r_sign) & decidable).sum())
    return hits / n


def mean_absolute_error(forecast: pd.Series, realized: pd.Series) -> float:
    """MAE between forecast and realized returns over their common index."""
    f, r = forecast.align(realized, join="inner")
    err = (f - r).abs().dropna()
    if err.empty:
        return float("nan")
    return float(err.mean())
