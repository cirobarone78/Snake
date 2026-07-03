"""Offline tests for news coverage volume as an event signal (D2)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.features.move_attribution import AbnormalMove
from src.features.news_volume import (
    annotate_moves_with_coverage,
    daily_news_volume,
    detect_volume_spikes,
    volume_zscore,
)


def _news(day_counts: dict[str, int], source: str = "googlenews_btc") -> pd.DataFrame:
    """A news frame with ``day_counts[date] = n`` headlines on that day."""
    stamps: list[pd.Timestamp] = []
    for day, n in day_counts.items():
        for i in range(n):
            stamps.append(pd.Timestamp(f"{day} {i % 24:02d}:00", tz="UTC"))
    idx = pd.DatetimeIndex(stamps, name="published")
    return pd.DataFrame(
        {
            "source": [source] * len(idx),
            "title": ["t"] * len(idx),
            "url": ["u"] * len(idx),
            "sentiment": [0.0] * len(idx),
        },
        index=idx,
    )


# --- daily_news_volume ---


def test_daily_volume_counts_and_fills_gaps() -> None:
    news = _news({"2026-01-01": 3, "2026-01-04": 2})  # gap on 02 and 03
    counts = daily_news_volume(news, "googlenews_btc")
    assert len(counts) == 4  # calendar-complete span
    assert counts.loc[pd.Timestamp("2026-01-01", tz="UTC")] == 3
    assert counts.loc[pd.Timestamp("2026-01-02", tz="UTC")] == 0  # gap = zero, not missing
    assert counts.loc[pd.Timestamp("2026-01-04", tz="UTC")] == 2


def test_daily_volume_filters_by_source() -> None:
    news = pd.concat([_news({"2026-01-01": 3}), _news({"2026-01-01": 5}, source="other")])
    counts = daily_news_volume(news, "googlenews_btc")
    assert counts.loc[pd.Timestamp("2026-01-01", tz="UTC")] == 3


def test_daily_volume_empty_when_no_match() -> None:
    assert daily_news_volume(_news({"2026-01-01": 3}), "nope").empty
    assert daily_news_volume(pd.DataFrame(), "googlenews_btc").empty


# --- spikes ---


def _steady_then_burst(days: int = 40, burst_day: int = 35, base: int = 4, burst: int = 30):
    start = pd.Timestamp("2026-01-01", tz="UTC")
    counts = {str((start + pd.Timedelta(days=i)).date()): base for i in range(days)}
    counts[str((start + pd.Timedelta(days=burst_day)).date())] = burst
    return _news(counts)


def test_spike_detected_on_burst_day() -> None:
    counts = daily_news_volume(_steady_then_burst(), "googlenews_btc")
    spikes = detect_volume_spikes(counts, window=20, z_threshold=2.5, min_count=5)
    burst_ts = pd.Timestamp("2026-02-05", tz="UTC")
    assert burst_ts in spikes.index
    assert spikes.loc[burst_ts, "count"] == 30
    # steady days are not spikes
    assert len(spikes) == 1


def test_min_count_floor_blocks_thin_feed_spikes() -> None:
    # baseline ~0 headlines, one day with 3: huge z but too thin to matter
    news = _news({"2026-01-01": 0, "2026-02-05": 3} | {
        str(pd.Timestamp("2026-01-01") + pd.Timedelta(days=i)): 0 for i in range(1, 35)
    })
    counts = daily_news_volume(news, "googlenews_btc")
    spikes = detect_volume_spikes(counts, window=20, z_threshold=2.5, min_count=5)
    assert spikes.empty


def test_zscore_baseline_is_causal() -> None:
    # the burst day must not inflate its own baseline (shift(1))
    counts = daily_news_volume(_steady_then_burst(), "googlenews_btc")
    z = volume_zscore(counts, window=20)
    burst_ts = pd.Timestamp("2026-02-05", tz="UTC")
    day_after = burst_ts + pd.Timedelta(days=1)
    assert z.loc[burst_ts] > 2.5
    # the day after returns to base rate: with the burst now IN the baseline,
    # z must be far below the spike threshold (no echo-flagging)
    assert z.loc[day_after] < 2.5


def test_min_count_rejects_negative() -> None:
    counts = daily_news_volume(_steady_then_burst(), "googlenews_btc")
    with pytest.raises(ValueError, match="min_count"):
        detect_volume_spikes(counts, min_count=-1)


# --- move annotation ---


def _move(day: str) -> AbnormalMove:
    return AbnormalMove(
        date=pd.Timestamp(day, tz="UTC"),
        return_pct=-8.0,
        zscore=-3.0,
        market_return_pct=None,
        classification="unknown",
    )


def test_annotate_moves_marks_spike_day() -> None:
    counts = daily_news_volume(_steady_then_burst(), "googlenews_btc")
    moves = annotate_moves_with_coverage([_move("2026-02-05"), _move("2026-01-20")], counts)
    spike_move, calm_move = moves[0], moves[1]
    assert spike_move.coverage is not None and spike_move.coverage["spike"] is True
    assert spike_move.coverage["count"] == 30
    assert calm_move.coverage is not None and calm_move.coverage["spike"] is False


def test_annotate_moves_off_calendar_day_is_zero() -> None:
    counts = daily_news_volume(_news({"2026-01-01": 3}), "googlenews_btc")
    moves = annotate_moves_with_coverage([_move("2026-03-01")], counts)
    assert moves[0].coverage == {"count": 0, "zscore": None, "spike": False}


def test_annotate_empty_moves_noop() -> None:
    counts = daily_news_volume(_news({"2026-01-01": 3}), "googlenews_btc")
    assert annotate_moves_with_coverage([], counts) == []
