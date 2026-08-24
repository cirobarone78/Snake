"""Offline tests for the walk-forward ranking harness (WP3). No network.

These test the *harness*, not the models: before trusting what a backtest says
about a strategy, you have to know the backtest itself isn't leaking.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.backtest.ranking_backtest import (
    concat_predictions,
    embargo_gap_days,
    fold_summary,
    realised_excess,
    split_halves,
    walk_forward_predict,
    weekly_sample,
)
from src.ingestion.tier1.ranking_backtest_cli import build_models, evaluate_model, verdicts
from src.models.etf_ranker import ClimatologyBaseline, MomentumRanker

FEATURES = ["f1", "f2"]


def _panel(n_weeks: int = 300, n_syms: int = 10, seed: int = 0, signal: float = 0.0) -> pd.DataFrame:
    """Weekly long-form panel shaped like the WP2 output."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2012-01-02", periods=n_weeks, freq="W-MON", tz="UTC")
    rows: list[dict[str, object]] = []
    for d in dates:
        for s in range(n_syms):
            f1 = rng.normal()
            excess = signal * f1 + rng.normal(scale=0.05)
            rows.append({
                "date": d, "symbol": f"S{s}", "f1": f1, "f2": rng.normal(),
                "rel_ret_60": f1, "excess_ret_20": excess,
                "outperform_20": 1.0 if excess > 0 else 0.0,
            })
    return pd.DataFrame(rows)


# --- sampling ---------------------------------------------------------------


def test_weekly_sample_keeps_only_mondays() -> None:
    daily = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=21, freq="D", tz="UTC"),
        "symbol": "A",
    })
    weekly = weekly_sample(daily)
    assert (pd.DatetimeIndex(weekly["date"]).weekday == 0).all()
    assert len(weekly) == 3


def test_weekly_sample_does_not_forward_fill_a_missing_monday() -> None:
    """A holiday Monday drops the week rather than inventing a decision date."""
    dates = pd.date_range("2024-01-01", periods=21, freq="D", tz="UTC")
    daily = pd.DataFrame({"date": dates, "symbol": "A"})
    without = daily[daily["date"] != dates[7]]  # remove the second Monday
    assert len(weekly_sample(without)) == 2


# --- walk-forward -----------------------------------------------------------


def test_folds_never_split_a_cross_section() -> None:
    panel = _panel(n_weeks=260)
    folds = walk_forward_predict(
        panel, MomentumRanker(), "outperform_20",
        train_weeks=104, test_weeks=52, embargo_weeks=4,
    )
    assert folds
    for f in folds:
        test_dates = set(pd.unique(f.predictions["date"]))
        # every symbol present on a test date, none of them straddling
        assert len(test_dates) > 0
        counts = f.predictions.groupby("date").size()
        assert counts.nunique() == 1


def test_embargo_gap_is_actually_present_between_train_and_test() -> None:
    panel = _panel(n_weeks=260)
    folds = walk_forward_predict(
        panel, MomentumRanker(), "outperform_20",
        train_weeks=104, test_weeks=52, embargo_weeks=4,
    )
    gaps = embargo_gap_days(folds)
    assert gaps
    # 4 embargoed weekly samples + the step to the next one = 5 weeks of calendar
    assert all(g >= 28 for g in gaps)


def test_no_embargo_leaves_the_usual_one_week_gap() -> None:
    panel = _panel(n_weeks=260)
    folds = walk_forward_predict(
        panel, MomentumRanker(), "outperform_20",
        train_weeks=104, test_weeks=52, embargo_weeks=0,
    )
    assert all(g == 7 for g in embargo_gap_days(folds))


def test_predictions_are_out_of_sample_only() -> None:
    panel = _panel(n_weeks=260)
    folds = walk_forward_predict(
        panel, MomentumRanker(), "outperform_20",
        train_weeks=104, test_weeks=52, embargo_weeks=4,
    )
    for f in folds:
        assert f.predictions["date"].min() >= f.test_start
        assert f.predictions["date"].max() <= f.test_end
        assert f.test_start > f.train_end


