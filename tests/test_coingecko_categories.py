"""Tests for CoinGeckoSource.fetch_categories parsing/filtering (Fase 6). No network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.ingestion.tier1.coingecko import CoinGeckoSource


def _resp(json_data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_data
    m.raise_for_status = MagicMock()
    return m


def _source() -> CoinGeckoSource:
    return CoinGeckoSource(sleep_between_calls=0.0, max_retries=1, backoff_base=0.0)


_PAYLOAD = [
    {
        "id": "ai",
        "name": "AI",
        "market_cap": 50e9,
        "volume_24h": 10e9,
        "market_cap_change_24h": 8.0,
        "top_3_coins_id": ["near", "bittensor", "fetch-ai"],
    },
    {
        "id": "rwa",
        "name": "RWA",
        "market_cap": 20e9,
        "volume_24h": 1e9,
        "market_cap_change_24h": 3.0,
        "top_3_coins_id": ["ondo", "chainlink"],
    },
    {
        "id": "pump",
        "name": "MicroPump",
        "market_cap": 5e6,
        "volume_24h": 4e6,
        "market_cap_change_24h": 420.0,
        "top_3_coins_id": ["scam"],
    },
]


def test_fetch_categories_parses_columns() -> None:
    src = _source()
    with patch.object(src._session, "get", return_value=_resp(_PAYLOAD)):
        df = src.fetch_categories()
    assert list(df.columns) == [
        "category_id",
        "name",
        "market_cap",
        "volume_24h",
        "change_24h_pct",
        "top_coins",
    ]
    assert df.index.name == "rank"
    # top_3_coins_id joined into a comma string
    ai = df[df["category_id"] == "ai"].iloc[0]
    assert ai["top_coins"] == "near,bittensor,fetch-ai"


def test_fetch_categories_sorted_by_market_cap() -> None:
    src = _source()
    with patch.object(src._session, "get", return_value=_resp(_PAYLOAD)):
        df = src.fetch_categories()
    # AI (50B) before RWA (20B)
    assert df.iloc[0]["category_id"] == "ai"
    assert df.iloc[1]["category_id"] == "rwa"


def test_fetch_categories_min_market_cap_filters() -> None:
    src = _source()
    with patch.object(src._session, "get", return_value=_resp(_PAYLOAD)):
        df = src.fetch_categories(min_market_cap=1e8)
    # the 5M micro-cap pump is filtered out
    assert "pump" not in df["category_id"].tolist()
    assert len(df) == 2
