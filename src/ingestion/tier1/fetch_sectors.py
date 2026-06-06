"""Fetch equity sector/theme ETF snapshot + accumulate history (Fase 8).

Pulls recent daily closes for the sector/theme ETF universe from Yahoo, builds a
current-strength snapshot (5d + 21d momentum), persists a per-day history
(ADR-022 ``write_snapshot``), and writes a readable ``REPORT_EQUITY.md`` at the
repo root. A scheduled workflow runs this daily, so the equity rotation history
accumulates (the equity analogue of the crypto category history).

Run:  uv run python -m src.ingestion.tier1.fetch_sectors
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.assets.sectors import SECTOR_ETFS
from src.features.market_series import sparkline_values
from src.features.report_json import equity_report_dict, write_report_json
from src.features.sector_report import format_sector_report_md
from src.features.sector_screener import build_sector_frame, screen_sectors
from src.ingestion.freshness import check_freshness, last_timestamp_of
from src.ingestion.snapshot import write_snapshot
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/sector_history")
REPORT_PATH = Path("REPORT_EQUITY.md")
JSON_PATH = Path("public/data/equity_report.json")
# ~3 months of daily bars is plenty for 5d/21d momentum + a safety margin.
FETCH_START = "2025-09-01"


def main() -> None:
    src = YahooFinanceSource()
    closes: dict[str, pd.Series] = {}
    names: dict[str, str] = {}
    for asset in SECTOR_ETFS:
        try:
            ohlcv = src.fetch_ohlcv(asset, start=FETCH_START, interval="1d")
        except Exception:
            logger.exception("Failed to fetch %s (%s)", asset.symbol, asset.yahoo_symbol)
            continue
        if ohlcv.empty:
            logger.warning("No data for %s", asset.symbol)
            continue
        # Freshness guard (ADR-026): a frozen ticker keeps returning old bars
        # and silently poisons the snapshot — make staleness loud.
        fresh = check_freshness(
            last_timestamp_of(ohlcv), max_age_days=5, name=asset.symbol
        )
        if not fresh.is_fresh:
            logger.warning("STALE FEED: %s", fresh.message())
        closes[asset.symbol] = ohlcv["close"]
        names[asset.symbol] = asset.name

    frame = build_sector_frame(closes, names=names)
    if frame.empty:
        logger.warning("No sector data assembled; nothing to persist.")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    write_snapshot(
        frame,
        latest_path=DATA_DIR / "sectors_latest.parquet",
        history_path=DATA_DIR / "sectors_history.parquet",
        primary_key=["symbol"],
    )

    now = pd.Timestamp.now(tz="UTC").floor("min")
    REPORT_PATH.write_text(format_sector_report_md(frame, snapshot_at=now), encoding="utf-8")

    # Dashboard JSON twin, from the same structured snapshot (no Markdown parsing).
    # Embed a short close-price sparkline per sector from the data already fetched.
    spark = {sym: sparkline_values(s, window=60) for sym, s in closes.items()}
    write_report_json(equity_report_dict(frame, generated_at=now, spark=spark), JSON_PATH)
    logger.info("Wrote dashboard JSON -> %s", JSON_PATH)

    top = screen_sectors(frame, top_n=3)
    logger.info(
        "Persisted %d sectors. Strongest now: %s",
        len(frame), ", ".join(top["name"].tolist()),
    )


if __name__ == "__main__":
    main()
