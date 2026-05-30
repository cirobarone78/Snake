"""Layer 1 sentiment: lexicon-based scoring (ADR-016, ADR-023).

The cheapest, most transparent rung of the AI ladder (ADR-016): a rule/lexicon
scorer (VADER) with no model weights, no GPU, no API cost. We start here and
only climb to FinBERT (Layer 2) / LLM (Layer 3) if a measured signal justifies
the added cost and dependency weight — per ADR-016 and CLAUDE.md.
"""

from __future__ import annotations

from src.ai.lexicon.sentiment import (
    align_sentiment_returns,
    daily_sentiment,
    lag_daily_features,
    score_news_frame,
    score_text,
)

__all__ = [
    "align_sentiment_returns",
    "daily_sentiment",
    "lag_daily_features",
    "score_news_frame",
    "score_text",
]
