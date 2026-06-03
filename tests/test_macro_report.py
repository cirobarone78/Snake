"""Offline tests for the macro climate report (Fase 8). No network."""

from __future__ import annotations

import numpy as np

from src.features.macro_report import (
    climate_reading,
    format_macro_report_md,
    yield_curve_slope,
)


def test_yield_curve_slope() -> None:
    assert yield_curve_slope({"DGS10": 4.5, "DGS2": 4.0}) == 0.5
    assert yield_curve_slope({"DGS10": 4.0, "DGS2": 4.6}) < 0  # inverted
    assert yield_curve_slope({"DGS10": 4.0}) is None  # missing 2Y


def test_climate_risk_off() -> None:
    # rates up + dollar up + inverted curve = 3 cautious -> risk-off
    latest = {"DGS10": 4.0, "DGS2": 4.6}
    change = {"DFF": +0.25, "DTWEXBGS": +1.2}
    assert "risk-off" in climate_reading(latest, change)


def test_climate_risk_on() -> None:
    # rates down + dollar down + normal curve = 0 cautious -> risk-on
    latest = {"DGS10": 4.5, "DGS2": 4.0}
    change = {"DFF": -0.25, "DTWEXBGS": -0.8}
    assert "risk-on" in climate_reading(latest, change)


def test_climate_indeterminate() -> None:
    assert "indeterminato" in climate_reading({}, {})


def test_report_has_sections_and_stamp() -> None:
    latest = {
        "DFF": 5.0,
        "DGS2": 4.6,
        "DGS10": 4.0,
        "DTWEXBGS": 100.0,
        "CPIAUCSL": 320.0,
        "M2SL": 21000.0,
        "UNRATE": 4.1,
    }
    change = {"DFF": +0.0, "DTWEXBGS": +0.5}
    md = format_macro_report_md(latest, change, snapshot_at="2026-06-03 12:00")
    assert md.startswith("# ")
    assert "Clima macro" in md
    assert "2026-06-03 12:00" in md
    assert "Curva 10Y-2Y" in md  # slope row present
    assert "non una previsione" in md.lower()


def test_report_empty() -> None:
    md = format_macro_report_md({}, {})
    assert md.startswith("#")
    assert "Nessun dato" in md


def test_report_tolerates_nan_and_partial() -> None:
    latest = {"DFF": 5.0, "DGS10": np.nan}
    md = format_macro_report_md(latest, {})
    assert "Fed funds rate" in md
    assert "n/d" in md  # NaN rendered safely
