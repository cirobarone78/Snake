"""Offline tests for data freshness checks (Fase 8 hardening). No network."""

from __future__ import annotations

import pandas as pd

from src.ingestion.freshness import check_freshness, last_timestamp_of

_NOW = pd.Timestamp("2026-06-05", tz="UTC")


def test_fresh_when_recent() -> None:
    last = pd.Timestamp("2026-06-04", tz="UTC")
    r = check_freshness(last, max_age_days=3, name="btc", now=_NOW)
    assert r.is_fresh
    assert r.age_days is not None and r.age_days < 3
    assert "OK" in r.message()


def test_stale_when_old() -> None:
    # the exact MATIC-USD failure: frozen ~70 days ago
    last = pd.Timestamp("2026-03-27", tz="UTC")
    r = check_freshness(last, max_age_days=3, name="POL", now=_NOW)
    assert not r.is_fresh
    assert r.age_days is not None and r.age_days > 60
    assert "STALE" in r.message()


def test_none_is_not_fresh() -> None:
    r = check_freshness(None, max_age_days=3, name="empty", now=_NOW)
    assert not r.is_fresh
    assert r.last_timestamp is None
    assert "nessun dato" in r.message()


def test_tz_naive_input_handled() -> None:
    last = pd.Timestamp("2026-06-04")  # naive
    r = check_freshness(last, max_age_days=3, name="x", now=_NOW)
    assert r.is_fresh  # treated as UTC, no crash


def test_boundary_exactly_at_threshold_is_fresh() -> None:
    last = _NOW - pd.Timedelta(days=3)
    r = check_freshness(last, max_age_days=3, name="x", now=_NOW)
    assert r.is_fresh  # <= threshold counts as fresh


def test_last_timestamp_of_index() -> None:
    idx = pd.DatetimeIndex(["2026-06-01", "2026-06-04", "2026-06-02"], tz="UTC")
    frame = pd.DataFrame({"v": [1, 2, 3]}, index=idx)
    assert last_timestamp_of(frame) == pd.Timestamp("2026-06-04", tz="UTC")


def test_last_timestamp_of_column() -> None:
    frame = pd.DataFrame(
        {"snapshot_at": pd.to_datetime(["2026-06-01", "2026-06-05"], utc=True), "v": [1, 2]}
    )
    assert last_timestamp_of(frame, column="snapshot_at") == pd.Timestamp("2026-06-05", tz="UTC")


def test_last_timestamp_of_empty() -> None:
    assert last_timestamp_of(pd.DataFrame()) is None
