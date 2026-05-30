"""Tests for news ingestion — RSS/Atom parsing, normalisation, dedup."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.ingestion.news.base import NewsItem, news_to_frame
from src.ingestion.news.rss import RSSNewsSource, parse_rss

# --- fixtures (inline, offline) ---

RSS_2_0 = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Crypto News</title>
    <item>
      <title>Bitcoin surges past resistance</title>
      <link>https://example.com/btc-surge</link>
      <guid>guid-001</guid>
      <pubDate>Mon, 06 Jan 2025 14:30:00 +0000</pubDate>
      <description>BTC up 5% on the day.</description>
    </item>
    <item>
      <title>Ethereum upgrade scheduled</title>
      <link>https://example.com/eth-upgrade</link>
      <guid>guid-002</guid>
      <pubDate>Tue, 07 Jan 2025 09:00:00 +0000</pubDate>
      <description>Devs announce date.</description>
    </item>
  </channel>
</rss>"""

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Crypto</title>
  <entry>
    <title>Solana hits new high</title>
    <id>atom-001</id>
    <link rel="alternate" href="https://example.com/sol-high"/>
    <published>2025-01-08T12:00:00Z</published>
    <summary>SOL rallies.</summary>
  </entry>
</feed>"""


# --- parse_rss ---


def test_parse_rss_2_0() -> None:
    items = parse_rss(RSS_2_0, source="cryptonews")
    assert len(items) == 2
    # newest-first: 07 Jan before 06 Jan
    assert items[0].item_id == "guid-002"
    assert items[1].item_id == "guid-001"
    first = items[1]
    assert first.title == "Bitcoin surges past resistance"
    assert first.url == "https://example.com/btc-surge"
    assert first.source == "cryptonews"
    assert first.summary == "BTC up 5% on the day."
    assert first.published == datetime(2025, 1, 6, 14, 30, tzinfo=UTC)


def test_parse_atom() -> None:
    items = parse_rss(ATOM, source="atomnews")
    assert len(items) == 1
    it = items[0]
    assert it.item_id == "atom-001"
    assert it.title == "Solana hits new high"
    assert it.url == "https://example.com/sol-high"
    assert it.published == datetime(2025, 1, 8, 12, 0, tzinfo=UTC)


def test_parse_skips_malformed_entries() -> None:
    # second item has no title and no date -> skipped, first still parsed
    feed = """<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>Good</title><link>u1</link><guid>g1</guid>
        <pubDate>Mon, 06 Jan 2025 14:30:00 +0000</pubDate></item>
      <item><link>u2</link></item>
    </channel></rss>"""
    items = parse_rss(feed, source="s")
    assert len(items) == 1
    assert items[0].title == "Good"


def test_parse_invalid_xml_raises() -> None:
    with pytest.raises(ValueError, match="not valid XML"):
        parse_rss("this is not xml <<<", source="s")


def test_parse_empty_feed() -> None:
    feed = '<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
    assert parse_rss(feed, source="s") == []


# --- news_to_frame ---


def test_news_to_frame_shape_and_sort() -> None:
    items = parse_rss(RSS_2_0, source="cryptonews")
    df = news_to_frame(items)
    assert list(df.columns) == ["item_id", "source", "title", "url", "summary"]
    assert df.index.name == "published"
    assert str(df.index.tz) == "UTC"
    # frame is sorted ascending by published
    assert df.index.is_monotonic_increasing
    assert df.iloc[0]["item_id"] == "guid-001"


def test_news_to_frame_dedup() -> None:
    base = parse_rss(RSS_2_0, source="cryptonews")
    # simulate the same story appearing twice across fetches
    df = news_to_frame(base + base)
    assert len(df) == 2
    assert not df["item_id"].duplicated().any()


def test_news_to_frame_empty() -> None:
    df = news_to_frame([])
    assert df.empty
    assert list(df.columns) == ["item_id", "source", "title", "url", "summary"]
    assert df.index.name == "published"


# --- NewsItem invariant ---


def test_newsitem_requires_tzaware() -> None:
    with pytest.raises(ValueError, match="tz-aware"):
        NewsItem(
            item_id="x",
            source="s",
            title="t",
            url="u",
            published=datetime(2025, 1, 1),  # naive
        )


# --- RSSNewsSource with a fake session (offline) ---


class _FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self, content: bytes) -> None:
        self._content = content
        self.calls = 0

    def get(self, url: str, headers: dict[str, str], timeout: float) -> _FakeResponse:
        self.calls += 1
        return _FakeResponse(self._content)


def test_rss_source_fetch_with_fake_session() -> None:
    session = _FakeSession(RSS_2_0.encode("utf-8"))
    src = RSSNewsSource(name="cryptonews", feed_url="https://x/feed", session=session)  # type: ignore[arg-type]
    items = src.fetch()
    assert session.calls == 1
    assert len(items) == 2
    assert src.name == "cryptonews"


def test_rss_source_respects_limit() -> None:
    session = _FakeSession(RSS_2_0.encode("utf-8"))
    src = RSSNewsSource(name="cryptonews", feed_url="https://x/feed", session=session)  # type: ignore[arg-type]
    items = src.fetch(limit=1)
    assert len(items) == 1
    # newest-first -> the 07 Jan item
    assert items[0].item_id == "guid-002"
