"""Tests for write_snapshot — single-row and multi-row append semantics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.ingestion.snapshot import write_snapshot


@pytest.fixture
def tmp_paths(tmp_path: Path) -> tuple[Path, Path]:
    return tmp_path / "x_latest.parquet", tmp_path / "x_history.parquet"


def _single_row(ts: str, value: float) -> pd.DataFrame:
    idx = pd.DatetimeIndex([pd.Timestamp(ts, tz="UTC")], name="snapshot_at")
    return pd.DataFrame({"value": [value]}, index=idx)


def _topn_snapshot(symbols_caps: list[tuple[str, float]]) -> pd.DataFrame:
    df = pd.DataFrame(
        [{"symbol": s, "market_cap": c} for s, c in symbols_caps]
    )
    df.index = pd.RangeIndex(start=1, stop=len(df) + 1, name="rank")
    return df


def test_writes_both_files_on_first_call(tmp_paths: tuple[Path, Path]) -> None:
    latest, history = tmp_paths
    df = _single_row("2020-01-01", 1.0)
    write_snapshot(df, latest, history)
    assert latest.exists()
    assert history.exists()
    assert len(pd.read_parquet(latest)) == 1
    assert len(pd.read_parquet(history)) == 1


def test_single_row_history_accumulates_distinct_timestamps(tmp_paths: tuple[Path, Path]) -> None:
    latest, history = tmp_paths
    write_snapshot(_single_row("2020-01-01", 1.0), latest, history)
    write_snapshot(_single_row("2020-01-02", 2.0), latest, history)
    write_snapshot(_single_row("2020-01-03", 3.0), latest, history)
    hist = pd.read_parquet(history)
    assert len(hist) == 3
    assert hist.index.is_monotonic_increasing
    # Latest carries only the most recent value
    last = pd.read_parquet(latest)
    assert len(last) == 1
    assert last.iloc[0]["value"] == 3.0


def test_single_row_history_is_idempotent_on_same_timestamp(tmp_paths: tuple[Path, Path]) -> None:
    latest, history = tmp_paths
    write_snapshot(_single_row("2020-01-01", 1.0), latest, history)
    write_snapshot(_single_row("2020-01-01", 1.5), latest, history)  # updated
    write_snapshot(_single_row("2020-01-01", 1.7), latest, history)  # updated again
    hist = pd.read_parquet(history)
    assert len(hist) == 1
    # Last write wins on dedup
    assert hist.iloc[0]["value"] == 1.7


def test_multi_row_snapshot_appends_with_snapshot_at_column(tmp_paths: tuple[Path, Path]) -> None:
    latest, history = tmp_paths
    snap1 = _topn_snapshot([("btc", 1_000), ("eth", 500)])
    write_snapshot(
        snap1, latest, history,
        snapshot_at=pd.Timestamp("2020-01-01", tz="UTC"),
        primary_key=["rank"],
    )
    snap2 = _topn_snapshot([("btc", 1_100), ("eth", 550)])
    write_snapshot(
        snap2, latest, history,
        snapshot_at=pd.Timestamp("2020-01-02", tz="UTC"),
        primary_key=["rank"],
    )
    hist = pd.read_parquet(history)
    assert len(hist) == 4  # 2 snapshots * 2 rows
    assert set(hist["snapshot_at"].unique()) == {
        pd.Timestamp("2020-01-01", tz="UTC"),
        pd.Timestamp("2020-01-02", tz="UTC"),
    }


def test_multi_row_snapshot_dedup_on_snapshot_at_and_primary_key(tmp_paths: tuple[Path, Path]) -> None:
    latest, history = tmp_paths
    ts = pd.Timestamp("2020-01-01", tz="UTC")
    snap1 = _topn_snapshot([("btc", 1_000), ("eth", 500)])
    write_snapshot(snap1, latest, history, snapshot_at=ts, primary_key=["rank"])
    # Same snapshot_at, updated market caps → should replace, not duplicate
    snap2 = _topn_snapshot([("btc", 1_111), ("eth", 555)])
    write_snapshot(snap2, latest, history, snapshot_at=ts, primary_key=["rank"])
    hist = pd.read_parquet(history)
    assert len(hist) == 2
    btc_row = hist[hist["symbol"] == "btc"].iloc[0]
    assert btc_row["market_cap"] == 1_111


def test_empty_frame_is_skipped(tmp_paths: tuple[Path, Path]) -> None:
    latest, history = tmp_paths
    empty = pd.DataFrame(
        columns=["value"], index=pd.DatetimeIndex([], name="snapshot_at", tz="UTC")
    )
    write_snapshot(empty, latest, history)
    assert not latest.exists()
    assert not history.exists()


def test_history_preserved_when_only_latest_disk_state_is_wrong(tmp_paths: tuple[Path, Path]) -> None:
    """Sanity: if a writer wipes latest by accident, the history is intact."""
    latest, history = tmp_paths
    write_snapshot(_single_row("2020-01-01", 1.0), latest, history)
    write_snapshot(_single_row("2020-01-02", 2.0), latest, history)
    latest.unlink()  # simulate accidental deletion
    assert history.exists()
    hist = pd.read_parquet(history)
    assert len(hist) == 2
