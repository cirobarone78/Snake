# pyright: strict
"""Yahoo Finance OHLCV source (Tier 1, ADR-017).

Yahoo is the first source we wire up: free, broad coverage (crypto, equity,
indices, FX, commodities), simple. Quality is good for daily bars and
acceptable for higher granularities. Known caveats:

- Crypto symbols use the ``BTC-USD`` style.
- Time zone returned by yfinance varies; we normalize to UTC.
- POL-USD only covers post-rename history (September 2024+). Pre-rename
  data is under MATIC-USD. Reconciliation deferred to a later phase.
- Adjusted close: yfinance applies split/dividend adjustments by default.
  For crypto this is a no-op. For equity (future Phase 8) we will need to
  decide adjusted vs raw — see ADR-014 (corporate actions).
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Final

import pandas as pd
import yfinance as yf

from src.assets.asset import Asset
from src.ingestion.base import OHLCVDataSource

logger = logging.getLogger(__name__)

VALID_INTERVALS: Final[set[str]] = {
    "1m", "2m", "5m", "15m", "30m", "60m", "90m",
    "1h", "1d", "5d", "1wk", "1mo", "3mo",
}


class YahooFinanceSource(OHLCVDataSource):
    """Free Yahoo Finance source for OHLCV bars."""

    @property
    def name(self) -> str:
        return "yahoo"

    def fetch_ohlcv(
        self,
        asset: Asset,
        start: datetime | str,
        end: datetime | str | None = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        if asset.yahoo_symbol is None:
            raise ValueError(
                f"Asset {asset.symbol} has no yahoo_symbol; cannot fetch from Yahoo"
            )
        if interval not in VALID_INTERVALS:
            raise ValueError(
                f"Invalid interval {interval!r}. Valid: {sorted(VALID_INTERVALS)}"
            )

        logger.info(
            "Fetching %s %s from Yahoo (interval=%s, start=%s, end=%s)",
            asset.symbol, asset.yahoo_symbol, interval, start, end,
        )

        ticker = yf.Ticker(asset.yahoo_symbol)
        raw = ticker.history(
            start=start,
            end=end,
            interval=interval,
            auto_adjust=True,
            actions=False,
        )

        if raw.empty:
            logger.warning("No data returned for %s", asset.yahoo_symbol)
            return _empty_ohlcv_frame()

        df = raw.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )[["open", "high", "low", "close", "volume"]]

        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")
        df.index.name = "timestamp"

        df = df.dropna(subset=["close"])

        return df


def _empty_ohlcv_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["open", "high", "low", "close", "volume"],
        index=pd.DatetimeIndex([], name="timestamp", tz="UTC"),
    )


def save_ohlcv_parquet(
    df: pd.DataFrame,
    asset: Asset,
    source_name: str,
    interval: str,
    data_dir: Path,
) -> Path:
    """Persist an OHLCV frame to parquet under a structured path.

    Layout: ``{data_dir}/{source_name}/{asset_class}/{symbol}_{interval}.parquet``.
    Tracks provenance via path; per-source metadata (rate limits, fetch time)
    is logged but not stored in the file in Phase 1.
    """
    out_dir = data_dir / source_name / asset.asset_class.value
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{asset.symbol}_{interval}.parquet"
    df.to_parquet(out_path, engine="pyarrow", compression="snappy")
    logger.info("Saved %d rows to %s", len(df), out_path)
    return out_path
