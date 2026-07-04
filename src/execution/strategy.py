"""Reference strategy for the live-shadow scenarios (Fase 6).

The paper portfolios run the ONE strategy this project's research actually
supports: the **defensive momentum** baseline of Fase 2 — long an asset when
its trailing momentum is positive, flat otherwise, equal weight across the
"on" assets. It is not a return predictor (directional accuracy ~50%, nb 04);
its measured value is staying out of bear regimes. That is exactly the claim
the live-shadow run exists to validate forward, out of sample by construction.

Honesty notes baked into the choice:
- **All Tier 1 assets, LINK included.** Notebook 05 showed the filter hurts
  LINK historically, but excluding it *after* seeing that result would be
  post-hoc cherry-picking (Q25 is still open). The live run tests the strategy
  as-is; if LINK keeps hurting, the forward data will say so.
- **Causal by reuse**: signals come from ``momentum_forecast`` (shift(1)
  inside), computed on closes up to the decision bar. Orders then fill on the
  NEXT bar's open (broker) — two layers of no-look-ahead.
"""

from __future__ import annotations

from typing import cast

import pandas as pd

from src.models.baseline import momentum_forecast, returns_from_prices

DEFAULT_LOOKBACK = 30


def momentum_target_weights(
    closes: dict[str, pd.Series],
    lookback: int = DEFAULT_LOOKBACK,
) -> dict[str, float]:
    """Equal-weight targets over assets with positive trailing momentum.

    ``closes`` maps symbol -> close Series up to the decision bar (inclusive).
    Returns symbol -> target fraction of equity; assets with non-positive or
    undefined momentum get 0. Weights sum to <= 1 (all zero -> stay in cash:
    the defensive posture IS the strategy).
    """
    on: list[str] = []
    for symbol, series in closes.items():
        rets = returns_from_prices(series)
        if len(rets) < lookback + 1:
            continue  # not enough history: no position, never a guess
        forecast = momentum_forecast(rets, lookback=lookback)
        last = cast("float", forecast.iloc[-1])
        if pd.notna(last) and last > 0:
            on.append(symbol)
    if not on:
        return {symbol: 0.0 for symbol in closes}
    w = 1.0 / len(on)
    return {symbol: (w if symbol in on else 0.0) for symbol in closes}
