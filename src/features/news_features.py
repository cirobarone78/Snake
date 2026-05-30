"""News-derived features + lead/lag analysis (Fase 3).

Turns the daily sentiment frame (``daily_sentiment``: ``mean_sentiment`` +
``news_count`` per UTC day, ADR-024) into model-ready features, and provides a
lead/lag correlation helper to test — honestly — whether news *leads* price.

Two design rules, both from CLAUDE.md:

- **Causal by construction**: every rolling feature at day ``t`` uses only days
  ``<= t`` (backward windows, warm-up positions are NaN, never back-filled).
  The anti-look-ahead lag between a feature day and the *return* it explains is
  applied separately at join time (ADR-024), so these functions stay pure
  feature transforms.
- **Lead/lag is symmetric and reported in full**: ``lead_lag_table`` computes
  ``corr(feature[t], target[t+k])`` for every ``k`` in a range — positive ``k``
  = feature *leads* target, negative ``k`` = feature *lags*. We never report a
  single cherry-picked lag.
"""

from __future__ import annotations

from typing import cast

import pandas as pd


def rolling_mean_sentiment(daily: pd.DataFrame, window: int = 7, min_periods: int = 1) -> pd.Series:
    """Causal rolling mean of daily ``mean_sentiment`` (a smoothed sentiment level).

    Smooths the noisy day-to-day polarity into a trend. Backward window, so the
    value at ``t`` uses only days ``<= t``.
    """
    sentiment = cast("pd.Series", daily["mean_sentiment"])
    rolled = cast("pd.Series", sentiment.rolling(window=window, min_periods=min_periods).mean())
    return rolled.rename("sentiment_roll")


def sentiment_change(daily: pd.DataFrame, periods: int = 1) -> pd.Series:
    """Day-over-``periods`` change in daily ``mean_sentiment`` (sentiment momentum).

    A shift in tone (improving/worsening) rather than its level — sometimes the
    derivative carries more signal than the value.
    """
    sentiment = cast("pd.Series", daily["mean_sentiment"])
    return cast("pd.Series", sentiment.diff(periods)).rename("sentiment_change")


def news_volume_zscore(daily: pd.DataFrame, window: int = 30, min_periods: int = 5) -> pd.Series:
    """Causal rolling z-score of ``news_count`` (relative news-volume spikes).

    News *volume* (attention), normalised to its recent baseline, is a candidate
    volatility predictor independent of polarity. Uses a backward window and a
    one-step shift of the rolling stats so day ``t``'s z-score is computed
    against days strictly before ``t`` (no same-day leakage into its own
    baseline). Periods with zero rolling std yield NaN (no spurious infinities).
    """
    count = cast("pd.Series", daily["news_count"]).astype("float64")
    roll = count.rolling(window=window, min_periods=min_periods)
    mean = cast("pd.Series", roll.mean()).shift(1)
    std = cast("pd.Series", roll.std(ddof=0)).shift(1)
    z = (count - mean) / std.where(std > 0)
    return cast("pd.Series", z).rename("news_volume_z")


def build_news_features(
    daily: pd.DataFrame,
    sentiment_window: int = 7,
    volume_window: int = 30,
) -> pd.DataFrame:
    """Assemble the causal news feature frame from a daily sentiment frame.

    Columns: ``mean_sentiment`` (raw daily level, passed through), plus the
    derived ``sentiment_roll``, ``sentiment_change``, ``news_volume_z``, and the
    raw ``news_count``. Indexed by the same UTC ``date`` grid. An empty input
    yields a correctly-typed empty frame.
    """
    cols = [
        "mean_sentiment",
        "sentiment_roll",
        "sentiment_change",
        "news_count",
        "news_volume_z",
    ]
    if daily.empty:
        return pd.DataFrame(
            {c: pd.Series(dtype="float64") for c in cols},
            index=pd.DatetimeIndex([], name="date", tz="UTC"),
        )
    out = pd.DataFrame(index=daily.index)
    out["mean_sentiment"] = daily["mean_sentiment"]
    out["sentiment_roll"] = rolling_mean_sentiment(daily, window=sentiment_window)
    out["sentiment_change"] = sentiment_change(daily)
    out["news_count"] = daily["news_count"].astype("float64")
    out["news_volume_z"] = news_volume_zscore(daily, window=volume_window)
    out.index.name = "date"
    return out


def lead_lag_table(
    feature: pd.Series,
    target: pd.Series,
    lags: range | list[int],
) -> pd.DataFrame:
    """Correlation of ``feature[t]`` vs ``target[t + k]`` for each lag ``k``.

    Positive ``k`` means the feature *leads* the target by ``k`` days (the
    interesting case for prediction); negative ``k`` means it lags. Both series
    are aligned on their shared index. Returns a frame indexed by ``lag`` with
    columns ``corr`` (Pearson) and ``n`` (overlapping observations used) — ``n``
    is reported precisely because on a short history a high ``corr`` on few
    points is not a signal.

    Pure/causal note: this is a *descriptive* diagnostic over the whole sample,
    not a backtest. It does not, by itself, avoid look-ahead — use it to decide
    which lag to test properly, then build the lagged feature with ADR-024.
    """
    feat = feature.dropna()
    tgt = target.dropna()
    rows: list[dict[str, float]] = []
    for k in lags:
        shifted = tgt.shift(-k)  # bring target[t+k] back to label t
        joined = pd.concat([feat, shifted], axis=1, join="inner").dropna()
        n = len(joined)
        corr = float(joined.iloc[:, 0].corr(joined.iloc[:, 1])) if n >= 2 else float("nan")
        rows.append({"lag": float(k), "corr": corr, "n": float(n)})
    table = pd.DataFrame(rows).set_index("lag")
    table["n"] = table["n"].astype("int64")
    return table
