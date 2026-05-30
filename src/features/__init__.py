"""Feature engineering — technical indicators (Fase 2).

Classic technical indicators computed as pure functions over OHLCV frames.
These are the first feature inputs for the baseline models (ROADMAP Fase 2)
and the educational L2 material on indicators (ADR-015).

No-look-ahead by construction: every indicator value at time ``t`` uses only
observations up to and including ``t`` (rolling/ewm windows look backward).
The leading positions where a window is not yet full are ``NaN`` — callers
must drop or mask them before feeding a model, never back-fill.

Asset-class-agnostic (ADR-014): nothing here assumes a calendar or a
crypto-specific scale; windows are expressed in observations.
"""

from __future__ import annotations

from src.features.indicators import (
    atr,
    bollinger_bands,
    ema,
    macd,
    obv,
    rsi,
    sma,
)

__all__ = [
    "atr",
    "bollinger_bands",
    "ema",
    "macd",
    "obv",
    "rsi",
    "sma",
]
