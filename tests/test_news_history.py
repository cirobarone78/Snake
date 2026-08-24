"""Offline tests for the compact, versioned news history (ADR-025/033). No network."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.ingestion.news.base import NewsItem, news_to_frame
from src.ingestion.news.history import (
    COMPACT_COLUMNS,
    LEGACY_FILENAME,
    migrate_to_partitions,
    partition_files,
    partition_path,
    read_news_history,
    to_compact,
    update_history,
)
from src.ingestion.news.persist import sort_canonical


def _item(
    item_id: str,
    day: int,
    title: str = "Bitcoin rallies on strong gains",
    month: int = 1,
) -> NewsItem:
    return NewsItem(
        item_id=item_id,
        source="test",
        title=title,
        url=f"https://example.com/{item_id}",
        published=datetime(2025, month, day, tzinfo=UTC),
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
    update_history(news_to_frame([_item("a", 1), _item("b", 2)]), tmp_path)
    # second run overlaps on "b", adds "c"
    merged = update_history(news_to_frame([_item("b", 2), _item("c", 3)]), tmp_path)
    assert list(merged["item_id"]) == ["a", "b", "c"]
    assert "summary" not in merged.columns


def test_update_history_empty_preserves(tmp_path: Path) -> None:
    update_history(news_to_frame([_item("a", 1)]), tmp_path)
    merged = update_history(news_to_frame([]), tmp_path)
    assert len(merged) == 1


def test_read_empty_directory_returns_typed_empty_frame(tmp_path: Path) -> None:
    history = read_news_history(tmp_path)
    assert history.empty
    assert list(history.columns) == COMPACT_COLUMNS
    assert history.index.name == "published"


# --- ADR-033: monthly partitioning ------------------------------------------


def test_writes_one_file_per_publication_month(tmp_path: Path) -> None:
    update_history(
        news_to_frame([_item("jan", 5, month=1), _item("feb", 5, month=2)]),
        tmp_path,
    )
    names = sorted(p.name for p in tmp_path.glob("*.parquet"))
    assert names == ["news_2025-01.parquet", "news_2025-02.parquet"]


def test_multi_partition_read_equals_monolithic_read(tmp_path: Path) -> None:
    """Two synthetic months, read back as one frame ≡ the pre-ADR-033 layout."""
    items = [_item("jan-a", 3, month=1), _item("jan-b", 20, month=1), _item("feb-a", 7, month=2)]
    frame = news_to_frame(items)

    monolith_dir = tmp_path / "monolith"
    monolith_dir.mkdir()
    to_compact(frame).to_parquet(monolith_dir / LEGACY_FILENAME)

    partitioned_dir = tmp_path / "partitioned"
    update_history(frame, partitioned_dir)

    monolithic = read_news_history(monolith_dir)
    partitioned = read_news_history(partitioned_dir)
    pd.testing.assert_frame_equal(monolithic, partitioned)


def test_append_only_rewrites_the_touched_partition(tmp_path: Path) -> None:
    """The point of ADR-033: a run must not rewrite past months."""
    update_history(news_to_frame([_item("jan", 5, month=1)]), tmp_path)
    january = partition_path(tmp_path, "2025-01")
    untouched = january.read_bytes()

    update_history(news_to_frame([_item("feb", 5, month=2)]), tmp_path)

    assert january.read_bytes() == untouched
    assert partition_path(tmp_path, "2025-02").exists()


def test_append_is_idempotent_on_the_current_month(tmp_path: Path) -> None:
    frame = news_to_frame([_item("a", 1), _item("b", 2)])
    update_history(frame, tmp_path)
    first = partition_path(tmp_path, "2025-01").read_bytes()
    merged = update_history(frame, tmp_path)
    assert len(merged) == 2
    assert partition_path(tmp_path, "2025-01").read_bytes() == first


def test_refetched_story_updates_in_place_within_its_partition(tmp_path: Path) -> None:
    update_history(news_to_frame([_item("a", 1, title="old")]), tmp_path)
    merged = update_history(news_to_frame([_item("a", 1, title="new")]), tmp_path)
    assert len(merged) == 1
    assert merged["title"].iloc[0] == "new"


def test_read_dedups_the_same_story_across_partitions(tmp_path: Path) -> None:
    """A feed re-dating a story leaves a stale copy behind; the read keeps one."""
    update_history(news_to_frame([_item("a", 28, title="old", month=1)]), tmp_path)
    update_history(news_to_frame([_item("a", 2, title="new", month=2)]), tmp_path)
    history = read_news_history(tmp_path)
    assert len(history) == 1
    assert history["title"].iloc[0] == "new"  # the later partition wins


# --- ADR-033: one-shot migration --------------------------------------------


def test_migration_preserves_rows_and_schema(tmp_path: Path) -> None:
    items = [_item(f"i{n}", 1 + n % 27, month=1 + n % 3) for n in range(40)]
    compact = to_compact(news_to_frame(items))
    (tmp_path / LEGACY_FILENAME).parent.mkdir(parents=True, exist_ok=True)
    compact.to_parquet(tmp_path / LEGACY_FILENAME)

    written = migrate_to_partitions(tmp_path)

    assert sum(written.values()) == len(compact)
    assert sorted(written) == ["2025-01", "2025-02", "2025-03"]
    assert not (tmp_path / LEGACY_FILENAME).exists()

    migrated = read_news_history(tmp_path)
    assert len(migrated) == len(compact)
    assert list(migrated.columns) == list(compact.columns)
    # Column-by-column round-trip: no row silently mangled by the split.
    # Compare in the canonical order the partitions are written in — sorting the
    # expectation by ``published`` alone would leave same-day rows tied and the
    # comparison would depend on input order, which is exactly what we removed.
    canonical = sort_canonical(compact)
    for column in compact.columns:
        expected = canonical[column].reset_index(drop=True)
        actual = migrated[column].reset_index(drop=True)
        pd.testing.assert_series_equal(expected, actual, check_names=False)


def test_migration_is_a_noop_without_a_monolith(tmp_path: Path) -> None:
    update_history(news_to_frame([_item("a", 1)]), tmp_path)
    assert migrate_to_partitions(tmp_path) == {}
    assert len(read_news_history(tmp_path)) == 1


def test_legacy_monolith_is_still_readable_alongside_partitions(tmp_path: Path) -> None:
    """A checkout made before the migration commit must not lose its history."""
    to_compact(news_to_frame([_item("old", 1)])).to_parquet(tmp_path / LEGACY_FILENAME)
    update_history(news_to_frame([_item("new", 2, month=2)]), tmp_path)
    assert sorted(read_news_history(tmp_path)["item_id"]) == ["new", "old"]
    assert [p.name for p in partition_files(tmp_path)] == [
        LEGACY_FILENAME,
        "news_2025-02.parquet",
    ]


# --- ADR-033: byte stability (regressione dal primo run reale del cron) ------


def _tied_item(item_id: str, day: int, month: int = 1) -> NewsItem:
    """A headline dated to the day — the shape feeds actually deliver."""
    return NewsItem(
        item_id=item_id,
        source="test",
        title=f"Headline {item_id}",
        url=f"https://example.com/{item_id}",
        published=datetime(2025, month, day, 7, 0, tzinfo=UTC),
        summary="dropped by to_compact",
    )


def test_refetch_in_different_order_leaves_bytes_identical(tmp_path: Path) -> None:
    """The bug that made the first live run rewrite 26.9MB.

    Feeds date most headlines to the day, so rows tie on ``published``, and the
    dedup moves each re-fetched story to the end of the frame. With a sort on
    ``published`` alone — stable, hence input-order-preserving — the same rows
    serialised differently on every run, so git stored a new blob every time and
    partitioning saved nothing. The order must come from the content, not from
    the order of arrival.
    """
    items = [_tied_item(f"i{n}", 5) for n in range(12)]
    update_history(news_to_frame(items), tmp_path)
    before = partition_path(tmp_path, "2025-01").read_bytes()

    # Same stories, arriving in a different order — as a feed re-serves them.
    reshuffled = [items[7], items[0], items[11], *items[1:7], *items[8:11]]
    update_history(news_to_frame(reshuffled), tmp_path)

    assert partition_path(tmp_path, "2025-01").read_bytes() == before


def test_partial_refetch_leaves_bytes_identical(tmp_path: Path) -> None:
    """A run that re-sees only *some* of a month's stories must not rewrite it."""
    items = [_tied_item(f"i{n}", 5) for n in range(12)]
    update_history(news_to_frame(items), tmp_path)
    before = partition_path(tmp_path, "2025-01").read_bytes()

    update_history(news_to_frame([items[9], items[2], items[5]]), tmp_path)

    assert partition_path(tmp_path, "2025-01").read_bytes() == before


def test_an_added_story_does_not_disturb_the_order_of_the_others(tmp_path: Path) -> None:
    """A genuinely new row is appended; the rest keep their canonical places."""
    items = [_tied_item(f"i{n}", 5) for n in range(6)]
    update_history(news_to_frame(items), tmp_path)

    update_history(news_to_frame([_tied_item("i9", 5)]), tmp_path)
    history = read_news_history(tmp_path)

    assert len(history) == 7
    # (published, item_id) is a total order: same timestamp -> item_id decides.
    assert list(history["item_id"]) == sorted(history["item_id"])


def test_write_order_is_independent_of_arrival_order(tmp_path: Path) -> None:
    """Two directories fed the same stories in different orders match byte for byte."""
    items = [_tied_item(f"i{n}", 5) for n in range(10)]
    forward, backward = tmp_path / "fwd", tmp_path / "bwd"

    update_history(news_to_frame(items[:5]), forward)
    update_history(news_to_frame(items[5:]), forward)
    update_history(news_to_frame(items[5:][::-1]), backward)
    update_history(news_to_frame(items[:5][::-1]), backward)

    assert (
        partition_path(forward, "2025-01").read_bytes()
        == partition_path(backward, "2025-01").read_bytes()
    )
