"""Layer 1 lexicon sentiment scoring + temporal alignment (ADR-023, ADR-024).

**Scoring (Q9 → ADR-023)**: VADER (`vaderSentiment`) gives each text a compound
polarity in ``[-1, +1]``. It's a lexicon+rules model — deterministic, fast, no
weights/GPU/API. General-domain (social/news tuned), so it's a *baseline*: we
escalate to a finance-tuned model only if a measured signal justifies it.

**Alignment (Q12 → ADR-024)**: news carry a *publication* timestamp (UTC). To
study whether sentiment predicts returns without look-ahead, we (1) aggregate
to a daily mean per UTC calendar day, then (2) lag the daily feature by N days
(default 1) before joining it to returns. So the feature used to explain the
return realised over day ``D`` is built only from news published on/before day
``D − N`` — the news is fully public before the return window opens.

All functions are pure over pandas objects, so they unit-test offline. The
scorer is the only stateful piece; a module-level analyzer is reused to avoid
reloading the lexicon per call.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


@lru_cache(maxsize=1)
def _analyzer() -> SentimentIntensityAnalyzer:
    """Lazily build and cache the VADER analyzer (loads its lexicon once)."""
    return SentimentIntensityAnalyzer()


def score_text(text: str) -> float:
    """Compound sentiment polarity of ``text`` in ``[-1.0, +1.0]``.

    Empty/whitespace text scores a neutral ``0.0``.
    """
    if not text or not text.strip():
        return 0.0
    return float(_analyzer().polarity_scores(text)["compound"])


def score_news_frame(frame: pd.DataFrame, text_col: str = "title") -> pd.DataFrame:
    """Return a copy of ``frame`` with a ``sentiment`` column scored on ``text_col``.

    We score the headline (``title``) by default: feed summaries often carry HTML
    and source boilerplate that add noise to a lexicon scorer. An empty frame
    gets the column added with the right dtype so downstream code is uniform.
    """
    out = frame.copy()
    if out.empty:
        out["sentiment"] = pd.Series(dtype="float64")
        return out
    out["sentiment"] = out[text_col].fillna("").map(score_text).astype("float64")
    return out


def daily_sentiment(scored: pd.DataFrame) -> pd.DataFrame:
    """Aggregate a scored, ``published``-indexed news frame to one row per UTC day.

    Returns a frame indexed by a UTC ``DatetimeIndex`` named ``date`` (midnight),
    with columns ``mean_sentiment`` (daily average polarity) and ``news_count``
    (number of items that day — itself a candidate "news volume" feature).
    Empty input yields a correctly-typed empty frame.
    """
    if scored.empty:
        return pd.DataFrame(
            {
                "mean_sentiment": pd.Series(dtype="float64"),
                "news_count": pd.Series(dtype="int64"),
            },
            index=pd.DatetimeIndex([], name="date", tz="UTC"),
        )
    day = scored.index.floor("D")
    grouped = scored["sentiment"].groupby(day)
    out = pd.DataFrame(
        {
            "mean_sentiment": grouped.mean(),
            "news_count": grouped.size().astype("int64"),
        }
    )
    out.index.name = "date"
    return out.sort_index()


def lag_daily_features(daily: pd.DataFrame, periods: int = 1) -> pd.DataFrame:
    """Shift daily features forward by ``periods`` calendar days (anti-look-ahead).

    Uses a label shift on the date index (``shift(freq="D")``), so a feature
    derived from day ``D`` becomes labelled ``D + periods``. Gaps in the news
    calendar are preserved (no spurious fill). This is the Q12/ADR-024 safety
    lag: the lagged value is safe to join to the return realised on its new
    label without leaking same-day information.
    """
    if daily.empty:
        return daily.copy()
    return daily.shift(periods, freq="D")


def align_sentiment_returns(
    daily: pd.DataFrame,
    returns: pd.Series,
    lag: int = 1,
) -> pd.DataFrame:
    """Join lagged daily sentiment to a return series for lead/lag analysis.

    ``returns`` is a daily simple/log return Series indexed by date. The daily
    sentiment features are lagged by ``lag`` days (ADR-024) and inner-joined to
    the returns, so each row pairs a return with sentiment that was fully public
    before that return's window. Returns a frame with
    ``mean_sentiment, news_count, return`` (rows with no overlap dropped).
    """
    lagged = lag_daily_features(daily, periods=lag)
    ret = returns.rename("return")
    # normalise the return index to UTC midnight to match the daily sentiment grid
    ret_idx = pd.DatetimeIndex(ret.index)
    if ret_idx.tz is None:
        ret_idx = ret_idx.tz_localize("UTC")
    ret = pd.Series(ret.to_numpy(), index=ret_idx.floor("D"), name="return")
    joined = lagged.join(ret, how="inner")
    return joined.dropna(subset=["return", "mean_sentiment"])
