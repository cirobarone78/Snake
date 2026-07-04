"""Offline tests for the replay engine: same-code-path history, consistency."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.execution.live_shadow import run_daily
from src.execution.replay import (
    REPLAY_DISCLAIMER,
    _decision_bars,
    build_replay_report,
    replay_into,
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


def test_decision_bars_skip_the_lookback_warmup() -> None:
    hist = {"A": _trending(40), "B": _trending(40)}
    bars = _decision_bars(hist, lookback=10)
    # 40 common bars, first 11 (lookback+1) are warm-up
    assert len(bars) == 40 - 11
    assert bars.is_monotonic_increasing


def test_replay_uptrend_invests_and_gains(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    hist = {"UP": _trending(60, up=True)}
    replay_into(store, hist, initial_cash=10_000.0, lookback=10)

    curve = store.equity_curve("replay")
    assert len(curve) == len(_decision_bars(hist, lookback=10))
    assert curve.index.is_monotonic_increasing
    state = store.load("replay")
    assert state.portfolio.positions.get("UP") is not None  # ended invested
    assert float(curve.iloc[-1]) > 10_000.0  # rode the uptrend


def test_replay_downtrend_stays_in_cash(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    hist = {"DOWN": _trending(60, up=False)}
    replay_into(store, hist, initial_cash=10_000.0, lookback=10)

    state = store.load("replay")
    assert state.portfolio.positions == {}  # never bought a falling asset
    assert state.portfolio.cash == pytest.approx(10_000.0)


def test_replay_matches_daily_stepped_live_run(tmp_path) -> None:
    """Replay is the live cron run bar-by-bar: same equity curve, same code."""
    hist = {"UP": _trending(55, up=True), "DOWN": _trending(55, up=False)}

    # replay drives a single "replay" scenario at 10k
    rstore = ScenarioStore(root=tmp_path / "replay")
    replay_into(rstore, hist, initial_cash=10_000.0, lookback=10)

    # live: step the default mid_10k (also 10k) over the SAME decision bars,
    # feeding a growing slice each "day" exactly like the cron would
    lstore = ScenarioStore(root=tmp_path / "live")
    for t in _decision_bars(hist, lookback=10):
        window = {s: df.loc[:t] for s, df in hist.items()}
        run_daily(lstore, window, lookback=10, scenario_ids=None)  # ensures defaults

    rcurve = rstore.equity_curve("replay")
    lcurve = lstore.equity_curve("mid_10k")
    assert list(rcurve.index) == list(lcurve.index)
    np.testing.assert_allclose(rcurve.to_numpy(), lcurve.to_numpy(), rtol=1e-9)


def test_build_replay_report_shape(tmp_path) -> None:
    hist = {"UP": _trending(60, up=True)}
    report = build_replay_report(
        hist, lookback=10, generated_at=pd.Timestamp("2026-07-04", tz="UTC")
    )
    assert report["title"] == "Replay storico"
    assert report["disclaimer"] == REPLAY_DISCLAIMER
    assert report["lookback"] == 10
    assert report["symbols"] == ["UP"]
    sc = report["scenario"]
    assert sc["scenario_id"] == "replay"
    assert sc["initial_cash"] == 10_000.0
    assert len(sc["curve"]) == len(_decision_bars(hist, lookback=10))
    # enough bars -> Fase 2 metrics are present
    assert sc["metrics"] is not None
    assert set(sc["metrics"]) == {"sharpe", "max_drawdown_pct", "time_underwater_pct", "n_days"}
