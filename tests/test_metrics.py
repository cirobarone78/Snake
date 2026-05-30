"""Tests for backtest performance metrics — known curves and edge cases."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.backtest import metrics


def _returns(values: list[float]) -> pd.Series:
    idx = pd.date_range("2020-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=idx)


# A small symmetric saw-tooth: up 10%, down 10%, repeated.
SAW = _returns([0.1, -0.1, 0.1, -0.1])


def test_equity_curve_compounds() -> None:
    eq = metrics.equity_curve(SAW, initial=100.0)
    assert eq.iloc[0] == pytest.approx(110.0)
    assert eq.iloc[1] == pytest.approx(99.0)
    assert eq.iloc[-1] == pytest.approx(98.01)


def test_total_return() -> None:
    assert metrics.total_return(SAW) == pytest.approx(0.9801 - 1.0)


def test_max_drawdown_negative_fraction() -> None:
    # Running peak is 1.1 throughout; deepest trough is the last point.
    assert metrics.max_drawdown(SAW) == pytest.approx(0.9801 / 1.1 - 1.0)


def test_max_drawdown_duration_counts_consecutive_underwater() -> None:
    # Positions 1,2,3 are below the peak set at position 0 → run of 3.
    assert metrics.max_drawdown_duration(SAW) == 3


def test_hit_rate_ignores_flat_periods() -> None:
    r = _returns([0.1, -0.1, 0.0, 0.1])
    # 2 positives out of 3 non-flat periods.
    assert metrics.hit_rate(r) == pytest.approx(2 / 3)


def test_profit_factor() -> None:
    assert metrics.profit_factor(SAW) == pytest.approx(1.0)


def test_profit_factor_no_losses_is_inf() -> None:
    assert metrics.profit_factor(_returns([0.01, 0.02])) == math.inf


def test_time_underwater() -> None:
    assert metrics.time_underwater(SAW) == pytest.approx(0.75)


def test_annualized_volatility_scales_with_sqrt_periods() -> None:
    r = _returns([0.01, -0.01, 0.02, -0.02, 0.0])
    per_period = float(r.std(ddof=1))
    assert metrics.annualized_volatility(r, periods_per_year=365) == pytest.approx(
        per_period * (365**0.5)
    )


def test_sharpe_sign_matches_mean_excess() -> None:
    up = _returns([0.02, 0.01, 0.03, 0.01])
    down = _returns([-0.02, -0.01, -0.03, -0.01])
    assert metrics.sharpe_ratio(up) > 0
    assert metrics.sharpe_ratio(down) < 0


def test_sortino_only_penalizes_downside() -> None:
    # Same mean (0.01/period), but a fatter downside lowers Sortino.
    mild = _returns([0.03, -0.01, 0.03, -0.01])
    severe = _returns([0.05, -0.03, 0.05, -0.03])
    assert metrics.sortino_ratio(mild) > metrics.sortino_ratio(severe)


def test_sortino_nan_when_no_downside() -> None:
    # No returns below target → downside deviation is zero → undefined.
    assert math.isnan(metrics.sortino_ratio(_returns([0.01, 0.02, 0.01, 0.03])))


def test_annualized_return_wiped_out() -> None:
    # A -100% period zeroes the equity curve forever.
    assert metrics.annualized_return(_returns([0.1, -1.0, 0.5])) == pytest.approx(-1.0)


def test_calmar_is_cagr_over_max_dd() -> None:
    expected = metrics.annualized_return(SAW, 365) / abs(metrics.max_drawdown(SAW))
    assert metrics.calmar_ratio(SAW, 365) == pytest.approx(expected)


# --- edge cases ---


def test_zero_volatility_yields_nan_ratios() -> None:
    flat = _returns([0.0, 0.0, 0.0, 0.0])
    assert math.isnan(metrics.sharpe_ratio(flat))
    assert math.isnan(metrics.sortino_ratio(flat))
    assert math.isnan(metrics.hit_rate(flat))  # no non-flat periods
    assert metrics.max_drawdown(flat) == pytest.approx(0.0)
    assert math.isnan(metrics.calmar_ratio(flat))  # zero max-dd guard


def test_all_positive_never_underwater() -> None:
    r = _returns([0.01] * 10)
    assert metrics.max_drawdown(r) == pytest.approx(0.0)
    assert metrics.max_drawdown_duration(r) == 0
    assert metrics.time_underwater(r) == pytest.approx(0.0)
    assert metrics.profit_factor(r) == math.inf


def test_empty_series_is_nan() -> None:
    empty = _returns([])
    assert math.isnan(metrics.total_return(empty))
    assert math.isnan(metrics.max_drawdown(empty))
    assert metrics.max_drawdown_duration(empty) == 0


def test_summarize_bundles_all_metrics() -> None:
    s = metrics.summarize(SAW, periods_per_year=365)
    assert s.n_periods == 4
    assert s.total_return == pytest.approx(metrics.total_return(SAW))
    assert s.max_drawdown == pytest.approx(metrics.max_drawdown(SAW))
    assert s.profit_factor == pytest.approx(1.0)
    # round-trips to a plain dict for reporting/serialization
    d = s.to_dict()
    assert d["n_periods"] == 4
    assert set(d) == {
        "n_periods",
        "total_return",
        "annualized_return",
        "annualized_volatility",
        "sharpe",
        "sortino",
        "max_drawdown",
        "max_drawdown_duration",
        "calmar",
        "hit_rate",
        "profit_factor",
        "time_underwater",
    }
