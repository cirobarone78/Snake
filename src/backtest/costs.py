"""Transaction cost model: fees + slippage (Fase 2, ADR-013).

Modelling costs realistically is not optional decoration — ADR-004 makes it
a Fase 2 requirement, because a backtest that ignores fees and slippage
flatters every strategy and is worthless as a go/no-go signal. The same
model feeds the paper broker in Fase 6.

Two components, both asset-class-agnostic (ADR-014 — rates and coefficients
are configuration, never hardcoded crypto assumptions):

1. **Fee**: a per-broker maker/taker rate on notional. Reference schedules
   for Binance and Kraken spot (ADR-012) are provided as constants; re-verify
   them before any real go-live, fees drift over time.

2. **Slippage** (ADR-013): ``rate = max(half_spread, base_cost) * size_adj``
   with ``size_adj = 1 + impact_coeff * notional / avg_daily_volume``. The
   floor (``base_cost_bps``) keeps slippage non-zero on illiquid assets with
   no spread data; market impact is off by default (``impact_coeff = 0``)
   because for orders up to ~100k EUR on Tier 1 assets it is negligible.

We have no order-book bid/ask in our data (Q23), so ``estimate_half_spread_bps``
derives a crude spread proxy from the OHLC range. It is a stand-in floor, not
a measured spread — see its docstring.

All amounts are in the same currency unit as ``notional``; rates are
fractions (0.001 = 10 bps = 0.10%). Basis points: 1 bp = 1e-4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import pandas as pd

BPS = 1e-4


@dataclass(frozen=True)
class FeeModel:
    """Maker/taker fee rates applied to the absolute notional traded."""

    maker_rate: float
    taker_rate: float

    def __post_init__(self) -> None:
        if self.maker_rate < 0 or self.taker_rate < 0:
            raise ValueError("fee rates must be non-negative")

    def fee(self, notional: float, *, maker: bool = False) -> float:
        """Currency fee for trading ``notional`` (sign-agnostic)."""
        rate = self.maker_rate if maker else self.taker_rate
        return abs(notional) * rate


# Reference spot fee schedules (ADR-012). Re-verify before any go-live.
BINANCE_SPOT = FeeModel(maker_rate=0.0010, taker_rate=0.0010)  # tier 0
KRAKEN_SPOT = FeeModel(maker_rate=0.0016, taker_rate=0.0026)  # "Starter" tier


@dataclass(frozen=True)
class SlippageModel:
    """Slippage as a rate on notional (ADR-013).

    ``base_cost_bps`` is the floor in basis points; ``impact_coeff`` scales a
    linear market-impact term by ``notional / avg_daily_volume`` (off by
    default). ``half_spread_bps`` is supplied per-trade (it is asset- and
    time-specific) and competes with the floor via ``max``.
    """

    base_cost_bps: float = 2.0
    impact_coeff: float = 0.0

    def __post_init__(self) -> None:
        if self.base_cost_bps < 0:
            raise ValueError("base_cost_bps must be non-negative")
        if self.impact_coeff < 0:
            raise ValueError("impact_coeff must be non-negative")

    def rate(
        self,
        notional: float,
        *,
        half_spread_bps: float = 0.0,
        avg_daily_volume: float | None = None,
    ) -> float:
        """Slippage rate (fraction of notional) for one trade."""
        if half_spread_bps < 0:
            raise ValueError("half_spread_bps must be non-negative")
        per_unit = max(half_spread_bps, self.base_cost_bps) * BPS
        size_adj = 1.0
        if self.impact_coeff > 0 and avg_daily_volume:
            if avg_daily_volume <= 0:
                raise ValueError("avg_daily_volume must be positive")
            size_adj = 1.0 + self.impact_coeff * (abs(notional) / avg_daily_volume)
        return per_unit * size_adj

    def cost(
        self,
        notional: float,
        *,
        half_spread_bps: float = 0.0,
        avg_daily_volume: float | None = None,
    ) -> float:
        """Currency slippage cost for trading ``notional``."""
        return abs(notional) * self.rate(
            notional,
            half_spread_bps=half_spread_bps,
            avg_daily_volume=avg_daily_volume,
        )


@dataclass(frozen=True)
class TransactionCostModel:
    """Fee + slippage for a single trade. The unit of round-trip cost (L1.04)."""

    fee: FeeModel
    slippage: SlippageModel = field(default_factory=SlippageModel)

    def cost(
        self,
        notional: float,
        *,
        maker: bool = False,
        half_spread_bps: float = 0.0,
        avg_daily_volume: float | None = None,
    ) -> float:
        """Total currency cost of executing ``notional``."""
        return self.fee.fee(notional, maker=maker) + self.slippage.cost(
            notional,
            half_spread_bps=half_spread_bps,
            avg_daily_volume=avg_daily_volume,
        )


def estimate_half_spread_bps(
    ohlc: pd.DataFrame,
    window: int = 30,
    quantile: float = 0.10,
) -> pd.Series:
    """Rough rolling half-spread proxy in basis points from OHLC range.

    We have no bid/ask in our data (ADR-013, Q23). Approximate the spread
    from the intraday high-low range: on the *calmest* days the range is
    dominated by the spread itself, so the lower ``quantile`` of the rolling
    range distribution is a conservative spread proxy. The result is half of
    that, in bps.

    This is deliberately crude — a floor stand-in, not a measured spread.
    Treat it as a lower bound and revisit if/when real spread data arrives
    (Kaiko, ADR-008 Tier 4).
    """
    needed = ("high", "low", "close")
    missing = [c for c in needed if c not in ohlc.columns]
    if missing:
        raise ValueError(f"estimate_half_spread_bps needs {list(needed)}; missing {missing}")
    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be in [0, 1]")
    if window <= 0:
        raise ValueError("window must be positive")

    range_frac = (ohlc["high"] - ohlc["low"]) / ohlc["close"]
    rolling_q = range_frac.rolling(window, min_periods=1).quantile(quantile)
    half_spread = rolling_q / 2.0 / BPS
    # Rolling.quantile is untyped in pandas (no stubs); the value is a Series.
    return cast("pd.Series", pd.Series(half_spread, index=ohlc.index))
