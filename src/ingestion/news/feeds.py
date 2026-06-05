# pyright: strict
"""Concrete news feed registry (Fase 3, ADR-017).

RSS/Atom parsing and HTTP fetch live in ``rss.py`` (source-agnostic). Here we
pin the *actual* feeds we ingest:

- **General crypto newswires** (Cointelegraph, Decrypt): broad market coverage,
  native RSS. (CoinDesk's public RSS endpoint serves an anti-bot JS wall rather
  than the feed for our UA/IP — not circumvented, per ADR-018 — so it is left
  out; Google News still surfaces CoinDesk stories via aggregation.)
- **Google News search aggregations** per Tier 1 crypto asset: pull in Reuters /
  Bloomberg / mainstream coverage we can't get from a single outlet, and give
  per-asset attribution for free (ROADMAP Fase 3: "≥2 fonti").
- **Google News search aggregations** per equity sector/theme ETF: the equity
  analogue, so move attribution on the sector ETFs (Fase 8) has a news channel
  too. Same machinery, equity-domain queries (no "crypto" qualifier).

Feeds are *data, not code*: adding a source is one entry here, no new class.
Non-RSS sources (Twitter/Reddit) come later behind the same ``NewsSource``
interface.
"""

from __future__ import annotations

from typing import Final
from urllib.parse import quote_plus

from src.assets.asset import TIER1_ASSETS, Asset
from src.assets.sectors import SECTOR_ETFS
from src.ingestion.news.rss import RSSNewsSource

# General crypto newswires (broad market coverage). name -> feed URL.
GENERAL_FEEDS: Final[dict[str, str]] = {
    "cointelegraph": "https://cointelegraph.com/rss",
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
}

# Curated Google News search per equity sector/theme ETF. Natural-language terms
# that map to mainstream financial coverage (Reuters/Bloomberg/CNBC), chosen to
# avoid ambiguous tickers — the equity analogue of ``asset_news_query`` but with
# no "crypto" qualifier. Keyed by the sector's project symbol (sectors.py).
SECTOR_NEWS_QUERIES: Final[dict[str, str]] = {
    "TECH": "technology sector stocks",
    "ENERGY": "energy sector stocks",
    "FINANCE": "bank stocks financial sector",
    "HEALTH": "healthcare sector stocks",
    "INDUSTRIAL": "industrial sector stocks",
    "UTILITIES": "utilities sector stocks",
    "STAPLES": "consumer staples stocks",
    "DISCRETIONARY": "consumer discretionary stocks",
    "MATERIALS": "materials sector stocks",
    "REALESTATE": "real estate REIT stocks",
    "COMMSERV": "communication services stocks",
    "SEMIS": "semiconductor stocks",
    "URANIUM": "uranium nuclear energy stocks",
    "CLEANENERGY": "clean energy renewable stocks",
    "OILGAS": "oil and gas stocks",
    "DEFENSE": "defense aerospace stocks",
    "ROBOTICS": "robotics AI stocks",
    "CYBER": "cybersecurity stocks",
    "BIOTECH": "biotech stocks",
    "GOLD_MINERS": "gold mining stocks",
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


def sector_news_query(asset: Asset) -> str:
    """Equity search query for a sector ETF.

    Uses the curated ``SECTOR_NEWS_QUERIES`` term; falls back to the ETF's name
    (sans the ``(TICKER)`` suffix) plus "stocks" for any sector not pinned there.
    Unlike ``asset_news_query`` it never adds "crypto".
    """
    pinned = SECTOR_NEWS_QUERIES.get(asset.symbol)
    if pinned is not None:
        return pinned
    base = asset.name.split("(")[0].strip()
    return f"{base} stocks"


def sector_news_sources(assets: list[Asset] = SECTOR_ETFS) -> list[RSSNewsSource]:
    """One Google News source per sector ETF, named ``googlenews_<symbol>``."""
    return [
        RSSNewsSource(
            name=f"googlenews_{asset.symbol.lower()}",
            feed_url=google_news_feed_url(sector_news_query(asset)),
        )
        for asset in assets
    ]


def default_news_sources() -> list[RSSNewsSource]:
    """All feeds ingested by default.

    General crypto newswires + per-crypto-asset aggregations + per-equity-sector
    aggregations, so the single daily news cron accumulates both universes.
    """
    return general_news_sources() + asset_news_sources() + sector_news_sources()
