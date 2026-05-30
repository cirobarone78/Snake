"""Offline tests for the news feed registry (Fase 3). No network."""

from __future__ import annotations

from src.assets.asset import TIER1_ASSETS
from src.ingestion.news.feeds import (
    GENERAL_FEEDS,
    asset_news_query,
    asset_news_sources,
    default_news_sources,
    general_news_sources,
    google_news_feed_url,
)
from src.ingestion.news.rss import RSSNewsSource


def test_general_sources_match_registry() -> None:
    sources = general_news_sources()
    assert {s.name for s in sources} == set(GENERAL_FEEDS)
    assert all(isinstance(s, RSSNewsSource) for s in sources)


def test_google_news_url_is_query_encoded() -> None:
    url = google_news_feed_url("Polygon POL crypto")
    # spaces must be percent-encoded, not left raw
    assert " " not in url
    assert "Polygon" in url and "POL" in url
    assert url.startswith("https://news.google.com/rss/search?q=")


def test_asset_query_includes_name_and_symbol() -> None:
    btc = next(a for a in TIER1_ASSETS if a.symbol == "BTC")
    query = asset_news_query(btc)
    assert "Bitcoin" in query
    assert "BTC" in query


def test_asset_sources_one_per_asset_named_by_symbol() -> None:
    sources = asset_news_sources()
    assert len(sources) == len(TIER1_ASSETS)
    names = {s.name for s in sources}
    assert "googlenews_btc" in names
    assert "googlenews_pol" in names


def test_default_sources_combine_general_and_per_asset() -> None:
    total = len(GENERAL_FEEDS) + len(TIER1_ASSETS)
    sources = default_news_sources()
    assert len(sources) == total
    # names are unique across the whole set
    assert len({s.name for s in sources}) == total
