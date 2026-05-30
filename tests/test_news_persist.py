"""Offline tests for news persistence (append + dedup). No network."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from src.ingestion.news.base import NewsItem, news_to_frame
from src.ingestion.news.persist import append_news


def _item(item_id: str, day: int, title: str = "t") -> NewsItem:
    return NewsItem(
        item_id=item_id,
        source="example",
        title=title,
        url=f"https://example.com/{item_id}",
        published=datetime(2025, 1, day, tzinfo=UTC),
    )


def test_first_write_creates_file(tmp_path: Path) -> None:
    path = tmp_path / "example.parquet"
    frame = news_to_frame([_item("a", 1), _item("b", 2)])
    merged = append_news(frame, path)
    assert path.exists()
    assert len(merged) == 2


def test_append_accumulates_and_dedups(tmp_path: Path) -> None:
    path = tmp_path / "example.parquet"
    append_news(news_to_frame([_item("a", 1), _item("b", 2)]), path)
    # second fetch overlaps on "b" and adds "c"
    merged = append_news(news_to_frame([_item("b", 2), _item("c", 3)]), path)
    assert list(merged["item_id"]) == ["a", "b", "c"]  # sorted by published
    assert len(merged) == 3


def test_refetch_updates_in_place(tmp_path: Path) -> None:
    path = tmp_path / "example.parquet"
    append_news(news_to_frame([_item("a", 1, title="old")]), path)
    merged = append_news(news_to_frame([_item("a", 1, title="new")]), path)
    assert len(merged) == 1
    assert merged["title"].iloc[0] == "new"  # newly fetched version wins


def test_empty_frame_is_noop_and_preserves_history(tmp_path: Path) -> None:
    path = tmp_path / "example.parquet"
    append_news(news_to_frame([_item("a", 1)]), path)
    merged = append_news(news_to_frame([]), path)
    assert len(merged) == 1


def test_empty_frame_no_existing_file_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "nope.parquet"
    merged = append_news(news_to_frame([]), path)
    assert merged.empty
    assert not path.exists()
