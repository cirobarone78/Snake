# pyright: strict
"""Phase 1 batch ingestion: fetch daily OHLCV for all Tier 1 + context assets.

Run with:
  ``uv run python -m src.ingestion.tier1.fetch_tier1``                # Yahoo (default)
  ``uv run python -m src.ingestion.tier1.fetch_tier1 --source binance`` # Binance (US endpoint)
  ``uv run python -m src.ingestion.tier1.fetch_tier1 --source all``     # both

This is the smallest end-to-end pipeline that exercises the
asset-class-agnostic abstractions: same code, different Asset entries,
crypto and equity indices side by side. Binance only handles crypto
(no equity indices on the venue), so on ``binance`` runs the context
assets are silently skipped when they lack a ``binance_symbol``.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from src.assets.asset import CONTEXT_ASSETS, TIER1_ASSETS, Asset
from src.ingestion.base import OHLCVDataSource
from src.ingestion.tier1.binance import BinanceSource
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
    source: OHLCVDataSource,
    start: str = DEFAULT_START,
    end: str | None = None,
    interval: str = DEFAULT_INTERVAL,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> dict[str, int]:
    """Fetch OHLCV for each asset and persist to parquet. Return row counts."""
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
        except ValueError as exc:
            # Asset not supported by this source (e.g. an index on Binance).
            logger.info("Skipping %s on %s: %s", asset.symbol, source.name, exc)
            results[asset.symbol] = -2
        except Exception as exc:
            logger.exception("Failed to fetch %s from %s: %s", asset.symbol, source.name, exc)
            results[asset.symbol] = -1

    return results


def _log_results(source_name: str, results: dict[str, int]) -> None:
    logger.info("Done with %s. Row counts per asset:", source_name)
    for symbol, count in results.items():
        if count == -2:
            status = "SKIP"
        elif count == -1:
            status = "ERROR"
        elif count == 0:
            status = "EMPTY"
        else:
            status = "OK"
        logger.info("  %-6s %6s rows  [%s]", symbol, count, status)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tier 1 batch ingestion")
    parser.add_argument(
        "--source",
        choices=["yahoo", "binance", "all"],
        default="yahoo",
        help="Which data source(s) to run. Default: yahoo.",
    )
    args = parser.parse_args()

    all_assets = TIER1_ASSETS + CONTEXT_ASSETS

    if args.source in {"yahoo", "all"}:
        logger.info("Starting Tier 1 batch ingestion via Yahoo (Phase 1)")
        _log_results("yahoo", fetch_all(all_assets, YahooFinanceSource()))

    if args.source in {"binance", "all"}:
        logger.info("Starting Tier 1 batch ingestion via Binance (Phase 1)")
        _log_results("binance", fetch_all(all_assets, BinanceSource()))


if __name__ == "__main__":
    main()
