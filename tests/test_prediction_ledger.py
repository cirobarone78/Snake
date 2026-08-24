"""Offline tests for the prediction ledger: idempotency, and no retro-dating.

The two properties worth defending here are the ones that make a track record
worth reading at all: a re-run cannot duplicate or overwrite a row, and an
outcome cannot appear before the horizon has actually matured. Everything else
is bookkeeping.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from src.execution.prediction_ledger import Factor, Prediction, PredictionLedger


def _prediction(
    asset: str = "TECH",
    emitted_at: str = "2026-08-24T07:00:00+00:00",
    cutoff: str = "2026-08-21T00:00:00+00:00",
    horizon: int = 20,
    **kwargs: object,
) -> Prediction:
    base: dict[str, object] = {
        "emitted_at": emitted_at,
        "data_cutoff": cutoff,
        "model_version": "momentum_rel_60@1",
        "dataset_version": "abc123",
        "asset": asset,
        "benchmark": "SPY",
        "horizon_days": horizon,
        "predictive": False,
        "rule": "momentum_rel_60",
        "selection_score": 0.04,
        "selection_rank": 1,
        "universe_size": 20,
        "selected": True,
        "target_weight": 0.2,
        "top_factors": [Factor(name="rel_ret_60", direction="positive", value=0.04)],
    }
    base.update(kwargs)
    return Prediction.model_validate(base)


def _series(values: list[float], start: str = "2026-08-01", periods: int | None = None) -> pd.Series:
    n = periods if periods is not None else len(values)
    idx = pd.date_range(start, periods=n, freq="D", tz="UTC")
    return pd.Series(np.array(values, dtype=float), index=idx)


# --- the schema guard rail (ADR-036) ----------------------------------------


def test_non_predictive_row_cannot_carry_a_probability() -> None:
    with pytest.raises(ValidationError) as exc:
        _prediction(probability_outperform=0.61)
    assert "probability_outperform" in str(exc.value)


def test_non_predictive_row_cannot_carry_expected_values() -> None:
    for field in ("expected_excess_return", "expected_volatility"):
        with pytest.raises(ValidationError):
            _prediction(**{field: 0.02})


def test_non_predictive_row_cannot_claim_a_confidence_level() -> None:
    with pytest.raises(ValidationError) as exc:
        _prediction(confidence="medium")
    assert "confidence" in str(exc.value)


def test_predictive_row_may_carry_forecast_fields() -> None:
    """The schema is not anti-probability, it is anti-*uncalibrated* probability."""
    row = _prediction(predictive=True, probability_outperform=0.61, confidence="medium")
    assert row.probability_outperform == pytest.approx(0.61)


def test_observed_state_is_recorded_instead_of_forecasts() -> None:
    row = _prediction(realized_vol_60=0.24)
    record = row.to_record()
    assert record["probability_outperform"] is None
    assert record["expected_excess_return"] is None
    assert record["expected_volatility"] is None
    assert record["realized_vol_60"] == pytest.approx(0.24)
    assert record["confidence"] == "not_applicable"
    assert record["outcome"] is None


# --- append idempotency -----------------------------------------------------


def test_append_writes_one_line_per_row(tmp_path) -> None:
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    assert ledger.append([_prediction("TECH"), _prediction("ENERGY")]) == 2
    assert len(ledger.path.read_text().strip().splitlines()) == 2
    assert len(ledger.read()) == 2


def test_append_is_idempotent_on_the_key(tmp_path) -> None:
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH")])
    assert ledger.append([_prediction("TECH")]) == 0
    assert len(ledger.raw_records()) == 1


def test_append_deduplicates_within_one_batch(tmp_path) -> None:
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    assert ledger.append([_prediction("TECH"), _prediction("TECH")]) == 1


def test_append_never_overwrites_an_existing_row(tmp_path) -> None:
    """A second opinion about the same moment must not erase the first."""
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH", selection_rank=1)])
    ledger.append([_prediction("TECH", selection_rank=7)])
    rows = ledger.read()
    assert len(rows) == 1
    assert rows[0].selection_rank == 1


def test_a_retry_with_a_new_timestamp_cannot_re_predict_the_same_bar(tmp_path) -> None:
    """A cron retry stamps a new emitted_at; the decision bar is still the same."""
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH", emitted_at="2026-08-24T07:00:00+00:00")])
    assert ledger.append([_prediction("TECH", emitted_at="2026-08-24T09:30:00+00:00")]) == 0
    assert len(ledger.raw_records()) == 1


def test_a_new_decision_bar_is_a_new_row(tmp_path) -> None:
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH", cutoff="2026-08-21T00:00:00+00:00")])
    assert (
        ledger.append(
            [
                _prediction(
                    "TECH",
                    emitted_at="2026-08-31T07:00:00+00:00",
                    cutoff="2026-08-28T00:00:00+00:00",
                )
            ]
        )
        == 1
    )
    assert len(ledger.raw_records()) == 2


def test_same_asset_different_horizon_is_a_different_row(tmp_path) -> None:
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH", horizon=20)])
    assert ledger.append([_prediction("TECH", horizon=60)]) == 1
    assert len(ledger.raw_records()) == 2


def test_missing_file_reads_as_empty(tmp_path) -> None:
    ledger = PredictionLedger(tmp_path / "nope.jsonl")
    assert ledger.raw_records() == []
    assert ledger.frame().empty


# --- outcomes: only when the future has actually happened --------------------


def test_unmatured_horizon_stays_null(tmp_path) -> None:
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH", cutoff="2026-08-10T00:00:00+00:00", horizon=20)])
    # only 5 bars after the cutoff: the 20-session horizon has not matured
    prices = _series(list(np.linspace(100, 110, 15)), start="2026-08-01")
    assert ledger.backfill_outcomes({"TECH": prices}, prices) == 0
    assert ledger.read()[0].outcome is None


def test_matured_horizon_resolves_with_the_excess_return(tmp_path) -> None:
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH", cutoff="2026-08-05T00:00:00+00:00", horizon=3)])
    # cutoff at index 4 (2026-08-05); asset +10% over 3 bars, benchmark flat
    asset = _series([100, 100, 100, 100, 100, 102, 105, 110, 110], start="2026-08-01")
    bench = _series([50, 50, 50, 50, 50, 50, 50, 50, 50], start="2026-08-01")
    assert ledger.backfill_outcomes({"TECH": asset}, bench) == 1
    outcome = ledger.read()[0].outcome
    assert outcome is not None
    assert outcome.asset_return == pytest.approx(0.10)
    assert outcome.benchmark_return == pytest.approx(0.0)
    assert outcome.excess_return == pytest.approx(0.10)
    assert outcome.outperformed is True
    assert outcome.resolved_price_date.startswith("2026-08-08")


def test_outcome_needs_the_benchmark_leg_too(tmp_path) -> None:
    """An excess return against a benchmark bar that does not exist is invented."""
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH", cutoff="2026-08-05T00:00:00+00:00", horizon=3)])
    asset = _series([100, 100, 100, 100, 100, 102, 105, 110], start="2026-08-01")
    short_bench = _series([50, 50, 50, 50, 50], start="2026-08-01")
    assert ledger.backfill_outcomes({"TECH": asset}, short_bench) == 0
    assert ledger.read()[0].outcome is None


def test_backfill_changes_nothing_but_the_outcome_field(tmp_path) -> None:
    """The whole point: a row emitted before the fact stays exactly as emitted."""
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH", cutoff="2026-08-05T00:00:00+00:00", horizon=3)])
    before = json.loads(ledger.path.read_text().strip())

    asset = _series([100, 100, 100, 100, 100, 102, 105, 110], start="2026-08-01")
    bench = _series([50, 50, 50, 50, 50, 50, 50, 50], start="2026-08-01")
    ledger.backfill_outcomes({"TECH": asset}, bench)

    after = json.loads(ledger.path.read_text().strip())
    assert after["outcome"] is not None
    assert {k: v for k, v in after.items() if k != "outcome"} == {
        k: v for k, v in before.items() if k != "outcome"
    }


def test_outcome_is_written_once_and_never_revised(tmp_path) -> None:
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH", cutoff="2026-08-05T00:00:00+00:00", horizon=3)])
    asset = _series([100, 100, 100, 100, 100, 102, 105, 110], start="2026-08-01")
    bench = _series([50, 50, 50, 50, 50, 50, 50, 50], start="2026-08-01")
    assert ledger.backfill_outcomes({"TECH": asset}, bench) == 1
    first = ledger.path.read_text()

    # the world moves on and the asset crashes: the resolved row must not care
    later = _series([100, 100, 100, 100, 100, 102, 105, 110, 40, 30], start="2026-08-01")
    assert ledger.backfill_outcomes({"TECH": later}, bench) == 0
    assert ledger.path.read_text() == first


def test_backfill_skips_assets_it_has_no_prices_for(tmp_path) -> None:
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH", cutoff="2026-08-05T00:00:00+00:00", horizon=3)])
    bench = _series([50] * 8, start="2026-08-01")
    assert ledger.backfill_outcomes({"OTHER": bench}, bench) == 0
    assert ledger.read()[0].outcome is None


def test_backfill_leaves_the_file_untouched_when_nothing_matures(tmp_path) -> None:
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH", cutoff="2026-08-10T00:00:00+00:00", horizon=20)])
    before = ledger.path.read_text()
    prices = _series(list(np.linspace(100, 110, 12)), start="2026-08-01")
    ledger.backfill_outcomes({"TECH": prices}, prices)
    assert ledger.path.read_text() == before


def test_tz_naive_prices_are_treated_as_utc(tmp_path) -> None:
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH", cutoff="2026-08-05T00:00:00+00:00", horizon=2)])
    idx = pd.date_range("2026-08-01", periods=8, freq="D")  # naive
    asset = pd.Series(np.array([100.0] * 5 + [110.0] * 3), index=idx)
    bench = pd.Series(np.array([50.0] * 8), index=idx)
    assert ledger.backfill_outcomes({"TECH": asset}, bench) == 1


def test_frame_flattens_the_ledger_for_reporting(tmp_path) -> None:
    ledger = PredictionLedger(tmp_path / "l.jsonl")
    ledger.append([_prediction("TECH"), _prediction("ENERGY")])
    frame = ledger.frame()
    assert len(frame) == 2
    assert set(frame["asset"]) == {"TECH", "ENERGY"}
