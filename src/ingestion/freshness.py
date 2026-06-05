"""Data freshness checks — catch silently-stale feeds (Fase 8 hardening).

ADR-026 lesson: a *frozen* feed is more dangerous than a missing one. A failed
fetch is loud (the cron logs an error); a feed that keeps returning the same old
value looks fine but quietly poisons every downstream analysis — exactly how the
stale MATIC-USD ticker hid POL's real crash.

This module makes staleness *loud*: given the most-recent timestamp of a series
(or its DataFrame), it tells you whether the data is older than a tolerance, so
ingestion scripts can log a warning (or a workflow can surface it) instead of
trusting old numbers.

Pure functions over timestamps/frames; unit-testable offline, no network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pandas as pd


@dataclass(frozen=True)
class FreshnessResult:
    """Outcome of a freshness check for one data source."""

    name: str
    last_timestamp: pd.Timestamp | None
    age_days: float | None
    max_age_days: float
    is_fresh: bool

    def message(self) -> str:
        """One-line human summary (warning-friendly)."""
        if self.last_timestamp is None:
            return f"⚠️ {self.name}: nessun dato (vuoto)"
        status = "OK" if self.is_fresh else "⚠️ STALE"
        return (
            f"{status} {self.name}: ultimo dato {str(self.last_timestamp)[:10]} "
            f"({self.age_days:.1f}g fa, soglia {self.max_age_days:.0f}g)"
        )


def check_freshness(
    last_timestamp: pd.Timestamp | None,
    max_age_days: float,
    name: str = "series",
    now: pd.Timestamp | None = None,
) -> FreshnessResult:
    """Flag a series as stale if its last timestamp is older than ``max_age_days``.

    ``now`` defaults to the current UTC time. A ``None`` last timestamp (empty
    data) is reported as not fresh. Tz-naive inputs are treated as UTC so the
    subtraction never raises.
    """
    ref = now if now is not None else pd.Timestamp.now(tz="UTC")
    if ref.tzinfo is None:
        ref = ref.tz_localize("UTC")
    if last_timestamp is None:
        return FreshnessResult(name, None, None, max_age_days, is_fresh=False)
    ts = last_timestamp if last_timestamp.tzinfo is not None else last_timestamp.tz_localize("UTC")
    age_days = (ref - ts).total_seconds() / 86400.0
    return FreshnessResult(name, ts, age_days, max_age_days, is_fresh=age_days <= max_age_days)


def last_timestamp_of(frame: pd.DataFrame, column: str | None = None) -> pd.Timestamp | None:
    """Most-recent timestamp of a frame.

    Uses the max of a DatetimeIndex by default; if ``column`` is given, uses the
    max of that (datetime) column instead. Returns ``None`` for empty input.
    """
    if frame.empty:
        return None
    if column is not None:
        ts = cast("pd.Timestamp", pd.to_datetime(frame[column]).max())
    else:
        ts = cast("pd.Timestamp", pd.DatetimeIndex(frame.index).max())
    return None if pd.isna(ts) else cast("pd.Timestamp", pd.Timestamp(ts))
