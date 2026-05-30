# pyright: strict
"""RSS/Atom news source (Fase 3, ADR-017).

Most free news feeds (CoinDesk, Cointelegraph, Google News aggregations of
Reuters/Bloomberg) expose RSS 2.0 or Atom. Both are simple XML, so we parse
with the stdlib (``xml.etree``) — no new dependency, per CLAUDE.md.

``parse_rss`` is a pure function over the feed bytes/string, so it is fully
testable offline with fixtures (important: the news hosts are behind the
environment allowlist and may be unreachable during development). ``RSSNewsSource``
adds only the HTTP fetch and rate-limit handling, mirroring the other sources.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Final
from xml.etree import ElementTree as ET

import requests

from src.ingestion.news.base import NewsItem, NewsSource

logger = logging.getLogger(__name__)

DEFAULT_REQUEST_TIMEOUT: Final[float] = 20.0
DEFAULT_MAX_RETRIES: Final[int] = 3
DEFAULT_BACKOFF_BASE: Final[float] = 5.0

# Atom namespace (RSS 2.0 elements are unqualified).
_ATOM_NS: Final[str] = "{http://www.w3.org/2005/Atom}"


def _parse_datetime(raw: str) -> datetime | None:
    """Parse an RSS (RFC 822) or Atom (ISO 8601) date into tz-aware UTC.

    Returns ``None`` if the string is missing or unparseable — the caller
    skips items without a usable timestamp rather than guessing.
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    # RSS 2.0: "Mon, 06 Jan 2025 14:30:00 +0000"
    try:
        dt = parsedate_to_datetime(raw)
        return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        pass
    # Atom: ISO 8601, possibly ending in 'Z'
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
    except ValueError:
        return None


def _text(elem: ET.Element | None) -> str:
    return (elem.text or "").strip() if elem is not None else ""


def _parse_rss_item(item: ET.Element, source: str) -> NewsItem | None:
    title = _text(item.find("title"))
    link = _text(item.find("link"))
    guid = _text(item.find("guid")) or link
    published = _parse_datetime(_text(item.find("pubDate")))
    summary = _text(item.find("description"))
    if not title or published is None:
        return None
    return NewsItem(
        item_id=guid or link or title,
        source=source,
        title=title,
        url=link,
        published=published,
        summary=summary,
    )


def _parse_atom_entry(entry: ET.Element, source: str) -> NewsItem | None:
    title = _text(entry.find(f"{_ATOM_NS}title"))
    guid = _text(entry.find(f"{_ATOM_NS}id"))
    published = _parse_datetime(
        _text(entry.find(f"{_ATOM_NS}published")) or _text(entry.find(f"{_ATOM_NS}updated"))
    )
    summary = _text(entry.find(f"{_ATOM_NS}summary"))
    # Atom links carry the URL in an href attribute; prefer rel="alternate".
    url = ""
    for link in entry.findall(f"{_ATOM_NS}link"):
        href = link.get("href", "")
        if link.get("rel", "alternate") == "alternate" and href:
            url = href
            break
        if href and not url:
            url = href
    if not title or published is None:
        return None
    return NewsItem(
        item_id=guid or url or title,
        source=source,
        title=title,
        url=url,
        published=published,
        summary=summary,
    )


def parse_rss(content: str | bytes, source: str) -> list[NewsItem]:
    """Parse RSS 2.0 or Atom feed content into ``NewsItem`` list (newest-first).

    Pure function: no network. Malformed individual entries are skipped (and
    counted in a debug log), not fatal — a single bad item must not drop the
    whole feed. Raises ``ValueError`` only if the document itself is not XML.
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError(f"feed content is not valid XML: {exc}") from exc

    items: list[NewsItem] = []
    skipped = 0

    # RSS 2.0: <rss><channel><item>... ; Atom: <feed><entry>...
    rss_items = root.findall(".//item")
    if rss_items:
        for it in rss_items:
            parsed = _parse_rss_item(it, source)
            if parsed is None:
                skipped += 1
            else:
                items.append(parsed)
    else:
        for entry in root.findall(f".//{_ATOM_NS}entry"):
            parsed = _parse_atom_entry(entry, source)
            if parsed is None:
                skipped += 1
            else:
                items.append(parsed)

    if skipped:
        logger.debug("parse_rss(%s): skipped %d malformed entries", source, skipped)
    items.sort(key=lambda i: i.published, reverse=True)
    return items


class RSSNewsSource(NewsSource):
    """News source backed by an RSS/Atom feed URL."""

    def __init__(
        self,
        name: str,
        feed_url: str,
        session: requests.Session | None = None,
        request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        user_agent: str = "market-analysis-research/0.1 (+research)",
    ) -> None:
        self._name = name
        self._feed_url = feed_url
        self._session = session or requests.Session()
        self._timeout = request_timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._user_agent = user_agent

    @property
    def name(self) -> str:
        return self._name

    def fetch(self, limit: int | None = None) -> list[NewsItem]:
        """Fetch and parse the feed, newest-first, capped at ``limit``."""
        logger.info("Fetching RSS feed %s from %s", self._name, self._feed_url)
        content = self._get()
        items = parse_rss(content, self._name)
        return items[:limit] if limit is not None else items

    def _get(self) -> bytes:
        headers = {"User-Agent": self._user_agent}
        attempt = 0
        while True:
            resp = self._session.get(self._feed_url, headers=headers, timeout=self._timeout)
            if resp.status_code == 429:
                attempt += 1
                if attempt > self._max_retries:
                    raise RuntimeError(
                        f"RSS feed {self._name} rate-limited (429) after "
                        f"{self._max_retries} retries."
                    )
                wait = self._backoff_base * (2 ** (attempt - 1))
                logger.warning(
                    "RSS %s 429: retry %d/%d in %.0fs",
                    self._name,
                    attempt,
                    self._max_retries,
                    wait,
                )
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.content
