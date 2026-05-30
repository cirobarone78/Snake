"""Offline tests for news-derived features + lead/lag (Fase 3). No network."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.news_features import (
    build_news_features,
    lead_lag_table,
    news_volume_zscore,
    rolling_mean_sentiment,
    sentiment_change,
)


def _daily(n: int = 40, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")
    idx.name = "date"
    return pd.DataFrame(
        {
            "mean_sentiment": rng.normal(0, 0.3, n),
            "news_count": rng.integers(1, 20, n).astype("int64"),
        },
        index=idx,
    )


# --- rolling / change ---


def test_rolling_mean_is_causal() -> None:
    daily = _daily()
    roll = rolling_mean_sentiment(daily, window=5)
    # value at t equals mean of mean_sentiment over the trailing 5 days <= t
    expected = daily["mean_sentiment"].iloc[5:10].mean()
    assert np.isclose(roll.iloc[9], expected)
    # appending a future row must not change a past value (causality)
    extended = pd.concat(
        [
            daily,
            _daily(1, seed=99).set_axis(
                pd.DatetimeIndex([daily.index[-1] + pd.Timedelta(days=1)], name="date")
            ),
        ]
    )
    roll2 = rolling_mean_sentiment(extended, window=5)
    assert np.isclose(roll.iloc[9], roll2.iloc[9])


def test_sentiment_change_is_diff() -> None:
    daily = _daily()
    chg = sentiment_change(daily)
    assert np.isnan(chg.iloc[0])
    assert np.isclose(
        chg.iloc[5], daily["mean_sentiment"].iloc[5] - daily["mean_sentiment"].iloc[4]
    )


# --- volume z-score ---


def test_volume_zscore_no_lookahead_and_finite() -> None:
    daily = _daily()
    z = news_volume_zscore(daily, window=10, min_periods=3)
    # baseline uses shift(1) so the current day is excluded from its own mean/std
    # -> no NaN/inf explosions, and early warm-up is NaN
    assert z.iloc[:3].isna().all()
    assert np.isfinite(z.dropna().to_numpy()).all()


def test_volume_zscore_constant_count_is_nan() -> None:
    idx = pd.date_range("2025-01-01", periods=20, freq="D", tz="UTC")
    daily = pd.DataFrame(
        {"mean_sentiment": 0.0, "news_count": np.full(20, 5, dtype="int64")}, index=idx
    )
    z = news_volume_zscore(daily, window=10, min_periods=3)
    # zero variance -> z is NaN, never inf
    assert z.dropna().empty or np.isfinite(z.dropna().to_numpy()).all()
    assert not np.isinf(z.fillna(0).to_numpy()).any()


# --- build_news_features ---


def test_build_features_columns_and_index() -> None:
    feats = build_news_features(_daily())
    assert list(feats.columns) == [
        "mean_sentiment",
        "sentiment_roll",
        "sentiment_change",
        "news_count",
        "news_volume_z",
    ]
    assert feats.index.name == "date"
    assert str(feats.index.tz) == "UTC"


def test_build_features_empty() -> None:
    feats = build_news_features(
        pd.DataFrame(
            {"mean_sentiment": pd.Series(dtype="float64"), "news_count": pd.Series(dtype="int64")},
            index=pd.DatetimeIndex([], name="date", tz="UTC"),
        )
    )
    assert feats.empty
    assert "news_volume_z" in feats.columns


# --- lead/lag table ---


def test_lead_lag_recovers_known_lead() -> None:
    # construct target[t+2] = feature[t] exactly -> corr at lag +2 must be ~1
    idx = pd.date_range("2025-01-01", periods=60, freq="D", tz="UTC")
    rng = np.random.default_rng(1)
    feat = pd.Series(rng.normal(size=60), index=idx, name="feat")
    target = feat.shift(2).rename("tgt")  # target[t] = feature[t-2] -> feature leads by 2
    table = lead_lag_table(feat, target, lags=range(-3, 4))
    best_lag = table["corr"].idxmax()
    assert best_lag == 2.0
    assert table.loc[2.0, "corr"] > 0.99


def test_lead_lag_reports_n() -> None:
    idx = pd.date_range("2025-01-01", periods=30, freq="D", tz="UTC")
    feat = pd.Series(np.arange(30.0), index=idx)
    target = pd.Series(np.arange(30.0), index=idx)
    table = lead_lag_table(feat, target, lags=range(-2, 3))
    # at lag 0, all 30 overlap; at lag k, |k| fewer
    assert table.loc[0.0, "n"] == 30
    assert table.loc[2.0, "n"] == 28
    assert (table["n"] > 0).all()
