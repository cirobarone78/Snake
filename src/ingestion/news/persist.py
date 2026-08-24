"""Append-and-dedup persistence for news items (Fase 3).

News is an append-only log: each fetch returns the most recent items, which
overlap heavily with previous fetches. We accumulate them into one parquet per
source, deduped on ``item_id`` (the feed GUID), so history grows without
duplicates regardless of fetch cadence (Q10: batch-friendly).

Pure I/O over pandas frames, so it unit-tests without network. The frame shape
is the one produced by ``news_to_frame``: a ``published`` DatetimeIndex (UTC)
with columns ``item_id, source, title, url, summary``.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pandas as pd


def append_news(frame: pd.DataFrame, path: str | Path) -> pd.DataFrame:
    """Append ``frame`` to the parquet at ``path``, deduped on ``item_id``.

    On re-fetch the same story (same ``item_id``) is kept once. The *newly
    fetched* version wins (``keep="last"``) so an updated title/summary refreshes
    in place. The merged history is written back in the canonical order of
    ``sort_canonical`` — byte-stable, so an unchanged file stays identical.
    Returns the merged frame.

    An empty ``frame`` is a no-op: the existing history (if any) is returned
    unchanged, never truncated.
    """
    path = Path(path)
    if frame.empty:
        if path.exists():
            return cast("pd.DataFrame", pd.read_parquet(path))
        return frame

    if path.exists():
        existing = pd.read_parquet(path)
        combined = pd.concat([existing, frame])
    else:
        combined = frame

    combined = combined[~combined["item_id"].duplicated(keep="last")]
    combined = sort_canonical(cast("pd.DataFrame", combined))

    path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(path)
    return cast("pd.DataFrame", combined)


def sort_canonical(frame: pd.DataFrame) -> pd.DataFrame:
    """Order rows by ``(published, item_id)`` — a total order, independent of arrival.

    Sorting by ``published`` alone is *not* enough, and the difference is not
    cosmetic. Feeds date most headlines to the day, so the vast majority of rows
    in a partition share a timestamp (measured: 88 of 101 in one real month).
    ``sort_index`` is stable, so those tied rows keep whatever order the input
    happened to have — and the input order changes on every run, because
    deduplication with ``keep="last"`` moves each re-fetched story to the end.

    Same rows, different byte layout, every single time. That silently defeated
    the whole point of ADR-033: the first cron run after partitioning rewrote 20
    of 92 partitions and 26.9MB, 17 of them with **zero** row changes. Adding
    ``item_id`` (unique) to the sort key makes the file a pure function of its
    contents, so an unchanged partition serialises to identical bytes and git
    stores no new blob.
    """
    if frame.empty:
        return frame
    index_name = frame.index.name
    ordered = frame.reset_index().sort_values(
        ["published", "item_id"], kind="stable", ignore_index=True
    )
    return cast("pd.DataFrame", ordered.set_index(index_name))
