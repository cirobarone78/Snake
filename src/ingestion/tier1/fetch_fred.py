# pyright: strict
"""FRED batch ingestion: macro fundamentals for crypto-macro analysis.

Run with:
  ``uv run python -m src.ingestion.tier1.fetch_fred``

Series chosen for Phase 1 (small, high-signal set; trivially extendable):
- DFF     — Federal Funds Effective Rate (daily)
- DGS2    — 2-Year Treasury (daily)
- DGS10   — 10-Year Treasury (daily). DGS10-DGS2 = yield curve slope
- DTWEXBGS— Trade-weighted Broad Dollar Index (daily; alt to Yahoo DXY)
- CPIAUCSL— CPI All Items (monthly; inflation level)
- M2SL    — M2 Money Supply (monthly)
- UNRATE  — Unemployment Rate (monthly)

Storage:
  data/raw/fred/{frequency}/{SERIES_ID}.parquet
where ``frequency`` is the FRED-reported natural cadence ("D", "M", ...).
The series_info metadata is logged but not persisted in Phase 1 (we keep
provenance in the file path).
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

from src.ingestion.tier1.fred import FredSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# (series_id, observation_start) tuples. Start dates chosen to roughly
# align with the rest of the Tier 1 panel (2018-01-01) but FRED will
# happily go back to series inception when given an earlier date.
DEFAULT_START = "2018-01-01"
SERIES: list[str] = [
    "DFF",
    "DGS2",
    "DGS10",
    "DTWEXBGS",
    "CPIAUCSL",
    "M2SL",
    "UNRATE",
]

DEFAULT_DATA_DIR = Path("data/raw/fred")


def main() -> None:
    load_dotenv()  # read FRED_API_KEY from .env if present
    src = FredSource()

    logger.info("Starting FRED batch ingestion (Phase 1)")
    results: dict[str, int] = {}
    for series_id in SERIES:
        try:
            info = src.fetch_series_info(series_id)
            freq = info.get("frequency_short", "U")
            df = src.fetch_series(series_id, observation_start=DEFAULT_START)
            if df.empty:
                logger.warning("Empty series %s", series_id)
                results[series_id] = 0
                continue
            out_dir = DEFAULT_DATA_DIR / freq
            out_dir.mkdir(parents=True, exist_ok=True)
            out = out_dir / f"{series_id}.parquet"
            df.to_parquet(out, engine="pyarrow", compression="snappy")
            logger.info(
                "Saved %d rows for %s (%s, %s) to %s",
                len(df), series_id, info.get("title", "?"), freq, out,
            )
            results[series_id] = len(df)
        except Exception as exc:
            logger.exception("Failed to fetch %s: %s", series_id, exc)
            results[series_id] = -1

    logger.info("Done. Row counts per series:")
    for series_id, count in results.items():
        status = "OK" if count > 0 else ("EMPTY" if count == 0 else "ERROR")
        logger.info("  %-10s %6s rows  [%s]", series_id, count, status)


if __name__ == "__main__":
    main()
