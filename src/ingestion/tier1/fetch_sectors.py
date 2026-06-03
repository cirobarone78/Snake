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
from src.features.sector_report import format_sector_report_md
from src.features.sector_screener import build_sector_frame, screen_sectors
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

    top = screen_sectors(frame, top_n=3)
    logger.info(
        "Persisted %d sectors. Strongest now: %s",
        len(frame), ", ".join(top["name"].tolist()),
    )


if __name__ == "__main__":
    main()
