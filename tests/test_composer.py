"""Tests for compose_ohlcv — provenance, overlap policy, edge cases."""

from __future__ import annotations

import pandas as pd
import pytest

from src.ingestion.composer import OHLCV_COLUMNS, compose_ohlcv


def _frame(dates: list[str], close: list[float]) -> pd.DataFrame:
    idx = pd.to_datetime(dates, utc=True)
    idx.name = "timestamp"
    return pd.DataFrame(
        {
            "open": close,
            "high": [c * 1.01 for c in close],
            "low": [c * 0.99 for c in close],
            "close": close,
            "volume": [1000.0] * len(close),
        },
        index=idx,
    )


def test_compose_empty_input_raises() -> None:
    with pytest.raises(ValueError, match="at least one source"):
        compose_ohlcv([])


def test_compose_all_empty_frames_returns_empty() -> None:
    empty = pd.DataFrame(columns=OHLCV_COLUMNS, index=pd.DatetimeIndex([], tz="UTC"))
    result = compose_ohlcv([(empty, "a"), (empty, "b")])
    assert result.empty
    assert list(result.columns) == [*OHLCV_COLUMNS, "source"]


def test_compose_missing_columns_raises() -> None:
    bad = pd.DataFrame(
        {"open": [1.0], "close": [1.0]},
        index=pd.to_datetime(["2020-01-01"], utc=True),
    )
    with pytest.raises(ValueError, match="missing columns"):
        compose_ohlcv([(bad, "incomplete")])


def test_compose_no_overlap_preserves_both() -> None:
    yh = _frame(["2020-01-01", "2020-01-02"], [10.0, 11.0])
    bn = _frame(["2020-01-03", "2020-01-04"], [12.0, 13.0])

    result = compose_ohlcv([(yh, "yahoo"), (bn, "binance")])

    assert len(result) == 4
    assert result.index.is_monotonic_increasing
    assert result.loc[result.index[0], "source"] == "yahoo"
    assert result.loc[result.index[-1], "source"] == "binance"


def test_compose_overlap_later_source_wins() -> None:
    yh = _frame(["2020-01-01", "2020-01-02", "2020-01-03"], [10.0, 11.0, 12.0])
    bn = _frame(["2020-01-02", "2020-01-03", "2020-01-04"], [11.5, 12.5, 13.5])

    result = compose_ohlcv([(yh, "yahoo"), (bn, "binance")])

    assert len(result) == 4
    # Day 1 only Yahoo, day 2-3 Binance wins (later-listed), day 4 only Binance
    assert result.loc[pd.Timestamp("2020-01-01", tz="UTC"), "source"] == "yahoo"
    assert result.loc[pd.Timestamp("2020-01-02", tz="UTC"), "source"] == "binance"
    assert result.loc[pd.Timestamp("2020-01-02", tz="UTC"), "close"] == 11.5
    assert result.loc[pd.Timestamp("2020-01-03", tz="UTC"), "source"] == "binance"
    assert result.loc[pd.Timestamp("2020-01-04", tz="UTC"), "source"] == "binance"


def test_compose_three_sources_priority_chain() -> None:
    a = _frame(["2020-01-01", "2020-01-02"], [1.0, 2.0])
    b = _frame(["2020-01-02", "2020-01-03"], [20.0, 30.0])
    c = _frame(["2020-01-03"], [300.0])

    result = compose_ohlcv([(a, "a"), (b, "b"), (c, "c")])

    assert result.loc[pd.Timestamp("2020-01-01", tz="UTC"), "source"] == "a"
    assert result.loc[pd.Timestamp("2020-01-02", tz="UTC"), "source"] == "b"
    assert result.loc[pd.Timestamp("2020-01-02", tz="UTC"), "close"] == 20.0
    assert result.loc[pd.Timestamp("2020-01-03", tz="UTC"), "source"] == "c"
    assert result.loc[pd.Timestamp("2020-01-03", tz="UTC"), "close"] == 300.0


def test_compose_one_empty_one_non_empty() -> None:
    empty = pd.DataFrame(columns=OHLCV_COLUMNS, index=pd.DatetimeIndex([], tz="UTC"))
    yh = _frame(["2020-01-01"], [10.0])
    result = compose_ohlcv([(empty, "empty"), (yh, "yahoo")])
    assert len(result) == 1
    assert result.loc[result.index[0], "source"] == "yahoo"
