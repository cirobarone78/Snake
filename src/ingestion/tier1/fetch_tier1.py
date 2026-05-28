# pyright: strict
"""Phase 1 batch ingestion: fetch daily OHLCV for all Tier 1 + context assets.

Run with: ``uv run python -m src.ingestion.tier1.fetch_tier1``

This is the smallest end-to-end pipeline that exercises the
asset-class-agnostic abstractions: same code, different Asset entries,
crypto and equity indices side by side.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from src.assets.asset import CONTEXT_ASSETS, TIER1_ASSETS, Asset
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource, save_ohlcv_parquet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_START = "2018-01-01"
DEFAULT_INTERVAL = "1d"
DEFAULT_DATA_DIR = Path("data/raw")


def fetch_all(
    assets: list[Asset],
    start: str = DEFAULT_START,
    end: str | None = None,
    interval: str = DEFAULT_INTERVAL,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> dict[str, int]:
    """Fetch OHLCV for each asset and persist to parquet. Return row counts."""
    source = YahooFinanceSource()
    end_str = end or datetime.utcnow().strftime("%Y-%m-%d")
    results: dict[str, int] = {}

    for asset in assets:
        try:
            df = source.fetch_ohlcv(asset, start=start, end=end_str, interval=interval)
            if df.empty:
                logger.warning("Empty frame for %s, skipping save", asset.symbol)
                results[asset.symbol] = 0
                continue
            save_ohlcv_parquet(df, asset, source.name, interval, data_dir)
            results[asset.symbol] = len(df)
        except Exception as exc:
            logger.exception("Failed to fetch %s: %s", asset.symbol, exc)
            results[asset.symbol] = -1

    return results


def main() -> None:
    logger.info("Starting Tier 1 batch ingestion (Phase 1)")
    all_assets = TIER1_ASSETS + CONTEXT_ASSETS
    results = fetch_all(all_assets)
    logger.info("Done. Row counts per asset:")
    for symbol, count in results.items():
        status = "OK" if count > 0 else ("EMPTY" if count == 0 else "ERROR")
        logger.info("  %-6s %6s rows  [%s]", symbol, count, status)


if __name__ == "__main__":
    main()
