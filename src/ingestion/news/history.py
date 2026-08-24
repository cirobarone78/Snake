"""Compact, versioned news history, partitioned by month (Fase 3, ADR-025/033).

The per-source parquet written by ``fetch_news`` lives under ``data/raw/news/``
and is gitignored (ADR-009). But a useful lead/lag study needs *months* of news,
and feeds only expose the last few weeks — so the history must survive the
ephemeral container. ADR-025 carves out a narrow exception to ADR-009: a
**compact** parquet history, committed to the repo, accumulated by a scheduled
job.

"Compact" = headline-level metadata only (``item_id, source, title, url,
published`` + a precomputed ``sentiment``). We deliberately **drop the article
summary**: it adds size and a licensing grey area, and the Layer 1 scorer
(ADR-023) only reads the title anyway. Headlines + links are facts/links, small,
and low-risk to version.

**Monthly partitioning** (ADR-033). The history used to be one monolithic
``news.parquet``. A parquet is rewritten whole on every append, so a cron
running every 3h stored a brand-new ~26MB blob in git each time — 97,5% of the
repository weight. The history is now split into one file per publication month,
``news_YYYY-MM.parquet``: a run only rewrites the month(s) it actually touched,
and past months become immutable blobs git never stores again. Readers see one
frame: ``read_news_history()`` concatenates the partitions, so consumers are
unaffected by the layout.

Deduplication on ``item_id`` happens twice, and the split matters:
``append_news`` dedups *within* a partition on write, ``read_news_history``
dedups *across* partitions on read. The second one covers the rare case of a
feed re-publishing a story under a new date: the stale copy stays in its old
partition (rewriting it would defeat the point) and the read keeps the row from
the later month.

**Byte stability is load-bearing here**, not a nicety. Partitioning only saves
anything if an unchanged partition serialises to the *same bytes*, so git
recognises it as the same blob and stores nothing. That requires a total,
content-determined row order — see ``sort_canonical`` in ``persist``, and the
first-run measurement that forced it.

Pure functions over pandas frames, so they unit-test offline.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import pandas as pd

from src.ai.lexicon.sentiment import score_news_frame
from src.ingestion.news.persist import append_news, sort_canonical

# Columns kept in the versioned history (no ``summary`` — see module docstring).
COMPACT_COLUMNS = ["item_id", "source", "title", "url", "sentiment"]

DEFAULT_HISTORY_DIR = Path("data/news_history")

# Pre-ADR-033 monolith. Still read (so a checkout that predates the migration
# keeps working) but never written again.
LEGACY_FILENAME = "news.parquet"

PARTITION_GLOB = "news_[0-9][0-9][0-9][0-9]-[0-9][0-9].parquet"
_PARTITION_RE = re.compile(r"^news_(\d{4}-\d{2})\.parquet$")


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


def resolve_history_dir(path: str | Path = DEFAULT_HISTORY_DIR) -> Path:
    """Accept either the history directory or a parquet inside it.

    Callers (and the ``--path`` flags of older CLIs) may still point at
    ``.../news.parquet``. Treat any ``.parquet`` argument as "the directory that
    contains it" so no caller breaks on the ADR-033 layout change.
    """
    path = Path(path)
    return path.parent if path.suffix == ".parquet" else path


def partition_key(timestamp: pd.Timestamp) -> str:
    """Month key (``"2026-08"``) a story published at ``timestamp`` belongs to."""
    return f"{timestamp.year:04d}-{timestamp.month:02d}"


def partition_path(directory: str | Path, key: str) -> Path:
    """Path of the partition holding month ``key`` (``"YYYY-MM"``)."""
    return resolve_history_dir(directory) / f"news_{key}.parquet"


def partition_files(directory: str | Path = DEFAULT_HISTORY_DIR) -> list[Path]:
    """Existing partitions, oldest month first.

    The legacy monolith, if still present, sorts **first** so that a partition
    wins over it when the same ``item_id`` exists in both (read dedup keeps the
    last occurrence).
    """
    history_dir = resolve_history_dir(directory)
    if not history_dir.is_dir():
        return []
    months = sorted(
        (p for p in history_dir.glob(PARTITION_GLOB) if _PARTITION_RE.match(p.name)),
        key=lambda p: p.name,
    )
    legacy = history_dir / LEGACY_FILENAME
    return ([legacy] if legacy.exists() else []) + months


def read_news_history(directory: str | Path = DEFAULT_HISTORY_DIR) -> pd.DataFrame:
    """Read the whole history as a single frame, transparently across months.

    Concatenates every partition (plus the pre-migration monolith if it is still
    there), drops duplicate ``item_id`` keeping the row from the latest
    partition, and sorts ascending by ``published``. Returns a correctly-typed
    empty compact frame when there is nothing on disk, so callers never need to
    branch on existence.
    """
    files = partition_files(directory)
    if not files:
        return empty_history()

    frames = [cast("pd.DataFrame", pd.read_parquet(path)) for path in files]
    combined = frames[0] if len(frames) == 1 else pd.concat(frames)
    combined = combined[~combined["item_id"].duplicated(keep="last")]
    return sort_canonical(cast("pd.DataFrame", combined))


def empty_history() -> pd.DataFrame:
    """An empty history frame with the compact schema and a UTC index."""
    return pd.DataFrame(
        columns=COMPACT_COLUMNS,
        index=pd.DatetimeIndex([], name="published", tz="UTC"),
    )


def update_history(
    frame: pd.DataFrame,
    directory: str | Path = DEFAULT_HISTORY_DIR,
) -> pd.DataFrame:
    """Score, compact, and append a news frame into the monthly partitions.

    Only the partitions the incoming items actually fall into are rewritten —
    that is the whole point of ADR-033. Within each partition the semantics are
    unchanged (``append_news``: dedup on ``item_id``, newly fetched version
    wins). Returns the merged full history.
    """
    history_dir = resolve_history_dir(directory)
    compact = to_compact(frame)
    if not compact.empty:
        index = cast("pd.DatetimeIndex", compact.index)
        keys = [partition_key(cast("pd.Timestamp", ts)) for ts in index]
        for key, month_frame in compact.groupby(pd.Index(keys, name="month")):
            append_news(month_frame, partition_path(history_dir, str(key)))
    return read_news_history(history_dir)


def migrate_to_partitions(
    directory: str | Path = DEFAULT_HISTORY_DIR,
    *,
    remove_legacy: bool = True,
) -> dict[str, int]:
    """Split a pre-ADR-033 ``news.parquet`` into monthly partitions.

    One-shot and idempotent: with no monolith on disk it is a no-op. Rows are
    merged into any partition that already exists (same dedup as a normal
    append), so re-running cannot lose or duplicate stories. The old blobs stay
    in the git history — nothing is rewritten there.

    Returns the row count written per month key.
    """
    history_dir = resolve_history_dir(directory)
    legacy = history_dir / LEGACY_FILENAME
    if not legacy.exists():
        return {}

    monolith = cast("pd.DataFrame", pd.read_parquet(legacy))
    index = cast("pd.DatetimeIndex", monolith.index)
    keys = [partition_key(cast("pd.Timestamp", ts)) for ts in index]
    written: dict[str, int] = {}
    for key, month_frame in monolith.groupby(pd.Index(keys, name="month")):
        merged = append_news(month_frame, partition_path(history_dir, str(key)))
        written[str(key)] = len(merged)

    if remove_legacy:
        legacy.unlink()
    return written
