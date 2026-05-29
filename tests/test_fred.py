"""Tests for FredSource — parsing, missing values, error mapping. No network."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.ingestion.tier1.fred import FredSource, _observations_to_frame


def _resp(payload: Any, status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    r.raise_for_status = MagicMock()
    if status >= 400 and status != 429 and status != 400:
        r.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return r


def test_init_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(ValueError, match="FRED API key"):
        FredSource()


def test_init_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRED_API_KEY", "envkey")
    src = FredSource()
    assert src._api_key == "envkey"


def test_init_explicit_api_key_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRED_API_KEY", "envkey")
    src = FredSource(api_key="explicit")
    assert src._api_key == "explicit"


def test_observations_to_frame_parses_values_and_handles_missing() -> None:
    rows = [
        {"date": "2020-01-01", "value": "1.5"},
        {"date": "2020-01-02", "value": "."},  # FRED missing sentinel
        {"date": "2020-01-03", "value": "1.8"},
    ]
    df = _observations_to_frame(rows)
    assert list(df.columns) == ["value"]
    assert len(df) == 3
    assert df.index.name == "timestamp"
    assert str(df.index.tz) == "UTC"
    assert df.iloc[0]["value"] == 1.5
    assert pd.isna(df.iloc[1]["value"])
    assert df.iloc[2]["value"] == 1.8


def test_observations_to_frame_empty() -> None:
    df = _observations_to_frame([])
    assert df.empty
    assert list(df.columns) == ["value"]
    assert df.index.name == "timestamp"


def test_observations_to_frame_sorts_by_date() -> None:
    rows = [
        {"date": "2020-01-03", "value": "3.0"},
        {"date": "2020-01-01", "value": "1.0"},
        {"date": "2020-01-02", "value": "2.0"},
    ]
    df = _observations_to_frame(rows)
    assert df.index.is_monotonic_increasing
    assert list(df["value"]) == [1.0, 2.0, 3.0]


def test_fetch_series_sends_correct_params() -> None:
    session = MagicMock()
    session.get.return_value = _resp({
        "observations": [{"date": "2020-01-01", "value": "1.0"}],
    })
    src = FredSource(api_key="k", session=session, sleep_between_calls=0)
    df = src.fetch_series("DFF", observation_start="2020-01-01", observation_end="2020-12-31")

    args, kwargs = session.get.call_args
    assert args[0].endswith("/series/observations")
    assert kwargs["params"]["series_id"] == "DFF"
    assert kwargs["params"]["observation_start"] == "2020-01-01"
    assert kwargs["params"]["observation_end"] == "2020-12-31"
    assert kwargs["params"]["api_key"] == "k"
    assert kwargs["params"]["file_type"] == "json"
    assert not df.empty


def test_fetch_series_info_returns_first_record() -> None:
    session = MagicMock()
    session.get.return_value = _resp({
        "seriess": [
            {"id": "DFF", "title": "Federal Funds Effective Rate",
             "frequency_short": "D", "units": "Percent"}
        ],
    })
    src = FredSource(api_key="k", session=session, sleep_between_calls=0)
    info = src.fetch_series_info("DFF")
    assert info["id"] == "DFF"
    assert info["frequency_short"] == "D"


def test_fetch_series_info_no_data_raises() -> None:
    session = MagicMock()
    session.get.return_value = _resp({"seriess": []})
    src = FredSource(api_key="k", session=session, sleep_between_calls=0)
    with pytest.raises(RuntimeError, match="no metadata"):
        src.fetch_series_info("NOPE")


def test_http_400_includes_error_message() -> None:
    session = MagicMock()
    session.get.return_value = _resp({"error_message": "Bad API key"}, status=400)
    src = FredSource(api_key="k", session=session, sleep_between_calls=0)
    with pytest.raises(RuntimeError, match="Bad API key"):
        src.fetch_series("DFF")


def test_rate_limit_recovers_after_one_429() -> None:
    session = MagicMock()
    session.get.side_effect = [
        _resp({}, status=429),
        _resp({"observations": [{"date": "2020-01-01", "value": "1.0"}]}),
    ]
    src = FredSource(
        api_key="k", session=session, sleep_between_calls=0,
        max_retries=3, backoff_base=0,
    )
    df = src.fetch_series("DFF")
    assert len(df) == 1
    assert session.get.call_count == 2


def test_rate_limit_exhausted_raises() -> None:
    session = MagicMock()
    session.get.return_value = _resp({}, status=429)
    src = FredSource(
        api_key="k", session=session, sleep_between_calls=0,
        max_retries=2, backoff_base=0,
    )
    with pytest.raises(RuntimeError, match="rate limit"):
        src.fetch_series("DFF")
    # 1 initial + 2 retries
    assert session.get.call_count == 3
