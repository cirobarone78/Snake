"""Offline tests for the conditional rotation-outcome layer. No network."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features.conditional_outcomes import (
    bucket_labels,
    conditional_outcome_table,
    forward_return,
    momentum,
    rotation_observations,
    rotation_outcomes,
    split_by_date,
    state_ranking,
)


def _panel(n: int = 80, n_assets: int = 6) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
    rng = np.random.default_rng(0)
    cols = {f"A{i}": 100 * np.cumprod(1 + rng.normal(0, 0.01, n)) for i in range(n_assets)}
    return pd.DataFrame(cols, index=idx)


# --- primitives ---


def test_forward_return_is_causal_and_tail_nan() -> None:
    close = pd.Series([100.0, 110.0, 121.0], index=pd.date_range("2020-01-01", periods=3))
    fwd = forward_return(close, horizon=1)
    assert fwd.iloc[0] == pytest.approx(0.1)  # 110/100 - 1
    assert fwd.iloc[1] == pytest.approx(0.1)  # 121/110 - 1
    assert pd.isna(fwd.iloc[-1])  # last has no realised future


def test_momentum_is_trailing() -> None:
    close = pd.Series([100.0, 100.0, 200.0], index=pd.date_range("2020-01-01", periods=3))
    mom = momentum(close, lookback=1)
    assert pd.isna(mom.iloc[0])
    assert mom.iloc[1] == 0.0
    assert mom.iloc[2] == 1.0  # 200/100 - 1


def test_forward_return_rejects_bad_horizon() -> None:
    close = pd.Series([1.0, 2.0])
    try:
        forward_return(close, horizon=0)
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_bucket_labels() -> None:
    assert bucket_labels(3) == ["weak", "mid", "strong"]
    assert bucket_labels(4) == ["b1", "b2", "b3", "b4"]


# --- observations ---


def test_rotation_observations_no_lookahead_tail() -> None:
    panel = _panel()
    obs = rotation_observations(panel, lookback=10, horizon=10, n_buckets=3)
    # every observation must have a realised forward return (no NaN leaked in)
    assert obs["fwd_ret"].notna().all()
    # the last `horizon` dates cannot appear: their forward return is unrealised
    assert obs["date"].max() <= panel.index[-11]


def test_rotation_observations_buckets_are_labelled() -> None:
    panel = _panel()
    obs = rotation_observations(panel, lookback=10, horizon=5, n_buckets=3)
    assert set(obs["bucket"].unique()) <= {"weak", "mid", "strong"}
    assert not obs.empty


def test_rotation_observations_skips_thin_dates() -> None:
    # only 2 assets but ask for 3 buckets -> no date qualifies
    panel = _panel(n_assets=2)
    obs = rotation_observations(panel, lookback=5, horizon=5, n_buckets=3)
    assert obs.empty


def test_strong_bucket_captures_top_momentum() -> None:
    # deterministic panel: A_k ramps at rate proportional to k, so ranking by
    # trailing momentum is stable -> the steepest asset lands in 'strong'.
    idx = pd.date_range("2020-01-01", periods=40, freq="D", tz="UTC")
    cols = {f"A{k}": np.array([100.0 * (1 + 0.001 * k) ** i for i in range(40)]) for k in range(6)}
    panel = pd.DataFrame(cols, index=idx)
    obs = rotation_observations(panel, lookback=10, horizon=5, n_buckets=3)
    steepest = obs[obs["symbol"] == "A5"]
    assert (steepest["bucket"] == "strong").all()
    flattest = obs[obs["symbol"] == "A0"]
    assert (flattest["bucket"] == "weak").all()


# --- conditional table ---


def test_conditional_table_counts_and_baseline() -> None:
    obs = pd.DataFrame(
        {
            "bucket": ["weak", "weak", "strong", "strong"],
            "fwd_ret": [-0.10, -0.20, 0.10, 0.30],
        }
    )
    table = conditional_outcome_table(obs, labels=["weak", "mid", "strong"])
    # 'mid' has no rows -> skipped; weak, strong, ALL present
    assert table["state"].tolist() == ["weak", "strong", "ALL"]
    weak = table[table["state"] == "weak"].iloc[0]
    assert weak["n"] == 2
    assert weak["hit_rate"] == 0.0
    assert weak["mean_fwd_pct"] == pytest.approx(-15.0)
    strong = table[table["state"] == "strong"].iloc[0]
    assert strong["hit_rate"] == 1.0
    assert strong["mean_fwd_pct"] == pytest.approx(20.0)
    all_row = table[table["state"] == "ALL"].iloc[0]
    assert all_row["n"] == 4
    assert all_row["hit_rate"] == 0.5


def test_conditional_table_empty() -> None:
    assert conditional_outcome_table(pd.DataFrame()).empty


def test_step_yields_nonoverlapping_dates() -> None:
    panel = _panel(n=120)
    obs = rotation_observations(panel, lookback=10, horizon=10, n_buckets=3, step=10)
    dates = pd.Index(sorted(obs["date"].unique()))
    gaps = dates[1:] - dates[:-1]
    # consecutive observation dates are >= horizon apart -> windows don't overlap
    assert (gaps >= pd.Timedelta(days=10)).all()


def test_extra_states_attached_and_conditioned() -> None:
    panel = _panel(n=80)
    # a per-date regime label, flipping halfway
    regime = pd.Series(
        ["bull"] * 40 + ["bear"] * 40, index=panel.index, name="regime"
    )
    obs = rotation_observations(
        panel, lookback=10, horizon=5, n_buckets=3, extra_states={"regime": regime}
    )
    assert "regime" in obs.columns
    assert set(obs["regime"].unique()) <= {"bull", "bear", "unknown"}
    # composite conditioning: bucket x regime produces 'weak | bull'-style states
    table = conditional_outcome_table(obs, state_col=["bucket", "regime"])
    assert any(" | " in s for s in table["state"] if s != "ALL")
    assert table["state"].tolist()[-1] == "ALL"


def test_split_by_date_is_chronological_and_disjoint() -> None:
    panel = _panel(n=100)
    obs = rotation_observations(panel, lookback=10, horizon=5, n_buckets=3)
    train, test = split_by_date(obs, train_frac=0.5)
    assert not train.empty and not test.empty
    assert train["date"].max() < test["date"].min()  # strictly earlier, no overlap
    assert len(train) + len(test) == len(obs)


def test_split_by_date_degenerate() -> None:
    train, test = split_by_date(pd.DataFrame(), train_frac=0.5)
    assert train.empty and test.empty


def test_state_ranking_orders_by_hit_rate() -> None:
    obs = pd.DataFrame(
        {
            "bucket": ["weak", "weak", "strong", "strong"],
            "fwd_ret": [-0.1, -0.2, 0.1, 0.3],
        }
    )
    table = conditional_outcome_table(obs, labels=["weak", "mid", "strong"])
    assert state_ranking(table) == ["strong", "weak"]  # strong hit_rate 1.0 > weak 0.0


def test_rotation_outcomes_end_to_end_shape() -> None:
    panel = _panel()
    table = rotation_outcomes(panel, lookback=10, horizon=10, n_buckets=3)
    assert table["state"].tolist()[-1] == "ALL"
    assert set(table["state"]) <= {"weak", "mid", "strong", "ALL"}
    assert (table["n"] > 0).all()
    # hit_rate is a probability
    assert ((table["hit_rate"] >= 0) & (table["hit_rate"] <= 1)).all()
