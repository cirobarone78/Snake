"""Offline tests for the ranking models, calibration and ranking metrics (WP3).

The tests that earn their keep here are the leakage ones: that the embargo really
removes the contaminated rows, and that the calibrator never sees the test set.
A backtest that quietly leaks looks like an edge.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.backtest.costs import FeeModel, SlippageModel, TransactionCostModel
from src.backtest.ranking_metrics import (
    hit_rate_outperform,
    ic_series,
    information_coefficient,
    summarize_spread,
    top_minus_bottom,
)
from src.backtest.splits import walk_forward_splits
from src.models.calibration import (
    IsotonicCalibrator,
    brier_score,
    brier_skill_score,
    expected_calibration_error,
    reliability_table,
)
from src.models.etf_ranker import (
    ClimatologyBaseline,
    LogisticRanker,
    MomentumRanker,
    RandomRanker,
    RidgeRanker,
)

FEATURES = ["f1", "f2", "f3"]


def _panel(n_dates: int = 40, n_syms: int = 10, seed: int = 0) -> pd.DataFrame:
    """Synthetic long-form panel with a genuine (weak) signal in f1."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-06", periods=n_dates, freq="W-MON", tz="UTC")
    rows: list[dict[str, object]] = []
    for d in dates:
        for s in range(n_syms):
            f1 = rng.normal()
            rows.append({
                "date": d, "symbol": f"S{s}",
                "f1": f1, "f2": rng.normal(), "f3": rng.normal(),
                "rel_ret_60": f1,
                # outcome correlated with f1 but far from deterministic
                "excess_ret_20": 0.4 * f1 + rng.normal(scale=1.0),
            })
    df = pd.DataFrame(rows)
    df["outperform_20"] = (df["excess_ret_20"] > 0).astype("float64")
    return df


# --- embargo ----------------------------------------------------------------


def test_embargo_removes_the_contaminated_train_rows() -> None:
    plain = walk_forward_splits(100, train_size=40, test_size=10)
    embargoed = walk_forward_splits(100, train_size=40, test_size=10, embargo=5)
    assert len(plain) == len(embargoed)
    for a, b in zip(plain, embargoed, strict=True):
        assert b.test_start == a.test_start  # test windows do not move
        assert b.train_end == a.train_end - 5  # only the train tail is dropped
        assert b.embargo == 5


def test_no_train_index_falls_within_the_horizon_of_any_test_index() -> None:
    """The property the embargo exists for, stated directly."""
    horizon = 20
    for split in walk_forward_splits(300, train_size=100, test_size=25, embargo=horizon):
        last_train = split.train_end - 1
        # the last train row's target resolves at last_train + horizon,
        # which must land before the test window opens
        assert last_train + horizon <= split.test_start


def test_zero_embargo_is_the_previous_behaviour() -> None:
    assert walk_forward_splits(100, 40, 10) == walk_forward_splits(100, 40, 10, embargo=0)


def test_embargo_wider_than_train_skips_the_fold() -> None:
    assert walk_forward_splits(100, train_size=10, test_size=10, embargo=10) == []
    assert walk_forward_splits(100, train_size=10, test_size=10, embargo=99) == []


def test_negative_embargo_rejected() -> None:
    with pytest.raises(ValueError, match="embargo must be non-negative"):
        walk_forward_splits(100, 40, 10, embargo=-1)


def test_expanding_mode_respects_embargo() -> None:
    for split in walk_forward_splits(200, 50, 10, expanding=True, embargo=7):
        assert split.train_start == 0
        assert split.embargo == 7


# --- models -----------------------------------------------------------------


@pytest.mark.parametrize("model_name", ["momentum", "logistic", "ridge", "random", "climatology"])
def test_probabilities_are_bounded(model_name: str) -> None:
    df = _panel()
    models = {
        "momentum": MomentumRanker(),
        "logistic": LogisticRanker(FEATURES),
        "ridge": RidgeRanker(FEATURES),
        "random": RandomRanker(seed=1),
        "climatology": ClimatologyBaseline(),
    }
    model = models[model_name]
    model.fit(df, df["outperform_20"])
    p = model.predict_proba(df).dropna()
    assert not p.empty
    assert p.min() >= 0.0
    assert p.max() <= 1.0


