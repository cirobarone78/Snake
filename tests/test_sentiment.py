"""Offline tests for Layer 1 lexicon sentiment + alignment (ADR-023/024)."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from src.ai.lexicon.sentiment import (
    align_sentiment_returns,
    daily_sentiment,
    lag_daily_features,
    score_news_frame,
    score_text,
)
from src.ingestion.news.base import NewsItem, news_to_frame


def _news(title: str, day: int, hour: int = 12) -> NewsItem:
    return NewsItem(
        item_id=f"{title}-{day}-{hour}",
        source="test",
        title=title,
        url="https://example.com",
        published=datetime(2025, 1, day, hour, tzinfo=UTC),
    )


# --- score_text ---


def test_score_text_sign_and_bounds() -> None:
    pos = score_text("Bitcoin surges to a record high, investors thrilled")
    neg = score_text("Bitcoin crashes in a brutal market panic, huge losses")
    assert pos > 0 > neg
    assert -1.0 <= pos <= 1.0
    assert -1.0 <= neg <= 1.0


def test_score_text_empty_is_neutral() -> None:
    assert score_text("") == 0.0
    assert score_text("   ") == 0.0


# --- score_news_frame ---


def test_score_news_frame_adds_column() -> None:
    frame = news_to_frame([_news("Great rally lifts crypto", 1)])
    scored = score_news_frame(frame)
    assert "sentiment" in scored.columns
    assert scored["sentiment"].iloc[0] > 0
    # original frame untouched (copy semantics)
    assert "sentiment" not in frame.columns


def test_score_news_frame_empty() -> None:
    scored = score_news_frame(news_to_frame([]))
    assert scored.empty
    assert "sentiment" in scored.columns
    assert scored["sentiment"].dtype == "float64"


# --- daily_sentiment ---


def test_daily_sentiment_groups_and_counts() -> None:
    frame = news_to_frame(
        [
            _news("Bullish surge, optimism everywhere", 1, hour=8),
            _news("Another positive breakout, gains soar", 1, hour=20),
            _news("Market crashes, fear and panic", 2, hour=10),
        ]
    )
    daily = daily_sentiment(score_news_frame(frame))
    assert list(daily.columns) == ["mean_sentiment", "news_count"]
    assert daily.index.name == "date"
    assert len(daily) == 2
    assert daily["news_count"].tolist() == [2, 1]
    # day 1 (two positive) > day 2 (one negative)
    assert daily["mean_sentiment"].iloc[0] > daily["mean_sentiment"].iloc[1]


def test_daily_sentiment_empty() -> None:
    daily = daily_sentiment(score_news_frame(news_to_frame([])))
    assert daily.empty
    assert list(daily.columns) == ["mean_sentiment", "news_count"]


# --- lag (anti-look-ahead) ---


def test_lag_shifts_index_forward() -> None:
    daily = daily_sentiment(
        score_news_frame(news_to_frame([_news("good news rally", 1), _news("bad crash", 2)]))
    )
    lagged = lag_daily_features(daily, periods=1)
    # the day-1 value now sits on day 2
    assert pd.Timestamp("2025-01-02", tz="UTC") in lagged.index
    assert pd.Timestamp("2025-01-01", tz="UTC") not in lagged.index


# --- alignment to returns ---


def test_align_no_lookahead() -> None:
    # sentiment on day 1 must align to the RETURN on day 2 (lag=1)
    frame = news_to_frame([_news("massive positive breakout, euphoria", 1)])
    daily = daily_sentiment(score_news_frame(frame))
    returns = pd.Series(
        [0.05, -0.02],
        index=pd.DatetimeIndex(["2025-01-01", "2025-01-02"], tz="UTC"),
    )
    aligned = align_sentiment_returns(daily, returns, lag=1)
    assert len(aligned) == 1
    assert aligned.index[0] == pd.Timestamp("2025-01-02", tz="UTC")
    assert aligned["return"].iloc[0] == -0.02
    assert aligned["mean_sentiment"].iloc[0] > 0
