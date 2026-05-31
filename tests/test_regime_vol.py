"""Tests for volatility regime, 4-state combination, and generic summary (Fase 5)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features.regime import (
    Regime,
    VolRegime,
    classify_vol_regime,
    combine_regimes,
    summarize_by_regime,
)


def _returns(values: list[float], start: str = "2020-01-01") -> pd.Series:
    idx = pd.date_range(start, periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=idx, name="ret")


# --- classify_vol_regime ---


def test_vol_regime_warmup_is_unknown() -> None:
    r = _returns(list(np.random.default_rng(0).normal(0, 0.01, 60)))
    vol = classify_vol_regime(r, vol_window=10, baseline_window=20)
    # need vol_window for vol + baseline_window for the (shifted) baseline median
    assert (vol.iloc[:10] == VolRegime.UNKNOWN.value).all()


def test_vol_regime_detects_high_low() -> None:
    rng = np.random.default_rng(1)
    calm = list(rng.normal(0, 0.005, 200))
    storm = list(rng.normal(0, 0.05, 60))  # 10x vol
    r = _returns(calm + storm)
    vol = classify_vol_regime(r, vol_window=20, baseline_window=100)
    decided = vol[vol != VolRegime.UNKNOWN.value]
    # the storm tail must be classified high_vol
    assert (vol.iloc[-30:] == VolRegime.HIGH.value).all()
    # and somewhere in the calm stretch we see low_vol
    assert (decided == VolRegime.LOW.value).any()


def test_vol_regime_is_causal() -> None:
    r = _returns(list(np.random.default_rng(2).normal(0, 0.02, 150)))
    vol_full = classify_vol_regime(r, vol_window=10, baseline_window=30)
    # appending a future return must not change a past label
    r_ext = pd.concat([r, _returns([0.5], start="2020-06-30")])
    vol_ext = classify_vol_regime(r_ext, vol_window=10, baseline_window=30)
    assert vol_full.iloc[100] == vol_ext.iloc[100]


def test_vol_regime_rejects_bad_windows() -> None:
    r = _returns([0.01, 0.02, 0.03])
    with pytest.raises(ValueError, match="vol_window"):
        classify_vol_regime(r, vol_window=1)
    with pytest.raises(ValueError, match="baseline_window"):
        classify_vol_regime(r, vol_window=2, baseline_window=0)


# --- combine_regimes ---


def test_combine_regimes_4_states_and_unknown_propagates() -> None:
    idx = pd.date_range("2020-01-01", periods=5, freq="D", tz="UTC")
    trend = pd.Series(
        [
            Regime.UNKNOWN.value,
            Regime.BULL.value,
            Regime.BULL.value,
            Regime.BEAR.value,
            Regime.BEAR.value,
        ],
        index=idx,
    )
    vol = pd.Series(
        [
            VolRegime.LOW.value,
            VolRegime.LOW.value,
            VolRegime.HIGH.value,
            VolRegime.HIGH.value,
            VolRegime.UNKNOWN.value,
        ],
        index=idx,
    )
    combined = combine_regimes(trend, vol)
    assert combined.iloc[0] == "unknown"  # trend unknown -> unknown
    assert combined.iloc[1] == "bull_low_vol"
    assert combined.iloc[2] == "bull_high_vol"
    assert combined.iloc[3] == "bear_high_vol"
    assert combined.iloc[4] == "unknown"  # vol unknown -> unknown


# --- generic summarize_by_regime ---


def test_summarize_by_regime_generic_labels() -> None:
    idx = pd.date_range("2020-01-01", periods=6, freq="D", tz="UTC")
    returns = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02, -0.03], index=idx)
    regime = pd.Series(
        ["high_vol", "high_vol", "low_vol", "low_vol", "unknown", "low_vol"], index=idx
    )
    out = summarize_by_regime(returns, regime)
    assert "full" in out
    assert "high_vol" in out and "low_vol" in out
    assert "unknown" not in out  # warm-up excluded
    # full covers all non-NaN returns (6); the regimes partition the known ones
    assert out["full"].n_periods == 6
