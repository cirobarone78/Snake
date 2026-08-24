"""Offline tests for the DCA sleeve advisor. No network."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.dca_advisor import (
    advise,
    align_timestamp,
    pick,
    portfolio_weights,
    relative_discount,
)


def _panel() -> pd.DataFrame:
    """250 daily bars: A drifts up, B drifts down, C is flat."""
    idx = pd.date_range("2024-01-01", periods=250, freq="D", tz="UTC")
    ramp = np.linspace(0.0, 1.0, 250)
    return pd.DataFrame(
        {
            "A": 100.0 * (1.0 + ramp),  # ends at its high
            "B": 100.0 * (1.0 - 0.5 * ramp),  # ends at its low
            "C": np.full(250, 50.0),  # flat
        },
        index=idx,
    )


def test_relative_discount_places_assets_in_their_own_range() -> None:
    pos = relative_discount(_panel(), lookback=180)
    assert pos["A"] == 1.0  # at the top of its window
    assert pos["B"] == 0.0  # at the bottom
    assert pos["C"] == 0.5  # flat series -> neutral, not NaN


def test_portfolio_weights_sum_to_one_and_treat_missing_as_zero() -> None:
    weights = portfolio_weights(_panel(), {"A": 1.0, "B": 1.0})
    assert abs(float(weights.sum()) - 1.0) < 1e-9
    assert weights["C"] == 0.0  # absent from holdings -> zero units


def test_portfolio_weights_empty_holdings_are_zero_not_nan() -> None:
    weights = portfolio_weights(_panel(), {})
    assert (weights == 0.0).all()


def test_advise_picks_the_most_underweight_asset() -> None:
    # Equal target, but A holds far more value than the others -> A is overweight
    # and must rank last; the pick is whichever is furthest below target.
    ranked = advise(_panel(), holdings_units={"A": 10.0, "B": 1.0, "C": 1.0})
    assert ranked.iloc[-1]["symbol"] == "A"
    assert ranked.iloc[0]["gap_pp"] > 0  # the pick is genuinely under target
    assert list(ranked["rank"]) == [1, 2, 3]


def test_advise_without_holdings_falls_back_to_discount_only() -> None:
    ranked = advise(_panel(), holdings_units=None)
    # B is at the bottom of its own range -> cheapest -> picked.
    assert ranked.iloc[0]["symbol"] == "B"
    # The weight terms are undefined, and must be NaN rather than invented.
    assert ranked["weight_now"].isna().all()
    assert ranked["gap_pp"].isna().all()


def test_advise_respects_uneven_target_weights() -> None:
    # C is targeted at 80% but holds a small share -> it is the most underweight.
    ranked = advise(
        _panel(),
        target_weights={"A": 0.1, "B": 0.1, "C": 0.8},
        holdings_units={"A": 1.0, "B": 1.0, "C": 1.0},
    )
    assert ranked.iloc[0]["symbol"] == "C"


def test_advise_is_deterministic_across_runs() -> None:
    holdings = {"A": 1.0, "B": 1.0, "C": 1.0}
    first = advise(_panel(), holdings_units=holdings)
    second = advise(_panel(), holdings_units=holdings)
    assert list(first["symbol"]) == list(second["symbol"])


def test_advise_as_of_ignores_later_bars() -> None:
    panel = _panel()
    cutoff = panel.index[100]
    ranked = advise(panel, holdings_units={"A": 1.0, "B": 1.0, "C": 1.0}, as_of=cutoff)
    price_a = float(ranked.loc[ranked["symbol"] == "A", "price"].iloc[0])
    assert abs(price_a - float(panel.loc[cutoff, "A"])) < 1e-9


def test_advise_on_empty_panel_returns_empty_frame() -> None:
    assert advise(pd.DataFrame()).empty
    assert pick(pd.DataFrame()) is None


def test_pick_matches_the_top_row() -> None:
    holdings = {"A": 10.0, "B": 1.0, "C": 1.0}
    assert pick(_panel(), holdings_units=holdings) == advise(
        _panel(), holdings_units=holdings
    ).iloc[0]["symbol"]


def test_align_timestamp_matches_index_awareness() -> None:
    aware = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
    naive = pd.date_range("2024-01-01", periods=3, freq="D")
    assert align_timestamp(aware, "2024-01-02").tzinfo is not None
    assert align_timestamp(naive, pd.Timestamp("2024-01-02", tz="UTC")).tzinfo is None
