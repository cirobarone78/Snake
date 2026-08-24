"""Offline tests for the weekly ETF rotation: weights, fills, idempotency.

The rule itself is trivial by design (ADR-034 left nothing else standing), so
what these tests defend is the machinery around it: the 20% cap, the disabled
D7 threshold and its still-working mechanism, orders that cannot fill before
they exist, and a re-run that changes nothing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.execution.etf_rotation import (
    MAX_WEIGHT,
    SCENARIO_CAPITAL,
    SCENARIO_ID,
    TOP_N,
    decide_from_panel,
    rank_universe,
    run_weekly,
    target_weights,
    to_predictions,
)
from src.execution.scenarios import ScenarioStore


def _bars(closes: list[float], start: str = "2026-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=len(closes), freq="D", tz="UTC")
    c = np.array(closes, dtype=float)
    return pd.DataFrame(
        {"open": c, "high": c * 1.001, "low": c * 0.999, "close": c}, index=idx
    )


def _flat_history(symbols: list[str], n: int = 10, price: float = 100.0) -> dict[str, pd.DataFrame]:
    """Flat prices: any equity change then comes from trading, not from the market."""
    return {s: _bars([price] * n) for s in symbols}


def _panel(scores: dict[str, float], date: str = "2026-08-24", regime: str = "bull_low_vol",
           extra_date: str | None = "2026-08-17") -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    dates = [d for d in (extra_date, date) if d is not None]
    for d in dates:
        for symbol, score in scores.items():
            rows.append(
                {
                    "date": pd.Timestamp(d, tz="UTC"),
                    "symbol": symbol,
                    "close": 100.0,
                    # the older cross-section carries deliberately opposite scores,
                    # so a decision that leaked into it would rank backwards
                    "rel_ret_60": score if d == date else -score,
                    "vol_60": 0.2,
                    "regime": regime,
                }
            )
    return pd.DataFrame(rows)


# --- weights: D6 cap, and D7 disabled (ADR-036) -----------------------------


def test_top_five_equal_weight_at_the_cap() -> None:
    scores = {f"S{i}": float(i) for i in range(10)}
    weights = target_weights(scores)
    assert len(weights) == TOP_N
    assert set(weights) == {"S9", "S8", "S7", "S6", "S5"}
    assert all(w == pytest.approx(MAX_WEIGHT) for w in weights.values())
    assert sum(weights.values()) == pytest.approx(1.0)


def test_no_single_weight_exceeds_the_cap_even_with_few_names() -> None:
    """Three names do not become 33% each: the cap binds, the rest is cash."""
    weights = target_weights({"A": 3.0, "B": 2.0, "C": 1.0})
    assert all(w <= MAX_WEIGHT + 1e-12 for w in weights.values())
    assert sum(weights.values()) == pytest.approx(0.6)


def test_missing_scores_are_not_ranked() -> None:
    weights = target_weights({"A": 1.0, "B": float("nan"), "C": 0.5})
    assert set(weights) == {"A", "C"}


def test_ties_break_on_symbol_so_the_portfolio_is_deterministic() -> None:
    scores = {"D": 1.0, "A": 1.0, "C": 1.0, "B": 1.0, "E": 1.0, "F": 1.0}
    first = target_weights(scores, top_n=3)
    second = target_weights(dict(reversed(list(scores.items()))), top_n=3)
    assert first == second
    assert set(first) == {"A", "B", "C"}
    # the 20% cap still binds: three equal names are 20% each, not 33%
    assert all(w == pytest.approx(MAX_WEIGHT) for w in first.values())


def test_confidence_threshold_is_off_by_default() -> None:
    """ADR-036: with no calibrated probability there is nothing to threshold."""
    scores = {f"S{i}": float(i) for i in range(10)}
    assert len(target_weights(scores)) == TOP_N


def test_confidence_threshold_still_works_when_a_model_supplies_probabilities() -> None:
    """The D7 mechanism survives for the day a model passes the adoption bar."""
    scores = {"A": 5.0, "B": 4.0, "C": 3.0}
    probs = {"A": 0.61, "B": 0.52, "C": 0.58}
    weights = target_weights(
        scores, top_n=3, probabilities=probs, confidence_threshold=0.55
    )
    assert set(weights) == {"A", "C"}  # B falls below the threshold -> partial cash
    assert sum(weights.values()) == pytest.approx(2 * MAX_WEIGHT)


def test_confidence_threshold_without_probabilities_is_an_error() -> None:
    with pytest.raises(ValueError, match="requires probabilities"):
        target_weights({"A": 1.0}, confidence_threshold=0.55)


def test_threshold_above_everything_leaves_full_cash() -> None:
    weights = target_weights(
        {"A": 1.0, "B": 2.0}, probabilities={"A": 0.4, "B": 0.3}, confidence_threshold=0.55
    )
    assert weights == {}


def test_invalid_parameters_are_rejected() -> None:
    with pytest.raises(ValueError):
        target_weights({"A": 1.0}, top_n=0)
    with pytest.raises(ValueError):
        target_weights({"A": 1.0}, max_weight=1.5)


# --- the ranked cross-section ------------------------------------------------


def test_rank_universe_returns_everything_not_only_the_holdings() -> None:
    ranked = rank_universe({f"S{i}": float(i) for i in range(8)})
    assert len(ranked) == 8
    assert [a.rank for a in ranked] == list(range(1, 9))
    assert ranked[0].symbol == "S7"
    assert sum(1 for a in ranked if a.selected) == TOP_N


def test_rank_pct_puts_the_leader_at_one() -> None:
    ranked = rank_universe({"A": 3.0, "B": 2.0, "C": 1.0, "D": 0.0})
    assert ranked[0].rank_pct == pytest.approx(1.0)
    assert ranked[-1].rank_pct == pytest.approx(0.25)


def test_decide_reads_only_the_latest_cross_section() -> None:
    panel = _panel({"A": 0.05, "B": 0.03, "C": -0.01})
    decision = decide_from_panel(panel)
    assert str(decision.as_of.date()) == "2026-08-24"
    assert [a.symbol for a in decision.ranked] == ["A", "B", "C"]
    assert decision.regime == "bull_low_vol"
    assert decision.predictive is False


def test_decide_records_symbols_it_could_not_score() -> None:
    panel = _panel({"A": 0.05, "B": float("nan")}, extra_date=None)
    decision = decide_from_panel(panel)
    assert decision.excluded == ["B"]
    assert [a.symbol for a in decision.ranked] == ["A"]


def test_decide_on_an_empty_panel_is_an_error() -> None:
    with pytest.raises(ValueError):
        decide_from_panel(pd.DataFrame())


def test_cash_weight_reflects_the_uninvested_share() -> None:
    decision = decide_from_panel(_panel({"A": 0.05, "B": 0.03}, extra_date=None))
    assert decision.cash_weight == pytest.approx(0.6)


# --- ledger rows built from a decision --------------------------------------


def test_predictions_cover_the_universe_at_both_horizons() -> None:
    decision = decide_from_panel(_panel({f"S{i}": float(i) for i in range(8)}, extra_date=None))
    rows = to_predictions(decision, emitted_at=pd.Timestamp("2026-08-24T07:00:00Z"))
    assert len(rows) == 8 * 2
    assert {r.horizon_days for r in rows} == {20, 60}


def test_prediction_rows_carry_no_forecast_under_the_fallback() -> None:
    decision = decide_from_panel(_panel({"A": 0.05, "B": 0.01}, extra_date=None))
    for row in to_predictions(decision, emitted_at=pd.Timestamp("2026-08-24T07:00:00Z")):
        assert row.predictive is False
        assert row.probability_outperform is None
        assert row.expected_excess_return is None
        assert row.expected_volatility is None
        assert row.confidence == "not_applicable"
        assert row.non_predictive_reason is not None
        assert "ADR-034" in row.non_predictive_reason


def test_prediction_cutoff_is_the_decision_bar_not_the_emission_time() -> None:
    decision = decide_from_panel(_panel({"A": 0.05}, extra_date=None))
    rows = to_predictions(decision, emitted_at=pd.Timestamp("2026-08-25T07:00:00Z"))
    assert rows[0].data_cutoff.startswith("2026-08-24")
    assert rows[0].emitted_at.startswith("2026-08-25")


# --- the runner: fills, idempotency, costs -----------------------------------


def _decision_for(history: dict[str, pd.DataFrame], scores: dict[str, float], date: str):
    return decide_from_panel(_panel(scores, date=date, extra_date=None))


def test_orders_decided_now_do_not_fill_now(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    history = _flat_history(["A", "B"], n=6)
    t = history["A"].index[-1]
    decision = _decision_for(history, {"A": 0.05, "B": 0.02}, str(t.date()))

    summary = run_weekly(store, history, decision)
    assert summary["fills"] == 0
    assert summary["new_orders"] == 2
    assert store.load(SCENARIO_ID).portfolio.cash == pytest.approx(SCENARIO_CAPITAL)
    assert len(store.load_pending(SCENARIO_ID)) == 2


def test_fill_timestamp_is_strictly_after_the_decision(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    history = _flat_history(["A", "B"], n=6)
    t0 = history["A"].index[-1]
    run_weekly(store, history, _decision_for(history, {"A": 0.05, "B": 0.02}, str(t0.date())))

    grown = _flat_history(["A", "B"], n=11)
    t1 = grown["A"].index[-1]
    run_weekly(store, grown, _decision_for(grown, {"A": 0.05, "B": 0.02}, str(t1.date())))

    orders = store.orders(SCENARIO_ID)
    filled = orders[orders["status"] == "filled"]
    assert len(filled) == 2
    for _, row in filled.iterrows():
        assert pd.Timestamp(row["filled_at"]) > pd.Timestamp(row["created_at"])


def test_rerunning_the_same_decision_date_is_a_no_op(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    history = _flat_history(["A", "B"], n=6)
    t = history["A"].index[-1]
    decision = _decision_for(history, {"A": 0.05, "B": 0.02}, str(t.date()))

    first = run_weekly(store, history, decision)
    orders_before = len(store.orders(SCENARIO_ID))
    second = run_weekly(store, history, decision)

    assert first.get("skipped") is not True
    assert second["skipped"] is True
    assert len(store.orders(SCENARIO_ID)) == orders_before


def test_a_stable_signal_produces_no_new_orders_on_the_next_run(tmp_path) -> None:
    """Second run, same targets, already filled: nothing left to trade."""
    store = ScenarioStore(root=tmp_path / "paper")
    scores = {"A": 0.05, "B": 0.02}
    history = _flat_history(["A", "B"], n=6)
    run_weekly(store, history, _decision_for(history, scores, str(history["A"].index[-1].date())))

    grown = _flat_history(["A", "B"], n=11)
    run_weekly(store, grown, _decision_for(grown, scores, str(grown["A"].index[-1].date())))

    third = _flat_history(["A", "B"], n=16)
    summary = run_weekly(store, third, _decision_for(third, scores, str(third["A"].index[-1].date())))
    assert summary["fills"] == 0
    assert summary["new_orders"] == 0


def test_costs_are_charged_once_per_fill(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    scores = {"A": 0.05}
    history = _flat_history(["A"], n=6)
    run_weekly(store, history, _decision_for(history, scores, str(history["A"].index[-1].date())))
    grown = _flat_history(["A"], n=11)
    run_weekly(store, grown, _decision_for(grown, scores, str(grown["A"].index[-1].date())))

    fees_after_fill = store.load(SCENARIO_ID).portfolio.fees_paid
    assert fees_after_fill > 0

    orders = store.orders(SCENARIO_ID)
    filled = orders[orders["status"] == "filled"]
    assert len(filled) == 1
    assert float(filled["fee_paid"].sum()) == pytest.approx(fees_after_fill)

    # a further run with the same signal must not re-charge anything
    third = _flat_history(["A"], n=16)
    run_weekly(store, third, _decision_for(third, scores, str(third["A"].index[-1].date())))
    assert store.load(SCENARIO_ID).portfolio.fees_paid == pytest.approx(fees_after_fill)


def test_target_weights_are_respected_after_the_fill(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    scores = {f"S{i}": float(i) for i in range(8)}
    symbols = list(scores)
    history = _flat_history(symbols, n=6)
    run_weekly(store, history, _decision_for(history, scores, str(history[symbols[0]].index[-1].date())))
    grown = _flat_history(symbols, n=11)
    run_weekly(store, grown, _decision_for(grown, scores, str(grown[symbols[0]].index[-1].date())))

    state = store.load(SCENARIO_ID)
    marks = {s: 100.0 for s in symbols}
    equity = state.portfolio.equity(marks)
    assert set(state.portfolio.positions) == {"S7", "S6", "S5", "S4", "S3"}
    for symbol, pos in state.portfolio.positions.items():
        share = pos.qty * marks[symbol] / equity
        assert share <= MAX_WEIGHT + 1e-6, symbol


def test_a_dropped_name_is_sold_on_the_next_decision(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    symbols = ["A", "B"]
    history = _flat_history(symbols, n=6)
    run_weekly(store, history, _decision_for(history, {"A": 0.05, "B": 0.04}, str(history["A"].index[-1].date())))
    grown = _flat_history(symbols, n=11)
    run_weekly(store, grown, _decision_for(grown, {"A": 0.05, "B": 0.04}, str(grown["A"].index[-1].date())))
    assert set(store.load(SCENARIO_ID).portfolio.positions) == {"A", "B"}

    # B disappears from the ranking: a SELL must be submitted for it
    third = _flat_history(symbols, n=16)
    run_weekly(store, third, _decision_for(third, {"A": 0.05, "B": float("nan")}, str(third["A"].index[-1].date())))
    pending = store.load_pending(SCENARIO_ID)
    assert [(o.symbol, o.side.value) for o in pending] == [("B", "sell")]


def test_equity_curve_gets_one_point_per_run(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    history = _flat_history(["A"], n=6)
    run_weekly(store, history, _decision_for(history, {"A": 0.05}, str(history["A"].index[-1].date())))
    grown = _flat_history(["A"], n=11)
    run_weekly(store, grown, _decision_for(grown, {"A": 0.05}, str(grown["A"].index[-1].date())))
    assert len(store.equity_curve(SCENARIO_ID)) == 2


def test_empty_history_is_an_error(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    decision = decide_from_panel(_panel({"A": 0.05}, extra_date=None))
    with pytest.raises(ValueError):
        run_weekly(store, {}, decision)