def test_calibrator_never_sees_the_test_outcomes() -> None:
    """Flip every test-set outcome: the predictions must not move at all."""
    panel = _panel(n_weeks=260, signal=0.5)
    folds_a = walk_forward_predict(
        panel, MomentumRanker(), "outperform_20", 104, 52, 4, calibrate=True
    )
    flipped = panel.copy()
    cutoff = flipped["date"].quantile(0.66)
    late = flipped["date"] >= cutoff
    flipped.loc[late, "outperform_20"] = 1.0 - flipped.loc[late, "outperform_20"]
    folds_b = walk_forward_predict(
        flipped, MomentumRanker(), "outperform_20", 104, 52, 4, calibrate=True
    )
    # compare only folds whose TRAIN window predates the flip
    a = concat_predictions(folds_a)
    b = concat_predictions(folds_b)
    early = a["date"] < cutoff
    pd.testing.assert_series_equal(a.loc[early, "proba"], b.loc[early, "proba"])


def test_walk_forward_is_deterministic() -> None:
    panel = _panel(n_weeks=260, signal=0.3)
    models = build_models(FEATURES)
    first = concat_predictions(walk_forward_predict(panel, models[1], "outperform_20", 104, 52, 4))
    second = concat_predictions(walk_forward_predict(panel, build_models(FEATURES)[1], "outperform_20", 104, 52, 4))
    pd.testing.assert_frame_equal(first, second)


def test_short_panel_yields_no_folds() -> None:
    panel = _panel(n_weeks=20)
    assert walk_forward_predict(panel, MomentumRanker(), "outperform_20", 104, 52, 4) == []
    assert concat_predictions([]).empty
    assert fold_summary([]).empty


def test_split_halves_is_chronological_and_disjoint() -> None:
    panel = _panel(n_weeks=260)
    preds = concat_predictions(
        walk_forward_predict(panel, MomentumRanker(), "outperform_20", 104, 52, 4)
    )
    first, second = split_halves(preds)
    assert not first.empty and not second.empty
    assert first["date"].max() < second["date"].min()
    assert len(first) + len(second) == len(preds)


def test_realised_excess_aligns_on_date_and_symbol() -> None:
    panel = _panel(n_weeks=260)
    preds = concat_predictions(
        walk_forward_predict(panel, MomentumRanker(), "outperform_20", 104, 52, 4)
    )
    excess = realised_excess(panel, preds, "excess_ret_20")
    assert len(excess) == len(preds)
    assert excess.notna().all()
    merged = preds.assign(e=excess).merge(
        panel, on=["date", "symbol"], suffixes=("", "_p")
    )
    assert np.allclose(merged["e"], merged["excess_ret_20"])


# --- verdicts ---------------------------------------------------------------


def test_verdicts_report_failure_on_pure_noise() -> None:
    """No signal in the data must not produce a passed adoption bar."""
    panel = _panel(n_weeks=300, signal=0.0, seed=4)
    results = [
        evaluate_model(panel, m, 20, "excess_ret_20") for m in build_models(FEATURES)
    ]
    v = verdicts(results, 20)
    assert v["adoption_bar_passed"] is False
    assert abs(v["H1_value"]) < 0.1  # IC indistinguishable from zero


def test_verdicts_detect_a_planted_signal() -> None:
    """The harness must be able to say yes, or a 'no' means nothing."""
    panel = _panel(n_weeks=300, signal=3.0, seed=6)
    results = [
        evaluate_model(panel, m, 20, "excess_ret_20") for m in build_models(FEATURES)
    ]
    v = verdicts(results, 20)
    assert v["H1_momentum_ic_positive"] is True
    assert v["H1_value"] > 0.5
    assert v["adoption_bar_passed"] is True


def test_climatology_brier_equals_base_rate_variance() -> None:
    panel = _panel(n_weeks=300, signal=0.0, seed=8)
    result = evaluate_model(panel, ClimatologyBaseline(), 20, "excess_ret_20")
    o = result["overall"]
    # a constant forecast at rate r scores about r*(1-r)
    assert o["brier"] == pytest.approx(o["base_rate"] * (1 - o["base_rate"]), abs=0.02)
    assert o["ic_spearman"] != o["ic_spearman"] or abs(o["ic_spearman"]) < 1e-9  # NaN or 0


def test_evaluate_model_on_empty_panel() -> None:
    empty = _panel(n_weeks=5)
    out = evaluate_model(empty, MomentumRanker(), 20, "excess_ret_20")
    assert out["n_predictions"] == 0
