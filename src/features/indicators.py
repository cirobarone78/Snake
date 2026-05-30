"""Classic technical indicators as pure functions (Fase 2).

Each function takes price/volume Series (or an OHLCV DataFrame) and returns a
new Series/DataFrame aligned to the input index. See the package docstring for
the no-look-ahead and asset-class-agnostic contracts.

Conventions
-----------
- Inputs are pandas Series with a chronological index (typically the
  ``close`` column, or the full OHLCV frame for range-based indicators).
- Leading positions where the lookback window is not yet full are ``NaN``.
- Smoothing uses ``ewm(..., adjust=False)`` for the recursive (Wilder /
  standard EMA) definitions, which is the convention charting tools use.
"""

from __future__ import annotations

from typing import cast

import pandas as pd


def _as_series(x: pd.Series, name: str) -> pd.Series:
    if not isinstance(x, pd.Series):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"{name} must be a pandas Series")
    return x


def sma(prices: pd.Series, window: int) -> pd.Series:
    """Simple moving average over ``window`` observations."""
    if window <= 0:
        raise ValueError("window must be positive")
    prices = _as_series(prices, "prices")
    return cast("pd.Series", prices.rolling(window).mean()).rename(f"sma_{window}")


def ema(prices: pd.Series, window: int) -> pd.Series:
    """Exponential moving average (span=window, recursive ``adjust=False``)."""
    if window <= 0:
        raise ValueError("window must be positive")
    prices = _as_series(prices, "prices")
    return cast("pd.Series", prices.ewm(span=window, adjust=False).mean()).rename(
        f"ema_{window}"
    )


def macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Moving Average Convergence Divergence.

    Returns a DataFrame with columns ``macd`` (fast EMA - slow EMA),
    ``signal`` (EMA of the macd line) and ``hist`` (macd - signal).
    """
    if not 0 < fast < slow:
        raise ValueError("require 0 < fast < slow")
    if signal <= 0:
        raise ValueError("signal must be positive")
    prices = _as_series(prices, "prices")
    macd_line = ema(prices, fast) - ema(prices, slow)
    signal_line = cast("pd.Series", macd_line.ewm(span=signal, adjust=False).mean())
    hist = macd_line - signal_line
    return pd.DataFrame(
        {"macd": macd_line, "signal": signal_line, "hist": hist},
        index=prices.index,
    )


def rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing).

    Bounded in [0, 100]. A flat or rising series with no losses tends to 100;
    a monotonically falling one tends to 0. Uses Wilder's exponential average
    of gains and losses (``alpha = 1/window``).
    """
    if window <= 0:
        raise ValueError("window must be positive")
    prices = _as_series(prices, "prices")
    delta = prices.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False).mean()
    rs = avg_gain / avg_loss
    result = cast("pd.Series", 100.0 - 100.0 / (1.0 + rs))
    # avg_loss == 0 → rs is inf → formula yields 100; make it explicit and
    # also handle the all-flat case (0/0) where both averages are zero.
    result = result.where(avg_loss != 0.0, 100.0)
    result = result.where(~((avg_gain == 0.0) & (avg_loss == 0.0)), 50.0)
    return cast("pd.Series", result).rename(f"rsi_{window}")


def bollinger_bands(
    prices: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """Bollinger Bands.

    Returns a DataFrame with ``mid`` (SMA), ``upper`` and ``lower`` bands at
    ``num_std`` rolling standard deviations (sample std, ddof=0 — the
    population std is the charting convention for Bollinger Bands).
    """
    if window <= 0:
        raise ValueError("window must be positive")
    if num_std < 0:
        raise ValueError("num_std must be non-negative")
    prices = _as_series(prices, "prices")
    mid = cast("pd.Series", prices.rolling(window).mean())
    sd = cast("pd.Series", prices.rolling(window).std(ddof=0))
    return pd.DataFrame(
        {"mid": mid, "upper": mid + num_std * sd, "lower": mid - num_std * sd},
        index=prices.index,
    )


def _require_columns(ohlc: pd.DataFrame, cols: tuple[str, ...]) -> None:
    missing = [c for c in cols if c not in ohlc.columns]
    if missing:
        raise ValueError(f"frame missing columns {missing}; need {list(cols)}")


def atr(ohlc: pd.DataFrame, window: int = 14) -> pd.Series:
    """Average True Range (Wilder), a volatility measure in price units.

    True range is ``max(high-low, |high-prev_close|, |low-prev_close|)``;
    ATR is Wilder's exponential average of it (``alpha = 1/window``).
    """
    if window <= 0:
        raise ValueError("window must be positive")
    _require_columns(ohlc, ("high", "low", "close"))
    high = ohlc["high"]
    low = ohlc["low"]
    prev_close = ohlc["close"].shift(1)
    true_range = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return cast(
        "pd.Series", true_range.ewm(alpha=1.0 / window, adjust=False).mean()
    ).rename(f"atr_{window}")


def obv(ohlc: pd.DataFrame) -> pd.Series:
    """On-Balance Volume.

    Cumulative volume signed by the direction of the close-to-close change:
    add volume on up days, subtract on down days, ignore flat days. The first
    observation seeds the running total at 0.
    """
    _require_columns(ohlc, ("close", "volume"))
    direction = ohlc["close"].diff()
    sign = direction.gt(0).astype(float) - direction.lt(0).astype(float)
    signed_volume = sign * ohlc["volume"]
    # The first row has no prior close → no flow; start the cumulative at 0.
    signed_volume = signed_volume.fillna(0.0)
    return cast("pd.Series", signed_volume.cumsum()).rename("obv")
