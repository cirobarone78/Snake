"""Tests for YahooFinanceSource — mocked yfinance, no network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.assets.asset import Asset, AssetClass
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource


def _btc_asset() -> Asset:
    return Asset(
        symbol="BTC", asset_class=AssetClass.CRYPTO, name="Bitcoin",
        yahoo_symbol="BTC-USD", tier=1,
    )


def _ticker_returning(df: pd.DataFrame) -> MagicMock:
    """Build a mock yfinance.Ticker whose .history() returns ``df``."""
    ticker = MagicMock()
    ticker.history.return_value = df
    return ticker


def _yf_history_frame(
    dates: list[str], closes: list[float], tz: str | None = None
) -> pd.DataFrame:
    idx = pd.to_datetime(dates)
    if tz is not None:
        idx = idx.tz_localize(tz)
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [c * 1.02 for c in closes],
            "Low": [c * 0.98 for c in closes],
            "Close": closes,
            "Volume": [1_000_000.0] * len(closes),
        },
        index=idx,
    )


def test_fetch_ohlcv_requires_yahoo_symbol() -> None:
    asset_no_yh = Asset(
        symbol="X", asset_class=AssetClass.CRYPTO, name="X", yahoo_symbol=None,
    )
    with pytest.raises(ValueError, match="no yahoo_symbol"):
        YahooFinanceSource().fetch_ohlcv(asset_no_yh, start="2020-01-01")


def test_fetch_ohlcv_rejects_invalid_interval() -> None:
    with pytest.raises(ValueError, match="Invalid interval"):
        YahooFinanceSource().fetch_ohlcv(_btc_asset(), start="2020-01-01", interval="bogus")


@patch("src.ingestion.tier1.yahoo_finance.yf.Ticker")
def test_fetch_ohlcv_renames_columns_and_normalizes_index(yf_ticker: MagicMock) -> None:
    raw = _yf_history_frame(
        ["2020-01-01", "2020-01-02", "2020-01-03"],
        [7200.0, 7250.0, 7300.0],
        tz=None,  # yfinance sometimes returns naive index
    )
    yf_ticker.return_value = _ticker_returning(raw)

    df = YahooFinanceSource().fetch_ohlcv(_btc_asset(), start="2020-01-01", end="2020-01-04")

    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.name == "timestamp"
    assert str(df.index.tz) == "UTC"
    assert len(df) == 3
    assert df.iloc[0]["close"] == 7200.0


@patch("src.ingestion.tier1.yahoo_finance.yf.Ticker")
def test_fetch_ohlcv_converts_existing_tz_to_utc(yf_ticker: MagicMock) -> None:
    # yfinance may return a New York timezone for some symbols
    raw = _yf_history_frame(["2020-01-01", "2020-01-02"], [7200.0, 7250.0], tz="America/New_York")
    yf_ticker.return_value = _ticker_returning(raw)

    df = YahooFinanceSource().fetch_ohlcv(_btc_asset(), start="2020-01-01", end="2020-01-03")

    assert str(df.index.tz) == "UTC"
    # Time offset should be preserved (NY midnight = 05:00 UTC in standard time)
    assert df.index[0].hour == 5


@patch("src.ingestion.tier1.yahoo_finance.yf.Ticker")
def test_fetch_ohlcv_drops_nan_close(yf_ticker: MagicMock) -> None:
    raw = _yf_history_frame(["2020-01-01", "2020-01-02", "2020-01-03"], [7200.0, 7250.0, 7300.0])
    raw.iloc[1, raw.columns.get_loc("Close")] = float("nan")
    yf_ticker.return_value = _ticker_returning(raw)

    df = YahooFinanceSource().fetch_ohlcv(_btc_asset(), start="2020-01-01", end="2020-01-04")

    assert len(df) == 2
    # Day 2 (the NaN close one) dropped
    assert df.index[1].date().isoformat() == "2020-01-03"


@patch("src.ingestion.tier1.yahoo_finance.yf.Ticker")
def test_fetch_ohlcv_empty_response_returns_empty_frame(yf_ticker: MagicMock) -> None:
    yf_ticker.return_value = _ticker_returning(pd.DataFrame())

    df = YahooFinanceSource().fetch_ohlcv(_btc_asset(), start="2020-01-01", end="2020-01-04")

    assert df.empty
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.name == "timestamp"


@patch("src.ingestion.tier1.yahoo_finance.yf.Ticker")
def test_fetch_ohlcv_forwards_kwargs_to_yfinance(yf_ticker: MagicMock) -> None:
    yf_ticker.return_value = _ticker_returning(
        _yf_history_frame(["2020-01-01"], [7200.0])
    )

    YahooFinanceSource().fetch_ohlcv(
        _btc_asset(), start="2020-01-01", end="2020-01-04", interval="1d"
    )

    yf_ticker.assert_called_once_with("BTC-USD")
    history_kwargs = yf_ticker.return_value.history.call_args.kwargs
    assert history_kwargs["start"] == "2020-01-01"
    assert history_kwargs["end"] == "2020-01-04"
    assert history_kwargs["interval"] == "1d"
    # auto_adjust and actions=False are baked-in policy, verify they survive
    assert history_kwargs["auto_adjust"] is True
    assert history_kwargs["actions"] is False
