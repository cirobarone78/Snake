"""Abstract news source interface and the normalised news item (Fase 3).

A ``NewsItem`` is the project-canonical shape every news source must produce,
regardless of feed format (RSS, Atom, JSON API). Keeping the shape stable here
means downstream NLP/feature code never sees source-specific quirks.

Design mirrors ``src.ingestion.base``: the pipeline depends on the abstraction
``NewsSource``, concrete feeds implement it. Intentionally minimal — we add
fields only when a concrete need appears (no speculative schema).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import cast

import pandas as pd


@dataclass(frozen=True)
class NewsItem:
    """One normalised news item.

    Timestamps are tz-aware UTC. ``published`` is the publication time as
    reported by the feed (Q12: we use publication time, not event time —
    the only timestamp feeds reliably give). ``source`` is the stable source
    identifier (``NewsSource.name``), kept on the item so multi-source frames
    stay attributable. ``item_id`` is the feed's GUID/link, used to dedupe
    across repeated fetches.
    """

    item_id: str
    source: str
    title: str
    url: str
    published: datetime
    summary: str = ""

    def __post_init__(self) -> None:
        if self.published.tzinfo is None:
            raise ValueError("NewsItem.published must be tz-aware (UTC)")


class NewsSource(ABC):
    """Base for any news feed. Concrete feeds normalise to ``NewsItem``."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier for the source. Used in storage paths and logs."""

    @abstractmethod
    def fetch(self, limit: int | None = None) -> list[NewsItem]:
        """Return recent news items, newest-first, normalised to ``NewsItem``.

        Implementations must surface partial failures (return what parsed,
        log what was skipped) rather than raising on a single malformed entry.
        ``limit`` caps the number of items returned when set.
        """


def news_to_frame(items: list[NewsItem]) -> pd.DataFrame:
    """Normalise news items into a time-indexed DataFrame.

    Index: tz-aware UTC ``DatetimeIndex`` named ``published`` (sorted
    ascending). Columns: ``item_id, source, title, url, summary``. Duplicate
    ``item_id`` rows (same story seen in repeated fetches) are dropped, keeping
    the first occurrence. An empty input yields a correctly-typed empty frame.
    """
    cols = ["item_id", "source", "title", "url", "summary"]
    if not items:
        return pd.DataFrame(columns=cols, index=pd.DatetimeIndex([], name="published", tz="UTC"))
    df = pd.DataFrame(
        {
            "item_id": [i.item_id for i in items],
            "source": [i.source for i in items],
            "title": [i.title for i in items],
            "url": [i.url for i in items],
            "summary": [i.summary for i in items],
        },
        index=pd.DatetimeIndex(
            pd.to_datetime([i.published for i in items], utc=True), name="published"
        ),
    )
    df = df[~df["item_id"].duplicated(keep="first")]
    return cast("pd.DataFrame", df.sort_index())
