"""Passive benchmarks: buy-and-hold and DCA (Fase 2).

A strategy is only interesting relative to what you'd get by doing (almost)
nothing. Two canonical baselines:

- Buy-and-hold: invest everything at t0 and hold to the end.
- DCA (dollar-cost averaging): invest a fixed amount at a fixed cadence,
  regardless of price. This mirrors the user's real-world behaviour
  (ADR-004: ~100 EUR/month) and, per education chapter L1.06, is the
  benchmark that actually matters when Fase 6 arrives — beating buy-and-hold
  is not enough, the monthly DCA must be beaten too.

Both produce equity curves directly comparable with strategy equity curves,
so the same metrics (``src.backtest.metrics``) apply uniformly. Inputs are
price Series with a chronological index; nothing here assumes a calendar
(ADR-014), so the ``every`` cadence is expressed in observations.
"""

from __future__ import annotations

import pandas as pd


def buy_and_hold_equity(prices: pd.Series, initial_capital: float = 1.0) -> pd.Series:
    """Equity curve of investing ``initial_capital`` fully at the first price."""
    p = prices.dropna()
    if p.empty:
        return p.astype(float)
    units = initial_capital / float(p.iloc[0])
    return units * p


def buy_and_hold_returns(prices: pd.Series) -> pd.Series:
    """Periodic simple returns of holding the asset (drops the undefined t0)."""
    return prices.dropna().pct_change().dropna()


def dca_equity(
    prices: pd.Series,
    contribution: float,
    every: int = 30,
) -> pd.DataFrame:
    """Simulate dollar-cost averaging over a price series.

    A fixed ``contribution`` buys units at every ``every``-th observation,
    starting at the first one (position 0). Purchases happen *at* the
    observed price — there is no look-ahead because each buy uses only the
    price available at that instant.

    Returns a DataFrame indexed like ``prices`` with columns:
    - ``invested``: cumulative cash put in
    - ``units``: cumulative units held
    - ``equity``: mark-to-market value of the holding

    To obtain a returns stream for the metrics module, use
    ``df["equity"].pct_change().dropna()``.
    """
    if contribution <= 0:
        raise ValueError("contribution must be positive")
    if every <= 0:
        raise ValueError("every must be positive")

    p = prices.dropna()
    if p.empty:
        return pd.DataFrame(
            {"invested": [], "units": [], "equity": []}, index=p.index
        ).astype(float)

    units = 0.0
    invested = 0.0
    invested_hist: list[float] = []
    units_hist: list[float] = []
    equity_hist: list[float] = []

    for i, price in enumerate(p):
        if i % every == 0:
            units += contribution / float(price)
            invested += contribution
        invested_hist.append(invested)
        units_hist.append(units)
        equity_hist.append(units * float(price))

    return pd.DataFrame(
        {"invested": invested_hist, "units": units_hist, "equity": equity_hist},
        index=p.index,
    )
