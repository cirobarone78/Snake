"""Tests for the Bitcoin halving cycle features (Fase 5). No network."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.cycles import (
    HALVING_DATES,
    days_since_last_halving,
    days_to_next_halving,
    halving_cycle_phase,
    halving_features,
)


def test_days_since_halving_known_value() -> None:
    # 10 days after the 2024-04-20 halving
    idx = pd.DatetimeIndex(["2024-04-30"], tz="UTC")
    since = days_since_last_halving(idx)
    assert since.iloc[0] == 10.0


def test_days_since_halving_nan_before_first() -> None:
    idx = pd.DatetimeIndex(["2010-01-01"], tz="UTC")  # before 2012 halving
    assert np.isnan(days_since_last_halving(idx).iloc[0])


def test_days_to_next_halving_known_value() -> None:
    # 2024-04-10 is 10 days before the 2024-04-20 halving
    idx = pd.DatetimeIndex(["2024-04-10"], tz="UTC")
    to = days_to_next_halving(idx)
    assert to.iloc[0] == 10.0


def test_days_to_next_halving_nan_after_last() -> None:
    last = max(HALVING_DATES) + pd.Timedelta(days=1)
    idx = pd.DatetimeIndex([last])
    assert np.isnan(days_to_next_halving(idx).iloc[0])


def test_cycle_phase_resets_near_halving() -> None:
    # day after a halving -> phase near 0; just before next -> phase near 1
    just_after = pd.DatetimeIndex(["2024-04-21"], tz="UTC")
    near_next = pd.DatetimeIndex(["2028-04-10"], tz="UTC")
    p_after = halving_cycle_phase(just_after).iloc[0]
    p_before = halving_cycle_phase(near_next).iloc[0]
    assert 0.0 <= p_after < 0.05
    assert p_before > 0.9
    assert p_before < 1.0  # clipped below 1


def test_halving_features_shape_and_causality() -> None:
    idx = pd.date_range("2021-01-01", "2026-01-01", freq="D", tz="UTC")
    feats = halving_features(idx)
    assert list(feats.columns) == ["days_since_halving", "days_to_halving", "halving_phase"]
    # monotonic ramp of days_since between two halvings (2024-04-20 to next)
    seg = feats.loc["2024-05-01":"2024-12-31", "days_since_halving"]
    assert seg.is_monotonic_increasing
    # purely calendar-derived: recomputing on a truncated index gives same values
    feats_trunc = halving_features(pd.DatetimeIndex(idx[:500]))
    assert np.allclose(
        feats["halving_phase"].iloc[:500].to_numpy(),
        feats_trunc["halving_phase"].to_numpy(),
        equal_nan=True,
    )
