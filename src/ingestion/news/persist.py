# pyright: strict
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
    in place. The merged history is sorted ascending by ``published`` and
    written back. Returns the merged frame.

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
    combined = combined.sort_index()

    path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(path)
    return cast("pd.DataFrame", combined)
