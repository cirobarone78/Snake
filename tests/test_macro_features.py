"""Offline tests for point-in-time-safe macro features (Fase 4). No network."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.features.macro_features import (
    align_macro_to_index,
    apply_publication_lag,
    build_macro_features,
    load_fred_series,
    to_daily,
    yoy_change,
)


def _monthly(values: list[float], start: str = "2024-01-01") -> pd.Series:
    idx = pd.date_range(start, periods=len(values), freq="MS", tz="UTC")
    idx.name = "timestamp"
    return pd.Series(values, index=idx, name="CPIAUCSL")


# --- publication lag ---


def test_publication_lag_shifts_forward() -> None:
    s = _monthly([100.0, 101.0])
    lagged = apply_publication_lag(s, 45)
    # Jan reference (2024-01-01) becomes available 45 days later
    assert lagged.index[0] == pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=45)
    assert lagged.iloc[0] == 100.0


def test_publication_lag_zero_is_noop() -> None:
    s = _monthly([1.0, 2.0])
    assert apply_publication_lag(s, 0).equals(s)


def test_publication_lag_negative_rejected() -> None:
    with pytest.raises(ValueError, match="look-ahead"):
        apply_publication_lag(_monthly([1.0]), -1)


# --- to_daily (step function, no back-fill) ---


def test_to_daily_forward_fills_not_backfills() -> None:
    s = _monthly([100.0, 110.0])  # Jan, Feb
    daily = to_daily(s)
    # a mid-January day holds the January value
    assert daily.loc["2024-01-15"] == 100.0
    # the value steps up only from the February reference date onward
    assert daily.loc["2024-02-01"] == 110.0
    assert daily.loc["2024-01-31"] == 100.0
    # no value exists before the first observation (no back-fill)
    assert daily.index.min() == pd.Timestamp("2024-01-01", tz="UTC")


# --- align to price index (no look-ahead) ---


def test_align_macro_no_lookahead() -> None:
    # monthly value released (already lagged) on the 1st; price bars are daily
    s = pd.Series(
        [5.0, 6.0],
        index=pd.DatetimeIndex(["2024-01-10", "2024-02-10"], tz="UTC", name="timestamp"),
        name="x",
    )
    price_idx = pd.DatetimeIndex(
        pd.date_range("2024-01-01", "2024-02-28", freq="D", tz="UTC"), name="date"
    )
    aligned = align_macro_to_index(s, price_idx)
    # before the first release: NaN (model has no macro yet, never guessed)
    assert np.isnan(aligned.loc["2024-01-05"])
    # on/after first release: the released value, held until next release
    assert aligned.loc["2024-01-10"] == 5.0
    assert aligned.loc["2024-02-09"] == 5.0
    assert aligned.loc["2024-02-10"] == 6.0


def test_align_empty_series() -> None:
    price_idx = pd.DatetimeIndex(pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC"))
    aligned = align_macro_to_index(pd.Series(dtype="float64", name="x"), price_idx)
    assert len(aligned) == 5
    assert aligned.isna().all()


# --- yoy ---


def test_yoy_change_one_year_back() -> None:
    idx = pd.date_range("2024-01-01", periods=400, freq="D", tz="UTC")
    s = pd.Series(np.arange(400.0), index=idx, name="CPIAUCSL")
    yoy = yoy_change(s, periods=365)
    assert yoy.name == "CPIAUCSL_yoy"
    # linear ramp of +1/day over 365 days -> YoY change == 365
    assert np.isclose(yoy.iloc[365], 365.0)
    assert np.isnan(yoy.iloc[0])


# --- build_macro_features end-to-end on a tmp FRED dir ---


def _write_series(base: Path, freq: str, sid: str, s: pd.Series) -> None:
    d = base / freq
    d.mkdir(parents=True, exist_ok=True)
    frame = s.to_frame("value")
    frame.index.name = "timestamp"
    frame.to_parquet(d / f"{sid}.parquet")


def test_build_macro_features_causal_and_columns(tmp_path: Path) -> None:
    # daily rates (lag 0) + one monthly series (lagged)
    didx = pd.date_range("2024-01-01", periods=400, freq="D", tz="UTC")
    _write_series(tmp_path, "D", "DGS2", pd.Series(np.full(400, 4.0), index=didx))
    _write_series(tmp_path, "D", "DGS10", pd.Series(np.full(400, 4.5), index=didx))
    _write_series(tmp_path, "D", "DFF", pd.Series(np.full(400, 5.0), index=didx))
    midx = pd.date_range("2024-01-01", periods=13, freq="MS", tz="UTC")
    _write_series(tmp_path, "M", "CPIAUCSL", pd.Series(np.arange(13.0) + 300, index=midx))

    price_idx = pd.DatetimeIndex(
        pd.date_range("2024-06-01", periods=60, freq="D", tz="UTC"), name="date"
    )
    feats = build_macro_features(price_idx, fred_dir=tmp_path)

    assert "yield_curve_slope" in feats.columns
    assert np.allclose(feats["yield_curve_slope"].dropna(), 0.5)
    assert "fed_funds" in feats.columns
    assert "cpi_yoy" in feats.columns
    # series absent from disk simply don't appear (graceful degrade)
    assert "broad_dollar" not in feats.columns
    assert feats.index.equals(price_idx)


def test_build_macro_features_missing_dir_degrades(tmp_path: Path) -> None:
    price_idx = pd.DatetimeIndex(pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC"))
    feats = build_macro_features(price_idx, fred_dir=tmp_path / "nope")
    # nothing on disk -> empty feature frame (no columns), but right index
    assert feats.index.equals(price_idx)
    assert feats.shape[1] == 0


def test_load_fred_series_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="not found"):
        load_fred_series("NOPE", tmp_path)
