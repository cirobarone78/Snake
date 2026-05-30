"""Performance metrics for strategy and benchmark equity curves (Fase 2).

All functions operate on a pandas Series of **periodic simple returns**
(not log returns): ``r_t = P_t / P_{t-1} - 1``. Simple returns compound
multiplicatively into an equity curve, which is what drawdown, Sharpe,
Calmar and friends all assume. Convert log returns with ``expm1`` before
feeding them here if needed.

Asset-class-agnostic (ADR-014): annualization is parameterized by
``periods_per_year``. Crypto trades 24/7 (365 daily periods); equity
markets trade ~252 days/year. The default (365) reflects the crypto-first
implementation phase — it is an overridable default, not a hardcoded
assumption. Pass the right value for the asset class and frequency.

These functions only *summarize* a realized return stream. The no-look-ahead
guarantee is a property of how that stream is generated (see
``src.backtest.splits``), not of the metrics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

# Periods-per-year conventions for the common frequencies.
DAILY_CRYPTO = 365
DAILY_EQUITY = 252
WEEKLY = 52
MONTHLY = 12

DEFAULT_PERIODS_PER_YEAR = DAILY_CRYPTO

_NAN = float("nan")


def _clean(returns: pd.Series) -> pd.Series:
    """Drop NaNs; the first return of any series is typically undefined."""
    return returns.dropna()


def equity_curve(returns: pd.Series, initial: float = 1.0) -> pd.Series:
    """Compound periodic simple returns into a wealth index.

    ``initial`` is the starting capital (1.0 → normalized curve). The result
    is aligned to ``returns`` (it does not prepend the t0 starting point).
    """
    r = _clean(returns)
    return pd.Series(initial * (1.0 + r).cumprod(), index=r.index)


def total_return(returns: pd.Series) -> float:
    """Cumulative return over the whole sample."""
    r = _clean(returns)
    if r.empty:
        return _NAN
    return float((1.0 + r).prod() - 1.0)


def annualized_return(
    returns: pd.Series, periods_per_year: int = DEFAULT_PERIODS_PER_YEAR
) -> float:
    """Geometric annualized return (CAGR) implied by the realized sample."""
    r = _clean(returns)
    n = len(r)
    if n == 0:
        return _NAN
    growth = float((1.0 + r).prod())
    if growth <= 0.0:
        return -1.0  # capital fully wiped out
    return growth ** (periods_per_year / n) - 1.0


def annualized_volatility(
    returns: pd.Series, periods_per_year: int = DEFAULT_PERIODS_PER_YEAR
) -> float:
    """Annualized standard deviation of returns (sample std, ddof=1)."""
    r = _clean(returns)
    if len(r) < 2:
        return _NAN
    sd = float(r.std(ddof=1))
    return sd * (periods_per_year**0.5)


def sharpe_ratio(
    returns: pd.Series,
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR,
    risk_free: float = 0.0,
) -> float:
    """Annualized Sharpe ratio.

    ``risk_free`` is an *annual* rate; it is converted to a per-period rate
    linearly. Returns NaN when volatility is zero or the sample is too short.
    """
    r = _clean(returns)
    if len(r) < 2:
        return _NAN
    excess = r - risk_free / periods_per_year
    sd = float(excess.std(ddof=1))
    if sd == 0.0:
        return _NAN
    return float(excess.mean()) / sd * (periods_per_year**0.5)


def sortino_ratio(
    returns: pd.Series,
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR,
    risk_free: float = 0.0,
) -> float:
    """Annualized Sortino ratio (downside-deviation denominator).

    Penalizes only returns below the per-period target (``risk_free`` split
    across periods). Downside deviation is the root-mean-square of the
    negative excess returns over the *whole* sample.
    """
    r = _clean(returns)
    if len(r) < 2:
        return _NAN
    target = risk_free / periods_per_year
    excess = r - target
    downside = excess.clip(upper=0.0)
    downside_dev = float((downside**2).mean()) ** 0.5
    if downside_dev == 0.0:
        return _NAN
    return float(excess.mean()) / downside_dev * (periods_per_year**0.5)


def drawdown_series(returns: pd.Series) -> pd.Series:
    """Per-period drawdown: fractional distance below the running peak (<= 0)."""
    eq = equity_curve(returns)
    if len(eq) == 0:
        return eq
    peak = eq.cummax()
    return pd.Series(eq / peak - 1.0, index=eq.index)


def max_drawdown(returns: pd.Series) -> float:
    """Worst peak-to-trough drawdown, returned as a negative fraction."""
    r = _clean(returns)
    if r.empty:
        return _NAN
    dd: pd.Series = drawdown_series(r)
    return float(dd.min())


def max_drawdown_duration(returns: pd.Series) -> int:
    """Longest run of consecutive underwater periods (peak not yet recovered)."""
    r = _clean(returns)
    if r.empty:
        return 0
    underwater = drawdown_series(r) < 0
    max_run = 0
    run = 0
    for is_underwater in underwater:
        run = run + 1 if is_underwater else 0
        max_run = max(max_run, run)
    return max_run


def calmar_ratio(
    returns: pd.Series, periods_per_year: int = DEFAULT_PERIODS_PER_YEAR
) -> float:
    """CAGR divided by the magnitude of the max drawdown."""
    mdd = max_drawdown(returns)
    if mdd != mdd or mdd == 0.0:  # NaN guard + flat-curve guard
        return _NAN
    return annualized_return(returns, periods_per_year) / abs(mdd)


def hit_rate(returns: pd.Series) -> float:
    """Fraction of *non-flat* periods that were positive.

    Flat (exactly zero) periods are excluded from the denominator so that
    long stretches of no-position do not inflate or deflate the rate.
    """
    r = _clean(returns)
    nonzero = r[r != 0.0]
    if len(nonzero) == 0:
        return _NAN
    return float((nonzero > 0.0).mean())


def profit_factor(returns: pd.Series) -> float:
    """Gross gains divided by gross losses (absolute).

    Returns ``inf`` if there are gains but no losses, NaN if neither.
    """
    r = _clean(returns)
    gains = float(r[r > 0.0].sum())
    losses = float(-r[r < 0.0].sum())
    if losses == 0.0:
        return float("inf") if gains > 0.0 else _NAN
    return gains / losses


def time_underwater(returns: pd.Series) -> float:
    """Fraction of periods spent below the prior equity peak."""
    r = _clean(returns)
    if r.empty:
        return _NAN
    return float((drawdown_series(r) < 0).mean())


@dataclass(frozen=True)
class PerformanceSummary:
    """All headline metrics for one return stream. See module docstring."""

    n_periods: int
    total_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe: float
    sortino: float
    max_drawdown: float
    max_drawdown_duration: int
    calmar: float
    hit_rate: float
    profit_factor: float
    time_underwater: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def summarize(
    returns: pd.Series,
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR,
    risk_free: float = 0.0,
) -> PerformanceSummary:
    """Compute every metric in one pass, returning a ``PerformanceSummary``."""
    r = _clean(returns)
    return PerformanceSummary(
        n_periods=len(r),
        total_return=total_return(r),
        annualized_return=annualized_return(r, periods_per_year),
        annualized_volatility=annualized_volatility(r, periods_per_year),
        sharpe=sharpe_ratio(r, periods_per_year, risk_free),
        sortino=sortino_ratio(r, periods_per_year, risk_free),
        max_drawdown=max_drawdown(r),
        max_drawdown_duration=max_drawdown_duration(r),
        calmar=calmar_ratio(r, periods_per_year),
        hit_rate=hit_rate(r),
        profit_factor=profit_factor(r),
        time_underwater=time_underwater(r),
    )
