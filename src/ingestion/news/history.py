"""Compact, versioned news history (Fase 3, ADR-025).

The per-source parquet written by ``fetch_news`` lives under ``data/raw/news/``
and is gitignored (ADR-009). But a useful lead/lag study needs *months* of news,
and feeds only expose the last few weeks — so the history must survive the
ephemeral container. ADR-025 carves out a narrow exception to ADR-009: a single
**compact** parquet, committed to the repo, accumulated by a scheduled job.

"Compact" = headline-level metadata only (``item_id, source, title, url,
published`` + a precomputed ``sentiment``). We deliberately **drop the article
summary**: it adds size and a licensing grey area, and the Layer 1 scorer
(ADR-023) only reads the title anyway. Headlines + links are facts/links, small,
and low-risk to version.

Pure functions over pandas frames, so they unit-test offline.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pandas as pd

from src.ai.lexicon.sentiment import score_news_frame
from src.ingestion.news.persist import append_news

# Columns kept in the versioned history (no ``summary`` — see module docstring).
COMPACT_COLUMNS = ["item_id", "source", "title", "url", "sentiment"]

DEFAULT_HISTORY_PATH = Path("data/news_history/news.parquet")


def to_compact(frame: pd.DataFrame) -> pd.DataFrame:
    """Score a ``news_to_frame`` frame and reduce it to the compact schema.

    Adds a Layer 1 ``sentiment`` column (ADR-023) and keeps only
    ``COMPACT_COLUMNS``, preserving the ``published`` UTC index. An empty input
    yields a correctly-typed empty compact frame.
    """
    scored = score_news_frame(frame)
    if scored.empty:
        return cast("pd.DataFrame", scored.reindex(columns=COMPACT_COLUMNS))
    return cast("pd.DataFrame", scored[COMPACT_COLUMNS])


def update_history(
    frame: pd.DataFrame,
    path: str | Path = DEFAULT_HISTORY_PATH,
) -> pd.DataFrame:
    """Score, compact, and append a news frame to the versioned history.

    Reuses ``append_news`` for the append+dedup-on-``item_id`` semantics, so a
    story seen across many scheduled runs is stored once (latest version wins).
    Returns the merged history frame.
    """
    return append_news(to_compact(frame), path)
