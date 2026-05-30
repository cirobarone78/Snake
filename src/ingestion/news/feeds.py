# pyright: strict
"""Concrete news feed registry (Fase 3, ADR-017).

RSS/Atom parsing and HTTP fetch live in ``rss.py`` (source-agnostic). Here we
pin the *actual* feeds we ingest:

- **General crypto newswires** (Cointelegraph, Decrypt): broad market coverage,
  native RSS. (CoinDesk's public RSS endpoint serves an anti-bot JS wall rather
  than the feed for our UA/IP — not circumvented, per ADR-018 — so it is left
  out; Google News still surfaces CoinDesk stories via aggregation.)
- **Google News search aggregations** per Tier 1 asset: pull in Reuters /
  Bloomberg / mainstream coverage we can't get from a single outlet, and give
  per-asset attribution for free (ROADMAP Fase 3: "≥2 fonti").

Feeds are *data, not code*: adding a source is one entry here, no new class.
Non-RSS sources (Twitter/Reddit) come later behind the same ``NewsSource``
interface.
"""

from __future__ import annotations

from typing import Final
from urllib.parse import quote_plus

from src.assets.asset import Asset, TIER1_ASSETS
from src.ingestion.news.rss import RSSNewsSource

# General crypto newswires (broad market coverage). name -> feed URL.
GENERAL_FEEDS: Final[dict[str, str]] = {
    "cointelegraph": "https://cointelegraph.com/rss",
    "decrypt": "https://decrypt.co/feed",
}

# Google News exposes any search as an RSS feed; we aggregate per asset.
_GOOGLE_NEWS_RSS: Final[str] = (
    "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
)


def google_news_feed_url(query: str) -> str:
    """Build the Google News RSS URL for a free-text search query."""
    return _GOOGLE_NEWS_RSS.format(query=quote_plus(query))


def asset_news_query(asset: Asset) -> str:
    """Search query for an asset.

    Name + symbol + "crypto" disambiguates tickers that collide with common
    words (e.g. POL/Polygon, LINK) and keeps results in the crypto domain.
    """
    return f"{asset.name} {asset.symbol} crypto"


def general_news_sources() -> list[RSSNewsSource]:
    """Concrete sources for the general crypto newswires."""
    return [RSSNewsSource(name, url) for name, url in GENERAL_FEEDS.items()]


def asset_news_sources(assets: list[Asset] = TIER1_ASSETS) -> list[RSSNewsSource]:
    """One Google News source per asset, named ``googlenews_<symbol>``."""
    return [
        RSSNewsSource(
            name=f"googlenews_{asset.symbol.lower()}",
            feed_url=google_news_feed_url(asset_news_query(asset)),
        )
        for asset in assets
    ]


def default_news_sources() -> list[RSSNewsSource]:
    """All feeds ingested by default: general newswires + per-asset aggregations."""
    return general_news_sources() + asset_news_sources()
