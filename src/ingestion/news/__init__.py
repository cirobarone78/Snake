"""News ingestion (Fase 3, ADR-017).

The informational, non-numeric dimension: headlines and articles whose
sentiment/volume may carry predictive signal (to be tested, not assumed —
VISION). Sources are abstracted behind ``NewsSource`` so the pipeline depends
on the interface, not on any specific feed (RSS today; Twitter/Reddit later
per ROADMAP Fase 3).

This package handles only *acquisition and normalisation* of news items.
Sentiment scoring / NLP is a separate concern (depends on the model stack,
ADR-016 Layer 1) and lives elsewhere.
"""

from __future__ import annotations

from src.ingestion.news.base import NewsItem, NewsSource, news_to_frame
from src.ingestion.news.feeds import default_news_sources
from src.ingestion.news.persist import append_news
from src.ingestion.news.rss import RSSNewsSource, parse_rss

__all__ = [
    "NewsItem",
    "NewsSource",
    "RSSNewsSource",
    "append_news",
    "default_news_sources",
    "news_to_frame",
    "parse_rss",
]
