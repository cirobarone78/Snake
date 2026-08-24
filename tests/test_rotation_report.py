"""Contract tests for the WP4 dashboard payloads (the WP5 renderer's input).

The schema assertions here are not decoration. A payload that quietly drops
``predictive: false``, or that starts carrying a number in
``probability_outperform``, would let the dashboard present a rule already
measured as indistinguishable from chance as if it were a forecast. That is the
one failure mode ADR-034 and ADR-036 exist to prevent, so it is a test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.execution.etf_rotation import SCENARIO_CAPITAL, decide_from_panel, to_predictions
from src.execution.prediction_ledger import PredictionLedger
from src.execution.rotation_report import (
    STATUS_OK,
    STATUS_STALE,
    benchmark_summary,
    ledger_scoreboard,
    past_predictions,
    rotation_model_dict,
    rotation_report_dict,
)

GENERATED_AT = "2026-08-24T07:00:00+00:00"

REPORT_REQUIRED_KEYS = {
    "generated_at", "title", "status", "status_reason", "stale_notice", "predictive",
    "rule", "rule_version", "rule_description", "non_predictive_notice",
    "non_predictive_reason", "confidence_threshold", "confidence_threshold_note",
    "disclaimer", "as_of", "benchmark", "regime", "horizons", "universe_size",
    "not_scoreable", "cash_weight", "items", "past_predictions",
}
ITEM_REQUIRED_KEYS = {
    "rank", "asset", "ticker", "name", "selected", "target_weight", "selection_score",
    "selection_rank_pct", "realized_vol_60", "close", "regime",
    "probability_outperform", "expected_excess_return", "expected_volatility",
    "confidence", "top_factors", "freshness_days",
}
MODEL_REQUIRED_KEYS = {
    "generated_at", "title", "status", "status_reason", "predictive", "model_adopted",
    "rule", "rule_version", "rule_description", "dataset_version",
    "non_predictive_notice", "non_predictive_reason", "adoption_bar", "calibration",
    "confidence_threshold", "confidence_threshold_note", "validation", "scenario",
    "benchmarks", "freshness", "scoreboard", "ledger", "disclaimer",
}


def _panel(scores: dict[str, float], date: str = "2026-08-24") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp(date, tz="UTC"),
                "symbol": symbol,
                "close": 100.0,
                "rel_ret_60": score,
                "vol_60": 0.2,
                "regime": "bull_low_vol",
            }
            for symbol, score in scores.items()
        ]
    )


def _decision(n: int = 8):
    return decide_from_panel(_panel({f"S{i}": float(i) / 100 for i in range(n)}))


def _series(values: list[float], start: str = "2026-01-01") -> pd.Series:
    idx = pd.date_range(start, periods=len(values), freq="D", tz="UTC")
    return pd.Series(np.array(values, dtype=float), index=idx)


# --- the opportunities payload ----------------------------------------------


def test_report_payload_has_the_full_contract(tmp_path) -> None:
    payload = rotation_report_dict(
        _decision(), GENERATED_AT, PredictionLedger(tmp_path / "l.jsonl")
    )
    assert set(payload) == REPORT_REQUIRED_KEYS
    assert payload["items"]
    for item in payload["items"]:
        assert set(item) == ITEM_REQUIRED_KEYS


def test_report_declares_itself_non_predictive(tmp_path) -> None:
    payload = rotation_report_dict(
        _decision(), GENERATED_AT, PredictionLedger(tmp_path / "l.jsonl")
    )
    assert payload["predictive"] is False
    assert "NON è una previsione" in payload["non_predictive_notice"]
    assert "ADR-034" in payload["non_predictive_reason"]
    assert "ADR-036" in payload["confidence_threshold_note"]
    assert payload["confidence_threshold"] is None


def test_every_item_leaves_the_forecast_fields_empty(tmp_path) -> None:
    payload = rotation_report_dict(
        _decision(), GENERATED_AT, PredictionLedger(tmp_path / "l.jsonl")
    )
    for item in payload["items"]:
        assert item["probability_outperform"] is None
        assert item["expected_excess_return"] is None
        assert item["expected_volatility"] is None
        assert item["confidence"] == "not_applicable"


def test_report_marks_the_five_holdings_and_the_cash(tmp_path) -> None:
    payload = rotation_report_dict(
        _decision(8), GENERATED_AT, PredictionLedger(tmp_path / "l.jsonl")
    )
    selected = [i for i in payload["items"] if i["selected"]]
    assert len(selected) == 5
    assert sum(i["target_weight"] for i in selected) == pytest.approx(1.0)
    assert payload["cash_weight"] == pytest.approx(0.0)
    assert payload["status"] == STATUS_OK
    assert payload["stale_notice"] is None


def test_stale_payload_is_an_explicit_empty_state(tmp_path) -> None:
    payload = rotation_report_dict(
        None,
        GENERATED_AT,
        PredictionLedger(tmp_path / "l.jsonl"),
        status=STATUS_STALE,
        status_reason="stale feeds: TECH",
    )
    assert set(payload) == REPORT_REQUIRED_KEYS
    assert payload["status"] == STATUS_STALE
    assert payload["items"] == []
    assert payload["as_of"] is None
    assert "TECH" in payload["status_reason"]
    assert "non è stato ribilanciato" in payload["stale_notice"]
    # even with nothing to show, the caveat travels
    assert payload["predictive"] is False


def test_report_labels_use_the_asset_registry(tmp_path) -> None:
    payload = rotation_report_dict(
        _decision(3),
        GENERATED_AT,
        PredictionLedger(tmp_path / "l.jsonl"),
        names={"S2": "Technology (XLK)"},
        tickers={"S2": "XLK"},
        freshness_days={"S2": 1.0},
    )
    top = payload["items"][0]
    assert top["asset"] == "S2"
    assert top["name"] == "Technology (XLK)"
    assert top["ticker"] == "XLK"
    assert top["freshness_days"] == pytest.approx(1.0)


# --- past predictions and the live scoreboard -------------------------------


def _ledger_with_outcome(tmp_path, excess: float = 0.05):
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    decision = decide_from_panel(_panel({"A": 0.05, "B": 0.01}, date="2026-08-03"))
    ledger.append(to_predictions(decision, emitted_at=pd.Timestamp("2026-08-03T07:00:00Z")))
    asset = _series([100.0] * 3 + [100.0 * (1 + excess)] * 30, start="2026-08-01")
    other = _series([100.0] * 33, start="2026-08-01")
    bench = _series([50.0] * 33, start="2026-08-01")
    ledger.backfill_outcomes({"A": asset, "B": other}, bench)
    return ledger


def test_only_resolved_rows_appear_in_past_predictions(tmp_path) -> None:
    ledger = _ledger_with_outcome(tmp_path)
    rows = past_predictions(ledger)
    assert rows
    assert all(r["excess_return"] is not None for r in rows)
    # the 60-session horizon has not matured on 33 bars, so it must be absent
    assert {r["horizon_days"] for r in rows} == {20}


def test_scoreboard_counts_selections_and_the_universe(tmp_path) -> None:
    board = ledger_scoreboard(_ledger_with_outcome(tmp_path), horizon=20)
    assert board["horizon_days"] == 20
    assert board["n_resolved"] == 2
    assert board["selected"]["n"] == 2  # both names fit inside the top 5
    assert board["universe"]["n"] == 2
    assert board["universe"]["hit_rate"] == pytest.approx(0.5)
    assert "fortuna" in board["caveat"]


def test_scoreboard_reports_pending_rows_separately(tmp_path) -> None:
    board = ledger_scoreboard(_ledger_with_outcome(tmp_path), horizon=60)
    assert board["n_resolved"] == 0
    assert board["n_pending"] == 2
    assert board["universe"]["hit_rate"] is None


def test_empty_ledger_scoreboard_says_nothing_rather_than_zero(tmp_path) -> None:
    board = ledger_scoreboard(PredictionLedger(tmp_path / "empty.jsonl"))
    assert board["n_resolved"] == 0
    assert board["selected"]["hit_rate"] is None
    assert board["universe"]["mean_excess"] is None


# --- benchmarks --------------------------------------------------------------


def test_benchmarks_are_measured_on_the_scenario_window() -> None:
    closes = {
        "A": _series([100.0] * 5 + [110.0] * 5),
        "B": _series([50.0] * 5 + [45.0] * 5),
    }
    spy = _series([200.0] * 5 + [220.0] * 5)
    start = pd.Timestamp("2026-01-06", tz="UTC")  # index 5
    summary = benchmark_summary(closes, spy, start, initial_capital=SCENARIO_CAPITAL)
    assert summary["spy_buy_and_hold"]["return_pct"] == pytest.approx(0.0)
    assert summary["equal_weight"]["return_pct"] == pytest.approx(0.0)
    assert summary["start"] == str(start)


def test_benchmarks_track_a_moving_universe() -> None:
    closes = {"A": _series([100.0, 110.0, 120.0]), "B": _series([50.0, 50.0, 50.0])}
    spy = _series([200.0, 200.0, 210.0])
    summary = benchmark_summary(
        closes, spy, pd.Timestamp("2026-01-01", tz="UTC"), initial_capital=1000.0
    )
    assert summary["spy_buy_and_hold"]["return_pct"] == pytest.approx(5.0)
    # A +20%, B flat -> equal weight +10%
    assert summary["equal_weight"]["return_pct"] == pytest.approx(10.0)


def test_benchmarks_are_null_before_the_scenario_starts() -> None:
    summary = benchmark_summary({}, _series([1.0, 2.0]), None, initial_capital=1000.0)
    assert summary["spy_buy_and_hold"] is None
    assert summary["equal_weight"] is None


def test_benchmarks_are_null_on_a_one_point_window() -> None:
    spy = _series([200.0, 210.0])
    summary = benchmark_summary(
        {"A": _series([100.0, 110.0])},
        spy,
        pd.Timestamp("2026-01-02", tz="UTC"),
        initial_capital=1000.0,
    )
    assert summary["spy_buy_and_hold"] is None
    assert summary["equal_weight"] is None


# --- the model payload -------------------------------------------------------


def test_model_payload_has_the_full_contract(tmp_path) -> None:
    payload = rotation_model_dict(
        GENERATED_AT, _decision(), PredictionLedger(tmp_path / "l.jsonl")
    )
    assert set(payload) == MODEL_REQUIRED_KEYS


def test_model_payload_carries_the_failed_adoption_bar(tmp_path) -> None:
    payload = rotation_model_dict(
        GENERATED_AT, _decision(), PredictionLedger(tmp_path / "l.jsonl")
    )
    assert payload["predictive"] is False
    assert payload["model_adopted"] is None
    assert payload["adoption_bar"]["passed"] is False
    assert payload["adoption_bar"]["reference"] == "ADR-034"
    assert payload["calibration"]["available"] is False
    assert payload["confidence_threshold"] is None
    assert "ADR-036" in payload["confidence_threshold_note"]


def test_model_payload_reports_both_horizons(tmp_path) -> None:
    payload = rotation_model_dict(
        GENERATED_AT, _decision(), PredictionLedger(tmp_path / "l.jsonl")
    )
    assert [b["horizon_days"] for b in payload["scoreboard"]] == [20, 60]


def test_model_payload_survives_a_stale_run(tmp_path) -> None:
    payload = rotation_model_dict(
        GENERATED_AT,
        None,
        PredictionLedger(tmp_path / "l.jsonl"),
        status=STATUS_STALE,
        status_reason="stale feeds",
    )
    assert set(payload) == MODEL_REQUIRED_KEYS
    assert payload["status"] == STATUS_STALE
    assert payload["rule"] is None
    assert payload["predictive"] is False
