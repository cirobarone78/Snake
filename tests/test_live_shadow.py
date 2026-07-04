"""Offline tests for the live-shadow runner: fills across runs, idempotency."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.execution.live_shadow import run_daily
from src.execution.scenarios import ScenarioStore
from src.execution.strategy import momentum_target_weights


def _frame(closes: list[float], start: str = "2026-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=len(closes), freq="D", tz="UTC")
    c = np.array(closes, dtype=float)
    return pd.DataFrame(
        {"open": c * 0.999, "high": c * 1.01, "low": c * 0.99, "close": c}, index=idx
    )


def _trending(n: int, up: bool = True, start: str = "2026-01-01") -> pd.DataFrame:
    base = 100 * np.cumprod(1 + (0.01 if up else -0.01) * np.ones(n))
    return _frame(list(base), start=start)


# --- strategy ---


def test_momentum_weights_equal_on_positive() -> None:
    closes = {
        "UP1": _trending(40, up=True)["close"],
        "UP2": _trending(40, up=True)["close"],
        "DOWN": _trending(40, up=False)["close"],
    }
    w = momentum_target_weights(closes, lookback=10)
    assert w["UP1"] == pytest.approx(0.5)
    assert w["UP2"] == pytest.approx(0.5)
    assert w["DOWN"] == 0.0


def test_momentum_all_negative_stays_in_cash() -> None:
    closes = {"A": _trending(40, up=False)["close"], "B": _trending(40, up=False)["close"]}
    w = momentum_target_weights(closes, lookback=10)
    assert all(v == 0.0 for v in w.values())


def test_momentum_short_history_means_no_position() -> None:
    closes = {"NEW": _trending(5, up=True)["close"]}
    w = momentum_target_weights(closes, lookback=10)
    assert w == {"NEW": 0.0}


# --- runner across runs (the cron reality) ---


def test_orders_decided_today_fill_next_run(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    hist_t = {"UP": _trending(40, up=True)}

    # run 1: decide at T -> orders pending, NOTHING fills today
    s1 = run_daily(store, hist_t, lookback=10)
    assert all(v["fills"] == 0 for v in s1.values() if not v.get("skipped"))
    assert any(v["new_orders"] > 0 for v in s1.values() if not v.get("skipped"))
    pending = store.load_pending("mid_10k")
    assert len(pending) == 1

    # run 2: history grows by one bar -> yesterday's order fills at T+1 open
    hist_t1 = {"UP": _trending(41, up=True)}
    s2 = run_daily(store, hist_t1, lookback=10)
    mid = s2["mid_10k"]
    assert mid["fills"] == 1
    assert store.load_pending("mid_10k") == []
    state = store.load("mid_10k")
    assert state.portfolio.positions["UP"].qty > 0
    # fill happened at the T+1 bar's open (recorded in the audit trail)
    orders = store.orders("mid_10k")
    filled = orders[orders["status"] == "filled"]
    assert len(filled) == 1
    t1_open = float(hist_t1["UP"]["open"].iloc[-1])
    assert float(filled["fill_price"].iloc[0]) == pytest.approx(t1_open, rel=1e-3)


def test_rerun_same_day_is_noop(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    hist = {"UP": _trending(40, up=True)}
    run_daily(store, hist, lookback=10)
    s2 = run_daily(store, hist, lookback=10)  # same T again
    assert all(v.get("skipped") for v in s2.values())
    # no duplicate orders, no duplicate equity points
    assert len(store.orders("mid_10k")) == 1
    assert len(store.equity_curve("mid_10k")) == 1


def test_equity_curve_accumulates_across_runs(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    for n in (40, 41, 42):
        run_daily(store, {"UP": _trending(n, up=True)}, lookback=10)
    curve = store.equity_curve("small_1k")
    assert len(curve) == 3
    assert curve.index.is_monotonic_increasing


def test_downtrend_scenario_stays_in_cash(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    s = run_daily(store, {"DOWN": _trending(40, up=False)}, lookback=10)
    for sid, summary in s.items():
        assert summary["new_orders"] == 0, sid  # defensive posture: no orders
        assert summary["targets"] == {}
    state = store.load("large_100k")
    assert state.portfolio.cash == pytest.approx(100_000.0)


def test_min_trade_filter_blocks_fee_churn(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    hist = {"UP": _trending(40, up=True)}
    run_daily(store, hist, lookback=10)          # decide
    run_daily(store, {"UP": _trending(41, up=True)}, lookback=10)  # fill ~100%
    # next run: target unchanged (~1.0), drift is tiny -> no new order
    s3 = run_daily(store, {"UP": _trending(42, up=True)}, lookback=10)
    assert s3["mid_10k"]["new_orders"] == 0
