"""Multifactor design matrix assembly (Fase 4).

Joins the three feature families the project has built — technical (Fase 2,
``src.features.indicators``), macro (Fase 4, ``src.features.macro_features``) and
news/sentiment (Fase 3, ``src.features.news_features``) — into one model-ready
``(X, y)`` for a directional classifier, **without look-ahead**.

The non-negotiable rule (CLAUDE.md): the feature row at day ``t`` must contain
only information knowable at the close of ``t`` (or earlier), and it predicts the
return realised over ``t -> t+1``. We enforce this by:

1. building each feature family causally (already true upstream),
2. **lagging every feature by one day** in ``assemble_design_matrix`` so the row
   labelled ``t`` is the state as of the *previous* close, then
3. defining the target as ``sign(return[t])`` — i.e. tomorrow's direction
   relative to the lagged features.

So ``X[t]`` (yesterday's close state) predicts ``y[t]`` (today's up/down). No
feature on row ``t`` can contain ``return[t]``.
"""

from __future__ import annotations

from typing import cast

import pandas as pd

from src.features import indicators as ind


def technical_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Causal technical features from an OHLCV frame (Fase 2 indicators).

    A compact, non-redundant set: trend (SMA gap, MACD histogram), momentum
    (RSI), volatility (ATR %), and a short return. All are causal by
    construction (see ``src.features.indicators``). Indexed like ``ohlcv``.
    """
    close = cast("pd.Series", ohlcv["close"])
    feats = pd.DataFrame(index=ohlcv.index)
    sma_20 = ind.sma(close, 20)
    sma_50 = ind.sma(close, 50)
    feats["sma_gap"] = (sma_20 - sma_50) / sma_50
    macd = ind.macd(close)
    feats["macd_hist"] = macd["hist"]
    feats["rsi_14"] = ind.rsi(close, 14)
    feats["atr_pct"] = ind.atr(ohlcv, 14) / close
    feats["ret_1d"] = close.pct_change()
    return feats


def directional_target(close: pd.Series) -> pd.Series:
    """Binary next-period direction: 1 if the period return is > 0 else 0.

    Defined on the *realised* return at each day (no shift here). The look-ahead
    safety comes from lagging the features against this target in
    ``assemble_design_matrix``, not from shifting the target.
    """
    ret = cast("pd.Series", close.pct_change())
    return cast("pd.Series", ret.gt(0.0).astype("float64")).rename("target")


def assemble_design_matrix(
    ohlcv: pd.DataFrame,
    extra_features: pd.DataFrame | None = None,
    *,
    feature_lag: int = 1,
) -> tuple[pd.DataFrame, pd.Series]:
    """Build ``(X, y)`` for a directional classifier, anti-look-ahead.

    Parameters
    ----------
    ohlcv:
        OHLCV frame for the target asset (must have a ``close`` column).
    extra_features:
        Optional already-causal features (macro, news, ...) on a compatible
        index; reindexed to ``ohlcv`` and forward-filled (macro/news change less
        often than price). They are lagged together with the technical features.
    feature_lag:
        Days to lag *all* features behind the target (default 1). With lag 1, the
        row labelled ``t`` holds the state as of ``t-1``'s close and predicts the
        direction of day ``t``. Must be >= 1 (0 would leak same-day info).

    Returns
    -------
    ``(X, y)`` aligned on a common index, with rows containing any NaN dropped
    (indicator warm-up, missing macro before first release, etc.).
    """
    if feature_lag < 1:
        raise ValueError("feature_lag must be >= 1 (lag 0 leaks same-day info)")

    close = cast("pd.Series", ohlcv["close"])
    feats = technical_features(ohlcv)

    if extra_features is not None and not extra_features.empty:
        aligned = extra_features.reindex(feats.index).ffill()
        feats = feats.join(aligned)

    x = feats.shift(feature_lag)
    y = directional_target(close)

    data = x.join(y.rename("target"), how="inner").dropna()
    y_out = cast("pd.Series", data["target"])
    x_out = data.drop(columns=["target"])
    return x_out, y_out
