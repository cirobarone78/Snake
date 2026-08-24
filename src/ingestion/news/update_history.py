"""Scheduled entrypoint: fetch news, score, append to versioned history (ADR-025).

Pulls every configured feed, scores each item with the Layer 1 lexicon
(ADR-023), and appends the compact result to the committed history under
``data/news_history/``, deduped on ``item_id``. Since ADR-033 that history is
**partitioned by publication month**, so a run only rewrites the month(s) it
touched instead of a ~26MB monolith. Run by the ``news-history`` GitHub Actions
workflow (Q10: batch); the workflow commits the changed partitions so history
accumulates across ephemeral runs.

The run migrates a pre-ADR-033 monolith to partitions first. That is a no-op on
any checkout made after the migration commit — it is there so an old worktree
converts itself instead of silently writing the 26MB file again.

A failure on one feed is logged and skipped (the others still run), matching the
partial-failure policy of the other ingestion scripts — important because native
publisher feeds are anti-bot flaky (see ``feeds.py``).

Run:  uv run python -m src.ingestion.news.update_history
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import pandas as pd

from src.ingestion.news.base import NewsSource, news_to_frame
from src.ingestion.news.feeds import default_news_sources
from src.ingestion.news.history import (
    DEFAULT_HISTORY_DIR,
    migrate_to_partitions,
    read_news_history,
    update_history,
)

logger = logging.getLogger(__name__)

DEFAULT_PACING_SECONDS = 2.0


def run(
    path: str | Path = DEFAULT_HISTORY_DIR,
    sources: list[NewsSource] | None = None,
    pacing_seconds: float = DEFAULT_PACING_SECONDS,
) -> int:
    """Fetch all sources, append scored items to the history, return total size."""
    migrated = migrate_to_partitions(path)
    if migrated:
        logger.info("Migrated the monolithic history into %d monthly partitions", len(migrated))
    feeds = sources if sources is not None else default_news_sources()
    frames: list[pd.DataFrame] = []
    for source in feeds:
        try:
            items = source.fetch()
        except Exception:
            logger.exception("Failed to fetch news source %s", source.name)
            continue
        frames.append(news_to_frame(items))
        logger.info("%s: fetched %d items", source.name, len(items))
        if pacing_seconds > 0:
            time.sleep(pacing_seconds)

    combined = pd.concat(frames) if frames else news_to_frame([])
    before = len(read_news_history(path))
    merged = update_history(combined, path)
    logger.info(
        "History updated: %d fetched, +%d new, %d total -> %s",
        len(combined),
        len(merged) - before,
        len(merged),
        path,
    )
    return len(merged)


def main() -> None:
    parser = argparse.ArgumentParser(description="Update the versioned news history.")
    parser.add_argument(
        "--path",
        default=str(DEFAULT_HISTORY_DIR),
        help="History directory holding the monthly partitions.",
    )
    parser.add_argument(
        "--pacing",
        type=float,
        default=DEFAULT_PACING_SECONDS,
        help="Seconds to sleep between feeds.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(path=args.path, pacing_seconds=args.pacing)


if __name__ == "__main__":
    main()
