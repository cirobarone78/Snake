"""Fetch and persist news from the configured feeds (Fase 3).

Pulls each feed in ``default_news_sources()``, normalises to the canonical
``NewsItem`` frame, and appends to a per-source parquet under
``data/raw/news/`` (gitignored), deduped on ``item_id`` so repeated runs
accumulate history (Q10: batch-friendly).

This script handles *acquisition and normalisation only*. Sentiment / NLP is a
separate, later concern that depends on the model stack (ADR-016).

Run:  uv run python -m src.ingestion.news.fetch_news
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import pandas as pd

from src.ingestion.news.base import NewsSource, news_to_frame
from src.ingestion.news.feeds import default_news_sources
from src.ingestion.news.persist import append_news

logger = logging.getLogger(__name__)

NEWS_DIR = "data/raw/news"
DEFAULT_PACING_SECONDS = 2.0


def fetch_all(
    out_dir: str = NEWS_DIR,
    sources: list[NewsSource] | None = None,
    pacing_seconds: float = DEFAULT_PACING_SECONDS,
) -> int:
    """Fetch every source, persist per-source history, return new-item count.

    A failure on one feed is logged and skipped (the others still run), matching
    the partial-failure policy of the other ingestion scripts.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    feeds = sources if sources is not None else default_news_sources()

    total_new = 0
    for source in feeds:
        try:
            items = source.fetch()
        except Exception:
            logger.exception("Failed to fetch news source %s", source.name)
            continue
        frame = news_to_frame(items)
        path = out / f"{source.name}.parquet"
        before = len(pd.read_parquet(path)) if path.exists() else 0
        merged = append_news(frame, path)
        added = len(merged) - before
        logger.info(
            "%s: fetched %d items (+%d new to history, total %d) -> %s",
            source.name,
            len(frame),
            added,
            len(merged),
            path,
        )
        total_new += added
        if pacing_seconds > 0:
            time.sleep(pacing_seconds)

    logger.info("Done: %d items fetched across %d sources", total_new, len(feeds))
    return total_new


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and persist crypto news feeds.")
    parser.add_argument("--out-dir", default=NEWS_DIR, help="Output directory.")
    parser.add_argument(
        "--pacing",
        type=float,
        default=DEFAULT_PACING_SECONDS,
        help="Seconds to sleep between feeds.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    fetch_all(out_dir=args.out_dir, pacing_seconds=args.pacing)


if __name__ == "__main__":
    main()
