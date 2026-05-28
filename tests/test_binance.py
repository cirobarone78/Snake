"""Tests for BinanceSource — parsing, pagination, error mapping. No network."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.assets.asset import Asset, AssetClass
from src.ingestion.tier1.binance import BinanceSource, _klines_to_frame, _to_ms


def _kline_row(open_ms: int, close_px: str = "100.0") -> list[Any]:
    """Build a Binance kline row in the API's positional schema."""
    return [
        open_ms, "99.5", "101.2", "98.7", close_px, "1234.5",
        open_ms + 86_399_999, "123456.7", 100,
        "617.25", "61728.35", "0",
    ]


def _make_response(payload: Any, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp


def test_to_ms_handles_str_and_datetime() -> None:
    # 2020-01-01 00:00:00 UTC = 1577836800000 ms
    assert _to_ms("2020-01-01") == 1_577_836_800_000
    assert _to_ms("2020-01-01T00:00:00+00:00") == 1_577_836_800_000


def test_klines_to_frame_shape_and_dtypes() -> None:
    rows = [_kline_row(1_577_836_800_000 + i * 86_400_000) for i in range(3)]
    df = _klines_to_frame(rows)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.name == "timestamp"
    assert str(df.index.tz) == "UTC"
    assert len(df) == 3
    for col in ("open", "high", "low", "close", "volume"):
        assert pd.api.types.is_float_dtype(df[col]), f"{col} should be float"


def test_klines_to_frame_drops_duplicates_and_sorts() -> None:
    # Two rows at the same open_ms (overlap from pagination) + one earlier
    dup_ms = 1_577_836_800_000
    rows = [_kline_row(dup_ms), _kline_row(dup_ms), _kline_row(dup_ms - 86_400_000)]
    df = _klines_to_frame(rows)
    assert len(df) == 2
    assert df.index.is_monotonic_increasing


def _btc_asset() -> Asset:
    return Asset(
        symbol="BTC", asset_class=AssetClass.CRYPTO, name="Bitcoin",
        binance_symbol="BTCUSDT", tier=1,
    )


def test_fetch_ohlcv_requires_binance_symbol() -> None:
    asset_no_bn = Asset(
        symbol="X", asset_class=AssetClass.CRYPTO, name="X", binance_symbol=None,
    )
    with pytest.raises(ValueError, match="no binance_symbol"):
        BinanceSource().fetch_ohlcv(asset_no_bn, start="2020-01-01")


def test_fetch_ohlcv_rejects_invalid_interval() -> None:
    with pytest.raises(ValueError, match="Invalid interval"):
        BinanceSource().fetch_ohlcv(_btc_asset(), start="2020-01-01", interval="bogus")


def test_fetch_ohlcv_geo_block_raises_permission_error() -> None:
    session = MagicMock()
    session.get.return_value = _make_response({"code": 0, "msg": "geo"}, status=451)
    src = BinanceSource(session=session, sleep_between_calls=0)
    with pytest.raises(PermissionError, match="451"):
        src.fetch_ohlcv(_btc_asset(), start="2020-01-01", end="2020-01-05")


def test_fetch_ohlcv_paginates_until_short_batch() -> None:
    # First batch: a "full" batch (limit-sized) -> pagination continues.
    # Second batch: shorter -> pagination ends.
    batch1 = [_kline_row(1_577_836_800_000 + i * 86_400_000) for i in range(1000)]
    batch2 = [_kline_row(1_577_836_800_000 + (1000 + i) * 86_400_000) for i in range(50)]
    session = MagicMock()
    session.get.side_effect = [
        _make_response(batch1),
        _make_response(batch2),
    ]

    src = BinanceSource(session=session, sleep_between_calls=0)
    df = src.fetch_ohlcv(
        _btc_asset(),
        start="2020-01-01",
        end="2024-01-01",
        interval="1d",
    )

    assert session.get.call_count == 2
    assert len(df) == 1050


def test_fetch_ohlcv_returns_empty_on_no_data() -> None:
    session = MagicMock()
    session.get.return_value = _make_response([])
    src = BinanceSource(session=session, sleep_between_calls=0)
    df = src.fetch_ohlcv(_btc_asset(), start="2020-01-01", end="2020-01-05")
    assert df.empty
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