def test_climatology_returns_the_train_frequency() -> None:
    df = _panel()
    train = df[df["date"] < df["date"].median()]
    model = ClimatologyBaseline().fit(train, train["outperform_20"])
    expected = float(train["outperform_20"].mean())
    assert model.rate == pytest.approx(expected)
    # constant across every row, including unseen ones
    p = model.predict_proba(df)
    assert p.nunique() == 1
    assert float(p.iloc[0]) == pytest.approx(expected)


def test_climatology_ignores_the_test_set() -> None:
    df = _panel()
    train = df[df["date"] < df["date"].median()]
    fitted = ClimatologyBaseline().fit(train, train["outperform_20"])
    before = fitted.rate
    fitted.predict_proba(df)  # scoring must not update anything
    assert fitted.rate == before


def test_random_ranker_is_deterministic_given_the_seed() -> None:
    df = _panel()
    a = RandomRanker(seed=42).fit(df, df["outperform_20"]).predict_proba(df)
    b = RandomRanker(seed=42).fit(df, df["outperform_20"]).predict_proba(df)
    c = RandomRanker(seed=43).fit(df, df["outperform_20"]).predict_proba(df)
    pd.testing.assert_series_equal(a, b)
    assert not a.equals(c)


def test_logistic_is_deterministic_and_learns_the_planted_signal() -> None:
    df = _panel(n_dates=60, seed=3)
    first = LogisticRanker(FEATURES, seed=0).fit(df, df["outperform_20"]).predict_proba(df)
    second = LogisticRanker(FEATURES, seed=0).fit(df, df["outperform_20"]).predict_proba(df)
    pd.testing.assert_series_equal(first, second)
    # f1 carries the signal, so predictions must correlate with it in-sample
    assert float(np.corrcoef(first.to_numpy(), df["f1"].to_numpy())[0, 1]) > 0.5


def test_logistic_falls_back_to_base_rate_on_a_single_class_fold() -> None:
    df = _panel()
    y = pd.Series(1.0, index=df.index)
    p = LogisticRanker(FEATURES).fit(df, y).predict_proba(df)
    assert p.dropna().nunique() == 1
    assert float(p.iloc[0]) == pytest.approx(1.0)


def test_models_do_not_impute_missing_features() -> None:
    df = _panel()
    df.loc[df.index[:5], "f2"] = np.nan
    model = LogisticRanker(FEATURES).fit(df, df["outperform_20"])
    p = model.predict_proba(df)
    assert p.iloc[:5].isna().all()  # missing in, missing out — never invented
    assert p.iloc[5:].notna().all()


def test_rank_is_within_date() -> None:
    df = _panel(n_dates=5, n_syms=8)
    model = MomentumRanker().fit(df, df["outperform_20"])
    ranks = model.rank(df, df["date"])
    by_date = pd.DataFrame({"date": df["date"], "rank": ranks}).groupby("date")["rank"]
    # every date's ranks span the full (0, 1] range independently
    assert by_date.max().nunique() == 1
    assert float(by_date.max().iloc[0]) == pytest.approx(1.0)


# --- calibration ------------------------------------------------------------


def test_calibrator_is_fit_on_train_only() -> None:
    """Changing the test set must not change the calibrator."""
    df = _panel(n_dates=60, seed=5)
    cutoff = df["date"].median()
    train = df[df["date"] < cutoff]
    test_a = df[df["date"] >= cutoff]
    test_b = test_a.copy()
    test_b["outperform_20"] = 1.0 - test_b["outperform_20"]  # flip every outcome

    cal = IsotonicCalibrator().fit(train["f1"].rank(pct=True), train["outperform_20"])
    out_a = cal.calibrate(test_a["f1"].rank(pct=True))
    out_b = cal.calibrate(test_b["f1"].rank(pct=True))
    pd.testing.assert_series_equal(out_a, out_b)


