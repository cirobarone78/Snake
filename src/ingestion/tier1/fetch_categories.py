"""Fetch crypto category snapshots and accumulate their history (Fase 6).

Pulls the CoinGecko category map and writes both a ``latest`` pointer and an
append-only ``history`` (ADR-022 ``write_snapshot`` pattern), so the category
rotation can be reconstructed over time. The history is the raw material for the
future probabilistic layer ("given this category state, what happened next").

The category history is **committed** (carve-out like the news history, ADR-025):
it is small (a few hundred rows/day, metadata only) and must survive the
ephemeral container to accumulate. A scheduled workflow runs this daily.

Run:  uv run python -m src.ingestion.tier1.fetch_categories
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.ingestion.snapshot import write_snapshot
from src.ingestion.tier1.coingecko import CoinGeckoSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Floor for what we persist: keep only categories with real size, so the
# committed history stays small and free of micro-cap pump noise.
PERSIST_MIN_MARKET_CAP = 1e8
DEFAULT_DATA_DIR = Path("data/category_history")


def main() -> None:
    src = CoinGeckoSource()
    data_dir = DEFAULT_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)

    df = src.fetch_categories(min_market_cap=PERSIST_MIN_MARKET_CAP)
    if df.empty:
        logger.warning("No categories returned; nothing to persist.")
        return

    write_snapshot(
        df,
        latest_path=data_dir / "categories_latest.parquet",
        history_path=data_dir / "categories_history.parquet",
        primary_key=["category_id"],
    )
    logger.info(
        "Persisted %d categories (>= $%.0fM mcap). Top by mcap: %s",
        len(df),
        PERSIST_MIN_MARKET_CAP / 1e6,
        ", ".join(df["name"].head(5).tolist()),
    )


if __name__ == "__main__":
    main()
