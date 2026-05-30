"""Offline tests for the compact, versioned news history (ADR-025). No network."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from src.ingestion.news.base import NewsItem, news_to_frame
from src.ingestion.news.history import COMPACT_COLUMNS, to_compact, update_history


def _item(item_id: str, day: int, title: str = "Bitcoin rallies on strong gains") -> NewsItem:
    return NewsItem(
        item_id=item_id,
        source="test",
        title=title,
        url=f"https://example.com/{item_id}",
        published=datetime(2025, 1, day, tzinfo=UTC),
        summary="some long summary text we do not want to version",
    )


def test_to_compact_drops_summary_adds_sentiment() -> None:
    compact = to_compact(news_to_frame([_item("a", 1)]))
    assert list(compact.columns) == COMPACT_COLUMNS
    assert "summary" not in compact.columns
    assert "sentiment" in compact.columns
    assert compact.index.name == "published"


def test_to_compact_empty() -> None:
    compact = to_compact(news_to_frame([]))
    assert compact.empty
    assert list(compact.columns) == COMPACT_COLUMNS


def test_update_history_accumulates_and_dedups(tmp_path: Path) -> None:
    path = tmp_path / "news.parquet"
    update_history(news_to_frame([_item("a", 1), _item("b", 2)]), path)
    # second run overlaps on "b", adds "c"
    merged = update_history(news_to_frame([_item("b", 2), _item("c", 3)]), path)
    assert list(merged["item_id"]) == ["a", "b", "c"]
    assert "summary" not in merged.columns
    assert path.exists()


def test_update_history_empty_preserves(tmp_path: Path) -> None:
    path = tmp_path / "news.parquet"
    update_history(news_to_frame([_item("a", 1)]), path)
    merged = update_history(news_to_frame([]), path)
    assert len(merged) == 1