def test_calibration_is_monotone_so_it_cannot_reorder() -> None:
    """Isotonic can merge neighbours into a plateau but never swap their order."""
    df = _panel(n_dates=60, seed=7)
    scores = df["f1"].rank(pct=True)
    cal = IsotonicCalibrator().fit(scores, df["outperform_20"])
    out = cal.calibrate(scores)
    ok = out.notna()
    pairs = pd.DataFrame({"s": scores[ok], "c": out[ok]}).sort_values("s")
    # weakly increasing: no pair is ever put back in the wrong order
    assert (pairs["c"].diff().dropna() >= -1e-12).all()
    # and the map is not degenerate: it still separates low from high
    assert float(pairs["c"].iloc[-1]) > float(pairs["c"].iloc[0])


def test_calibration_improves_a_deliberately_miscalibrated_forecast() -> None:
    rng = np.random.default_rng(0)
    n = 2000
    truth = rng.random(n)
    y = pd.Series((rng.random(n) < truth).astype("float64"))
    # squash toward 0.5: right ordering, badly wrong confidence
    bad = pd.Series(0.5 + (truth - 0.5) * 0.2)
    cal = IsotonicCalibrator().fit(bad, y)
    assert brier_score(cal.calibrate(bad), y) < brier_score(bad, y)


def test_unfit_calibrator_passes_scores_through() -> None:
    scores = pd.Series([0.1, 0.5, 0.9])
    cal = IsotonicCalibrator().fit(pd.Series([0.5, 0.5]), pd.Series([1.0, 1.0]))
    assert not cal.is_fitted
    pd.testing.assert_series_equal(cal.calibrate(scores), scores)


def test_calibrator_preserves_nan() -> None:
    df = _panel()
    cal = IsotonicCalibrator().fit(df["f1"].rank(pct=True), df["outperform_20"])
    scores = pd.Series([0.2, np.nan, 0.8])
    assert bool(cal.calibrate(scores).isna().iloc[1])


def test_brier_score_and_skill() -> None:
    y = pd.Series([1.0, 0.0, 1.0, 0.0])
    assert brier_score(pd.Series([1.0, 0.0, 1.0, 0.0]), y) == pytest.approx(0.0)
    assert brier_score(pd.Series([0.5] * 4), y) == pytest.approx(0.25)
    # a constant forecast at the base rate scores rate*(1-rate)
    assert brier_skill_score(pd.Series([0.5] * 4), y, reference=0.25) == pytest.approx(0.0)
    assert brier_skill_score(pd.Series([1.0, 0.0, 1.0, 0.0]), y, reference=0.25) == pytest.approx(1.0)


def test_reliability_table_and_ece() -> None:
    rng = np.random.default_rng(1)
    n = 4000
    p = pd.Series(rng.random(n))
    y = pd.Series((rng.random(n) < p).astype("float64"))  # perfectly calibrated by construction
    table = reliability_table(p, y, bins=10)
    assert not table.empty
    assert table["n"].sum() == n
    assert (table["observed_frequency"] - table["mean_predicted"]).abs().max() < 0.06
    assert expected_calibration_error(p, y, bins=10) < 0.03
    # empty bins are omitted, not reported as zeros
    narrow = reliability_table(pd.Series([0.05] * 50), pd.Series([0.0] * 50), bins=10)
    assert len(narrow) == 1


# --- ranking metrics --------------------------------------------------------


def test_perfect_ranking_scores_ic_one_and_inverted_minus_one() -> None:
    dates = pd.Series(["d1"] * 6 + ["d2"] * 6)
    outcome = pd.Series([1.0, 2, 3, 4, 5, 6] * 2)
    assert information_coefficient(dates, outcome, outcome)["spearman"] == pytest.approx(1.0)
    assert information_coefficient(dates, -outcome, outcome)["spearman"] == pytest.approx(-1.0)


