"""Tests for CoinGeckoSource — payload parsing, snapshot framing, error mapping."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.ingestion.tier1.coingecko import (
    CoinGeckoSource,
    _market_chart_to_frame,
)


def _resp(payload: Any, status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    r.raise_for_status = MagicMock()
    if status >= 400 and status != 429:
        r.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return r


def test_market_chart_to_frame_parses_three_arrays() -> None:
    ms_d1 = 1_577_836_800_000  # 2020-01-01 UTC
    ms_d2 = ms_d1 + 86_400_000
    payload = {
        "prices": [[ms_d1, 7200.0], [ms_d2, 7300.0]],
        "market_caps": [[ms_d1, 1.3e11], [ms_d2, 1.32e11]],
        "total_volumes": [[ms_d1, 2e10], [ms_d2, 2.1e10]],
    }
    df = _market_chart_to_frame(payload)
    assert list(df.columns) == ["price", "market_cap", "volume"]
    assert len(df) == 2
    assert df.index.name == "timestamp"
    assert df.iloc[0]["price"] == 7200.0


def test_market_chart_floors_to_date_and_keeps_latest_intraday() -> None:
    base = 1_577_836_800_000  # 2020-01-01 00:00 UTC
    intraday1 = base + 30_000_000   # ~08:20 same day
    intraday2 = base + 60_000_000   # ~16:40 same day
    payload = {
        "prices": [[base, 100.0], [intraday1, 110.0], [intraday2, 120.0]],
        "market_caps": [],
        "total_volumes": [],
    }
    df = _market_chart_to_frame(payload)
    assert len(df) == 1
    # 120.0 is the latest of the day -> wins
    assert df.iloc[0]["price"] == 120.0


def test_market_chart_empty_payload_returns_empty_frame() -> None:
    df = _market_chart_to_frame({"prices": [], "market_caps": [], "total_volumes": []})
    assert df.empty
    assert list(df.columns) == ["price", "market_cap", "volume"]


def test_fetch_global_extracts_dominance_and_totals() -> None:
    session = MagicMock()
    session.get.return_value = _resp({
        "data": {
            "market_cap_percentage": {"btc": 50.5, "eth": 17.2, "usdt": 5.1},
            "total_market_cap": {"usd": 2.5e12},
            "total_volume": {"usd": 1.0e11},
            "active_cryptocurrencies": 15000,
        }
    })
    src = CoinGeckoSource(session=session, sleep_between_calls=0)
    df = src.fetch_global()
    assert df.shape[0] == 1
    assert df.iloc[0]["btc_dom"] == 50.5
    assert df.iloc[0]["eth_dom"] == 17.2
    assert df.iloc[0]["usdt_dom"] == 5.1
    assert df.iloc[0]["total_market_cap_usd"] == 2.5e12
    assert df.iloc[0]["active_cryptocurrencies"] == 15000.0


def test_fetch_top_n_returns_ranked_frame() -> None:
    session = MagicMock()
    session.get.return_value = _resp([
        {
            "symbol": "btc", "name": "Bitcoin", "market_cap": 1e12,
            "current_price": 50000, "total_volume": 3e10,
            "price_change_percentage_24h": 2.5, "market_cap_rank": 1,
        },
        {
            "symbol": "eth", "name": "Ethereum", "market_cap": 4e11,
            "current_price": 3000, "total_volume": 2e10,
            "price_change_percentage_24h": -1.2, "market_cap_rank": 2,
        },
    ])
    src = CoinGeckoSource(session=session, sleep_between_calls=0)
    df = src.fetch_top_n(n=2)
    assert list(df.index) == [1, 2]
    assert df.loc[1, "symbol"] == "btc"
    assert df.loc[1, "price_change_24h_pct"] == 2.5


def test_rate_limit_raises_runtime_error_after_max_retries() -> None:
    session = MagicMock()
    session.get.return_value = _resp({}, status=429)
    src = CoinGeckoSource(
        session=session,
        sleep_between_calls=0,
        max_retries=2,
        backoff_base=0,
    )
    with pytest.raises(RuntimeError, match="rate limit"):
        src.fetch_global()
    # 1 initial + 2 retries = 3 attempts
    assert session.get.call_count == 3


def test_rate_limit_recovers_after_one_429() -> None:
    session = MagicMock()
    session.get.side_effect = [
        _resp({}, status=429),
        _resp({"data": {"market_cap_percentage": {"btc": 50.0}}}),
    ]
    src = CoinGeckoSource(
        session=session,
        sleep_between_calls=0,
        max_retries=3,
        backoff_base=0,
    )
    df = src.fetch_global()
    assert df.iloc[0]["btc_dom"] == 50.0
    assert session.get.call_count == 2


def test_demo_api_key_is_sent_as_header() -> None:
    session = MagicMock()
    session.get.return_value = _resp({"data": {"market_cap_percentage": {}}})
    src = CoinGeckoSource(api_key="DEMO123", session=session, sleep_between_calls=0)
    src.fetch_global()
    _, kwargs = session.get.call_args
    assert kwargs["headers"]["x-cg-demo-api-key"] == "DEMO123"


def test_fetch_market_chart_passes_params() -> None:
    session = MagicMock()
    session.get.return_value = _resp({
        "prices": [[1_577_836_800_000, 7200.0]],
        "market_caps": [],
        "total_volumes": [],
    })
    src = CoinGeckoSource(session=session, sleep_between_calls=0)
    df = src.fetch_market_chart("bitcoin", days=180, vs_currency="eur")

    args, kwargs = session.get.call_args
    assert "/coins/bitcoin/market_chart" in args[0]
    assert kwargs["params"] == {"vs_currency": "eur", "days": 180}
    assert not df.empty


def test_fetch_markets_returns_the_extra_screening_fields() -> None:
    session = MagicMock()
    session.get.return_value = _resp([
        {
            "id": "bitcoin", "symbol": "btc", "name": "Bitcoin",
            "market_cap": 1e12, "market_cap_rank": 1, "current_price": 100000.0,
            "total_volume": 3e10, "price_change_percentage_24h": 1.4,
            "ath_change_percentage": -38.0, "atl_date": "2013-07-05T16:00:00.000Z",
        },
        {
            "id": "ethereum", "symbol": "eth", "name": "Ethereum",
            "market_cap": 3e11, "market_cap_rank": 2, "current_price": 2500.0,
            "total_volume": 1.7e10, "price_change_percentage_24h": 2.1,
            "ath_change_percentage": -49.0, "atl_date": "2015-10-19T16:00:00.000Z",
        },
    ])
    src = CoinGeckoSource(session=session, sleep_between_calls=0)
    df = src.fetch_markets(n=2)
    assert list(df.index) == [1, 2]
    # Upper-cased so it joins against the project's canonical symbols.
    assert df.loc[1, "symbol"] == "BTC"
    assert df.loc[1, "coingecko_id"] == "bitcoin"
    assert df.loc[2, "atl_date"] == "2015-10-19T16:00:00.000Z"
    assert df.loc[1, "ath_change_pct"] == -38.0
