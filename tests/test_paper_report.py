"""Offline tests for the paper-report builder (the dashboard payload)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.execution.live_shadow import run_daily
from src.execution.report import (
    DISCLAIMER,
    MIN_POINTS_FOR_METRICS,
    build_paper_report,
)
from src.execution.scenarios import ScenarioStore


def _frame(closes: list[float], start: str = "2026-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=len(closes), freq="D", tz="UTC")
    c = np.array(closes, dtype=float)
    return pd.DataFrame(
        {"open": c * 0.999, "high": c * 1.01, "low": c * 0.99, "close": c}, index=idx
    )


def _trending(n: int, up: bool = True) -> pd.DataFrame:
    base = 100 * np.cumprod(1 + (0.01 if up else -0.01) * np.ones(n))
    return _frame(list(base))


def test_report_shape_before_any_run(tmp_path) -> None:
    """Fresh store: scenarios exist at initial cash, no positions, no metrics."""
    store = ScenarioStore(root=tmp_path / "paper")
    from src.execution.scenarios import ensure_default_scenarios

    ensure_default_scenarios(store)
    report = build_paper_report(store, marks={}, generated_at=pd.Timestamp("2026-07-04", tz="UTC"))

    assert report["title"] == "Paper trading"
    assert report["disclaimer"] == DISCLAIMER
    assert report["generated_at"].startswith("2026-07-04")
    assert len(report["scenarios"]) == 3
    by_id = {s["scenario_id"]: s for s in report["scenarios"]}
    small = by_id["small_1k"]
    assert small["initial_cash"] == 1_000.0
    assert small["equity"] == 1_000.0
    assert small["cash"] == 1_000.0
    assert small["return_pct"] == 0.0
    assert small["positions"] == []
    assert small["metrics"] is None
    assert small["curve"] == []
    assert small["recent_orders"] == []
    assert small["fully_marked"] is True  # no positions -> nothing unmarked


def test_report_after_fills_marks_positions(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    run_daily(store, {"UP": _trending(40, up=True)}, lookback=10)  # decide
    run_daily(store, {"UP": _trending(41, up=True)}, lookback=10)  # fill

    price = float(_trending(41, up=True)["close"].iloc[-1])
    report = build_paper_report(store, marks={"UP": price})
    mid = next(s for s in report["scenarios"] if s["scenario_id"] == "mid_10k")

    assert len(mid["positions"]) == 1
    pos = mid["positions"][0]
    assert pos["symbol"] == "UP"
    assert pos["qty"] > 0
    assert pos["price"] == round(price, 4)
    assert pos["value"] is not None
    assert mid["fully_marked"] is True
    # equity moved off the initial 10k once invested and marked
    assert mid["equity"] != 10_000.0
    assert any(o["symbol"] == "UP" for o in mid["recent_orders"])


def test_missing_mark_flags_partial_valuation(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    run_daily(store, {"UP": _trending(40, up=True)}, lookback=10)
    run_daily(store, {"UP": _trending(41, up=True)}, lookback=10)

    report = build_paper_report(store, marks={})  # no price for UP
    mid = next(s for s in report["scenarios"] if s["scenario_id"] == "mid_10k")
    assert mid["fully_marked"] is False
    pos = mid["positions"][0]
    assert pos["price"] is None
    assert pos["value"] is None
    assert pos["pnl_pct"] is None


def test_metrics_appear_only_with_enough_history(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    # fewer than MIN_POINTS_FOR_METRICS runs -> no metrics
    for n in range(40, 40 + MIN_POINTS_FOR_METRICS - 1):
        run_daily(store, {"UP": _trending(n, up=True)}, lookback=10)
    price = float(_trending(43, up=True)["close"].iloc[-1])
    report = build_paper_report(store, marks={"UP": price})
    small = next(s for s in report["scenarios"] if s["scenario_id"] == "small_1k")
    assert small["metrics"] is None

    # cross the threshold -> metrics present with the expected keys
    for n in range(40 + MIN_POINTS_FOR_METRICS - 1, 40 + MIN_POINTS_FOR_METRICS + 2):
        run_daily(store, {"UP": _trending(n, up=True)}, lookback=10)
    report2 = build_paper_report(store, marks={"UP": price})
    small2 = next(s for s in report2["scenarios"] if s["scenario_id"] == "small_1k")
    assert small2["metrics"] is not None
    assert set(small2["metrics"]) == {"sharpe", "max_drawdown_pct", "time_underwater_pct", "n_days"}
    assert len(small2["curve"]) >= MIN_POINTS_FOR_METRICS