def test_ic_is_averaged_per_date_not_pooled() -> None:
    """Two dates on different scales: pooling would report ~0, per-date reports 1."""
    dates = pd.Series(["d1"] * 4 + ["d2"] * 4)
    pred = pd.Series([1.0, 2, 3, 4, 1, 2, 3, 4])
    real = pd.Series([1.0, 2, 3, 4, 101, 102, 103, 104])
    assert information_coefficient(dates, pred, real, min_names=4)["spearman"] == pytest.approx(1.0)


def test_ic_skips_degenerate_and_thin_dates() -> None:
    dates = pd.Series(["d1"] * 6 + ["d2"] * 6 + ["d3"] * 2)
    pred = pd.Series([1.0, 2, 3, 4, 5, 6] + [7.0] * 6 + [1.0, 2])
    real = pd.Series(list(np.arange(6.0)) + list(np.arange(6.0)) + [1.0, 2])
    table = ic_series(dates, pred, real, min_names=5)
    assert list(table["date"]) == ["d1"]  # d2 constant prediction, d3 too thin


def test_ic_empty_input() -> None:
    empty = pd.Series([], dtype="float64")
    out = information_coefficient(pd.Series([], dtype="object"), empty, empty)
    assert out["n_dates"] == 0.0
    assert np.isnan(out["spearman"])


def test_top_minus_bottom_costs_reduce_the_spread() -> None:
    df = _panel(n_dates=30, n_syms=10, seed=11)
    ranks = df.groupby("date")["rel_ret_60"].rank(pct=True)
    free = top_minus_bottom(df["date"], ranks, df["excess_ret_20"])
    costs = TransactionCostModel(
        fee=FeeModel(maker_rate=0.0010, taker_rate=0.0010),
        slippage=SlippageModel(base_cost_bps=5.0),
    )
    charged = top_minus_bottom(df["date"], ranks, df["excess_ret_20"], costs=costs)
    assert (free["cost"] == 0.0).all()
    assert (charged["cost"] > 0.0).all()
    assert charged["net"].mean() < free["net"].mean()
    pd.testing.assert_series_equal(free["gross"], charged["gross"])  # costs never touch gross


def test_top_minus_bottom_separates_a_perfect_ranking() -> None:
    dates = pd.Series(["d1"] * 10)
    ranks = pd.Series(np.linspace(0, 1, 10))
    returns = pd.Series(np.linspace(-0.05, 0.05, 10))
    out = top_minus_bottom(dates, ranks, returns, q=0.2)
    assert len(out) == 1
    assert float(out["gross"].iloc[0]) > 0.0


def test_top_minus_bottom_rejects_bad_q_and_thin_dates() -> None:
    with pytest.raises(ValueError, match="q must be in"):
        top_minus_bottom(pd.Series(["d"]), pd.Series([0.5]), pd.Series([0.1]), q=0.9)
    thin = top_minus_bottom(pd.Series(["d"] * 3), pd.Series([0.1, 0.5, 0.9]), pd.Series([1.0, 2, 3]))
    assert thin.empty


def test_summarize_spread() -> None:
    spread = pd.DataFrame({"net": [0.01, 0.02, -0.005, 0.015]})
    out = summarize_spread(spread)
    assert out["n"] == 4.0
    assert out["mean"] == pytest.approx(0.01)
    assert out["positive_share"] == pytest.approx(0.75)
    assert summarize_spread(pd.DataFrame())["n"] == 0.0


def test_hit_rate() -> None:
    p = pd.Series([0.9, 0.8, 0.2, 0.1])
    y = pd.Series([1.0, 0.0, 0.0, 1.0])
    assert hit_rate_outperform(p, y) == pytest.approx(0.5)
    assert np.isnan(hit_rate_outperform(pd.Series([np.nan]), pd.Series([1.0])))
