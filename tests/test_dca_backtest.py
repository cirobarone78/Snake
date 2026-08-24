"""Offline tests for the DCA validation harness. No network."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.dca_backtest import (
    compare,
    month_ends,
    random_control,
    simulate,
    split_halves,
)


def _panel(days: int = 400) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=days, freq="D", tz="UTC")
    ramp = np.linspace(0.0, 1.0, days)
    return pd.DataFrame(
        {
            "A": 100.0 * (1.0 + ramp),
            "B": 100.0 * (1.0 - 0.5 * ramp),
            "C": np.full(days, 50.0),
        },
        index=idx,
    )


def test_month_ends_returns_one_date_per_month() -> None:
    idx = pd.date_range("2024-01-01", periods=200, freq="D", tz="UTC")
    dates = month_ends(idx, day_of_month=1)
    assert len(dates) == 7  # Jan..Jul
    assert all(d.day == 1 for d in dates)


def test_month_ends_honours_day_of_month() -> None:
    idx = pd.date_range("2024-01-01", periods=100, freq="D", tz="UTC")
    dates = month_ends(idx, day_of_month=15)
    assert all(d.day == 15 for d in dates)


def test_simulate_split_spends_the_budget_every_month() -> None:
    res = simulate(_panel(), "split", budget_eur=30.0)
    assert res["n_purchases"] == 14
    assert res["invested_eur"] == 14 * 30.0
    assert all(v > 0 for v in res["units"].values())


def test_simulate_single_asset_rule_buys_only_that_asset() -> None:
    res = simulate(_panel(), "A", budget_eur=10.0)
    assert res["units"]["A"] > 0
    assert res["units"]["B"] == 0.0 and res["units"]["C"] == 0.0


def test_fees_reduce_the_units_acquired() -> None:
    free = simulate(_panel(), "split", fee_pct=0.0)
    charged = simulate(_panel(), "split", fee_pct=1.0)
    assert charged["units"]["A"] < free["units"]["A"]
    assert charged["invested_eur"] == free["invested_eur"]  # fee comes out of the buy


def test_momentum_rule_buys_the_riser_and_discount_rule_buys_the_faller() -> None:
    # A only rises and B only falls, so the two rules must disagree completely.
    assert simulate(_panel(), "momentum")["units"]["A"] > 0
    assert simulate(_panel(), "momentum")["units"]["B"] == 0.0
    assert simulate(_panel(), "discount")["units"]["B"] > 0


def test_advisor_ends_closer_to_target_than_a_single_asset_rule() -> None:
    table = compare(_panel(), rules=["advisor", "A"], fee_pct=0.0)
    drift = dict(zip(table["rule"], table["weight_drift_pp"], strict=True))
    assert drift["advisor"] < drift["A"]


def test_compare_reports_vs_split_relative_to_the_split_row() -> None:
    table = compare(_panel(), rules=["split", "A", "advisor"])
    row = table.loc[table["rule"] == "split"].iloc[0]
    assert row["vs_split"] == 1.0
    assert (table["vs_split"] > 0).all()


def test_compare_leaves_vs_split_null_without_a_split_benchmark() -> None:
    table = compare(_panel(), rules=["A", "advisor"])
    assert table["vs_split"].isna().all()


def test_max_drawdown_is_positive_when_the_holding_falls() -> None:
    res = simulate(_panel(), "B")  # B only declines
    assert res["max_drawdown_pct"] is not None
    assert res["max_drawdown_pct"] > 0


def test_split_halves_covers_disjoint_periods() -> None:
    halves = split_halves(_panel(), rules=["split"])
    first = halves["first"].iloc[0]["n_purchases"]
    second = halves["second"].iloc[0]["n_purchases"]
    assert first > 0 and second > 0
    whole = compare(_panel(), rules=["split"]).iloc[0]["n_purchases"]
    # The split point can land mid-month, so the halves may share one month.
    assert first + second >= whole


def test_random_control_locates_a_rule_inside_the_random_distribution() -> None:
    out = random_control(_panel(), rule="split", n_seeds=20)
    assert out["n_seeds"] == 20
    assert out["percentile"] is not None
    assert 0.0 <= out["percentile"] <= 100.0


def test_simulate_on_empty_panel_reports_nothing_rather_than_failing() -> None:
    res = simulate(pd.DataFrame(), "split")
    assert res["n_purchases"] == 0
    assert res["multiple"] is None
