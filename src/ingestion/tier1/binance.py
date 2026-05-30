# pyright: strict
"""Binance OHLCV source (Tier 1, ADR-017).

Binance is added as a second crypto-native source to:
- Provide higher granularity than Yahoo when needed (1m/5m/1h klines)
- Close the recent-history gap on POL (see ADR-019 and OPEN_QUESTIONS Q21bis)
- Cross-validate Yahoo's daily closes (Yahoo aggregates from multiple
  feeds; Binance is the direct exchange).

Geo-restriction: ``api.binance.com`` returns HTTP 451 from the current
environment (Binance terms of service). We default to ``api.binance.us``
as the base URL — same REST schema, US-compliant entity, smaller universe
but covers all our Tier 1 pairs (BTC/ETH/SOL/LINK/POL/MATIC). The base
URL is configurable so production environments with access to the global
endpoint can switch via ``BinanceSource(base_url="https://api.binance.com")``.
See ADR-020.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Final

import pandas as pd
import requests

from src.assets.asset import Asset
from src.ingestion.base import OHLCVDataSource

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL: Final[str] = "https://api.binance.us"
KLINES_MAX_LIMIT: Final[int] = 1000  # exchange-imposed per-call cap

# Binance interval codes. We expose only the daily one in Phase 1, but
# the source accepts any valid Binance code so the interface can grow.
VALID_INTERVALS: Final[set[str]] = {
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M",
}

# Approximate ms-per-bar mapping for pagination math (close enough for
# scheduling; the actual end timestamp is taken from the response).
_INTERVAL_MS: Final[dict[str, int]] = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "6h": 21_600_000,
    "8h": 28_800_000, "12h": 43_200_000,
    "1d": 86_400_000, "3d": 259_200_000, "1w": 604_800_000, "1M": 2_592_000_000,
}


class BinanceSource(OHLCVDataSource):
    """Binance public REST API for klines (OHLCV).

    No API key required for klines. Public-endpoint rate limit is 1200
    weight/min; each klines call is weight 2, so >500 calls/min are
    available — comfortably above what we need.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        session: requests.Session | None = None,
        request_timeout: float = 15.0,
        sleep_between_calls: float = 0.1,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._timeout = request_timeout
        self._sleep = sleep_between_calls

    @property
    def name(self) -> str:
        return "binance"

    def fetch_ohlcv(
        self,
        asset: Asset,
        start: datetime | str,
        end: datetime | str | None = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        if asset.binance_symbol is None:
            raise ValueError(
                f"Asset {asset.symbol} has no binance_symbol; cannot fetch from Binance"
            )
        if interval not in VALID_INTERVALS:
            raise ValueError(
                f"Invalid interval {interval!r}. Valid: {sorted(VALID_INTERVALS)}"
            )

        start_ms = _to_ms(start)
        end_ms = _to_ms(end) if end is not None else int(time.time() * 1000)

        logger.info(
            "Fetching %s %s from Binance (base=%s, interval=%s, start=%s, end=%s)",
            asset.symbol, asset.binance_symbol, self._base_url, interval, start, end,
        )

        chunks: list[list[list[Any]]] = []
        cursor = start_ms
        while cursor < end_ms:
            batch = self._klines(
                symbol=asset.binance_symbol,
                interval=interval,
                start_ms=cursor,
                end_ms=end_ms,
                limit=KLINES_MAX_LIMIT,
            )
            if not batch:
                break
            chunks.append(batch)
            last_open_ms = int(batch[-1][0])
            # Advance one bar past the last open we just received.
            cursor = last_open_ms + _INTERVAL_MS.get(interval, 86_400_000)
            if len(batch) < KLINES_MAX_LIMIT:
                # We caught up — fewer than max returned means no more pages.
                break
            time.sleep(self._sleep)

        if not chunks:
            logger.warning("No data returned for %s on Binance", asset.binance_symbol)
            return _empty_ohlcv_frame()

        rows = [row for batch in chunks for row in batch]
        return _klines_to_frame(rows)

    def _klines(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
        limit: int,
    ) -> list[list[Any]]:
        url = f"{self._base_url}/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": limit,
        }
        resp = self._session.get(url, params=params, timeout=self._timeout)
        if resp.status_code == 451:
            raise PermissionError(
                f"Binance refused the request (HTTP 451 — geo-restricted). "
                f"base_url={self._base_url}. "
                f"Use api.binance.us or run from an eligible region. See ADR-020."
            )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected Binance response shape: {data!r}")
        return data


def _to_ms(ts: datetime | str) -> int:
    dt = ts if isinstance(ts, datetime) else pd.Timestamp(ts).to_pydatetime()
    if dt.tzinfo is None:
        # Treat naive timestamps as UTC, consistent with the rest of the pipeline.
        dt = pd.Timestamp(dt).tz_localize("UTC").to_pydatetime()
    return int(dt.timestamp() * 1000)


def _klines_to_frame(rows: list[list[Any]]) -> pd.DataFrame:
    """Convert a Binance klines payload into our standard OHLCV frame.

    Binance kline schema (positional):
      [openTime, open, high, low, close, volume, closeTime, quoteVolume,
       trades, takerBuyBase, takerBuyQuote, ignored]
    """
    df = pd.DataFrame(
        rows,
        columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades",
            "taker_buy_base", "taker_buy_quote", "ignored",
        ],
    )
    df = df[["open_time", "open", "high", "low", "close", "volume"]].copy()
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.set_index("open_time")
    df.index.name = "timestamp"
    df = df.dropna(subset=["close"])
    # Deduplicate in case pagination overlap produced duplicates.
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


def _empty_ohlcv_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["open", "high", "low", "close", "volume"],
        index=pd.DatetimeIndex([], name="timestamp", tz="UTC"),
    )
