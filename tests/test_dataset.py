"""Offline tests for the multifactor design matrix (Fase 4). No network."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features.dataset import (
    assemble_design_matrix,
    directional_target,
    technical_features,
)


def _ohlcv(n: int = 120, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    close = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)), index=idx)
    high = close + rng.uniform(0, 2, n)
    low = close - rng.uniform(0, 2, n)
    return pd.DataFrame(
        {"open": close, "high": high, "low": low, "close": close, "volume": rng.uniform(1, 10, n)},
        index=idx,
    )


def test_technical_features_columns_and_causal() -> None:
    ohlcv = _ohlcv()
    feats = technical_features(ohlcv)
    assert set(feats.columns) == {"sma_gap", "macd_hist", "rsi_14", "atr_pct", "ret_1d"}
    # appending a future bar must not change a past feature value (causality)
    feats2 = technical_features(_ohlcv(121))
    assert np.isclose(feats["rsi_14"].iloc[60], feats2["rsi_14"].iloc[60], equal_nan=True)


def test_directional_target_is_binary() -> None:
    close = pd.Series(
        [100.0, 101.0, 100.5, 100.5, 102.0],
        index=pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC"),
    )
    y = directional_target(close)
    # t0 has no prior return (NaN -> 0.0); then up, down, flat(->0), up
    assert y.tolist() == [0.0, 1.0, 0.0, 0.0, 1.0]
    assert set(y.unique()).issubset({0.0, 1.0})


def test_assemble_no_lookahead() -> None:
    # the feature row at t must be the state at t-1: X[t]'s ret_1d == close.pct_change()[t-1]
    ohlcv = _ohlcv()
    x, y = assemble_design_matrix(ohlcv, feature_lag=1)
    ret = ohlcv["close"].pct_change()
    # pick a label t well past warm-up
    t = x.index[20]
    t_prev = ohlcv.index[ohlcv.index.get_loc(t) - 1]
    assert np.isclose(x.loc[t, "ret_1d"], ret.loc[t_prev])
    # target at t is the direction of the return realised AT t (not lagged)
    assert y.loc[t] == float(ret.loc[t] > 0)


def test_assemble_rejects_zero_lag() -> None:
    with pytest.raises(ValueError, match="feature_lag must be >= 1"):
        assemble_design_matrix(_ohlcv(), feature_lag=0)


def test_assemble_joins_extra_features() -> None:
    ohlcv = _ohlcv()
    # a sparse macro-like feature; should be ffilled then lagged
    macro = pd.DataFrame(
        {"cpi_yoy": [2.0, 2.5]},
        index=pd.DatetimeIndex(["2024-01-01", "2024-03-01"], tz="UTC"),
    )
    x, y = assemble_design_matrix(ohlcv, extra_features=macro)
    assert "cpi_yoy" in x.columns
    assert len(x) == len(y)
    assert not x.isna().any().any()  # rows with NaN dropped


def test_assemble_aligned_and_no_nan() -> None:
    x, y = assemble_design_matrix(_ohlcv())
    assert x.index.equals(y.index)
    assert not x.isna().any().any()
    assert len(x) > 0
