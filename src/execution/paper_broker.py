"""PaperBroker: simulated execution with real-world frictions (Fase 6).

The validation gate before any live-trading consideration (ADR-010). The
non-negotiables are structural here, not conventions:

- **No look-ahead (ADR-010 #1)**: ``submit()`` only records the order; nothing
  fills until ``process_bar()`` is called with a bar *strictly after* the
  order's creation time. Market orders fill at the next bar's **open** (the
  first price actually available to someone who decided at the previous
  close), never at the price that generated the signal.
- **Costs (ADR-012/013)**: every fill pays fee + slippage through the same
  ``TransactionCostModel`` used by the Fase 2 backtests — one cost model,
  everywhere. Slippage worsens the fill price (paid on price, not just cash),
  so it compounds exactly like the real world does.
- **Long-only spot**: sells are capped at the held quantity; buys at available
  cash. Violations reject the order (auditable) rather than raising mid-run.

Limit semantics (standard next-bar evaluation): a BUY limit fills if the bar
trades at/below the limit — at the open when the bar opens below it (you get
the better price), otherwise at the limit. Symmetric for SELL.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd

from src.backtest.costs import BINANCE_SPOT, SlippageModel, TransactionCostModel
from src.execution.orders import Order, OrderStatus, OrderType, Side
from src.execution.portfolio import Portfolio


@dataclass(frozen=True)
class Bar:
    """One OHLC bar for one symbol, tz-aware timestamp."""

    symbol: str
    ts: pd.Timestamp
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if not (self.low <= self.open <= self.high and self.low <= self.close <= self.high):
            raise ValueError("inconsistent OHLC bar")


class Broker(ABC):
    """What any broker (paper today, live never-say-never) must expose."""

    @abstractmethod
    def submit(self, order: Order) -> Order:
        """Accept an order for future execution; returns it (possibly rejected)."""

    @abstractmethod
    def process_bar(self, bar: Bar) -> list[Order]:
        """Advance time by one bar; returns the orders filled on this bar."""


def default_cost_model() -> TransactionCostModel:
    """Binance spot fees + 2 bps slippage floor — the ADR-012/013 default."""
    return TransactionCostModel(fee=BINANCE_SPOT, slippage=SlippageModel(base_cost_bps=2.0))


class PaperBroker(Broker):
    """Simulated spot broker for one scenario's portfolio."""

    def __init__(
        self,
        portfolio: Portfolio,
        cost_model: TransactionCostModel | None = None,
    ) -> None:
        self.portfolio = portfolio
        self.cost_model = cost_model if cost_model is not None else default_cost_model()
        self.pending: list[Order] = []
        self.history: list[Order] = []  # every submitted order, terminal or not

    # -- order intake ------------------------------------------------------

    def submit(self, order: Order) -> Order:
        """Validate intent (long-only) and queue for the next bar."""
        self.history.append(order)
        if order.side is Side.SELL:
            pos = self.portfolio.positions.get(order.symbol)
            held = pos.qty if pos else 0.0
            if order.qty > held + 1e-9:
                order.status = OrderStatus.REJECTED
                order.reject_reason = f"sell {order.qty} > held {held} (long-only)"
                return order
        self.pending.append(order)
        return order

    def cancel_pending(self, symbol: str | None = None) -> int:
        """Cancel pending orders (optionally only one symbol); returns count."""
        cancelled = 0
        for o in self.pending:
            if symbol is None or o.symbol == symbol:
                o.status = OrderStatus.CANCELLED
                cancelled += 1
        self.pending = [o for o in self.pending if o.status is OrderStatus.PENDING]
        return cancelled

    # -- time advance ------------------------------------------------------

    def process_bar(self, bar: Bar) -> list[Order]:
        """Fill whatever this bar allows. Orders created at/after ``bar.ts``
        are NOT touched — the no-look-ahead rule in one line."""
        filled: list[Order] = []
        still_pending: list[Order] = []
        for order in self.pending:
            if order.symbol != bar.symbol or order.created_at >= bar.ts:
                still_pending.append(order)
                continue
            price = self._fill_price(order, bar)
            if price is None:
                still_pending.append(order)  # limit not reached; stays working
                continue
            if self._execute(order, price, bar.ts):
                filled.append(order)
            # rejected orders (e.g. cash shortfall at fill time) drop out here
        self.pending = still_pending
        return filled

    # -- internals ---------------------------------------------------------

    def _fill_price(self, order: Order, bar: Bar) -> float | None:
        """Raw fill price before slippage, or None if the order doesn't trigger."""
        if order.order_type is OrderType.MARKET:
            return bar.open
        limit = order.limit_price
        assert limit is not None  # enforced at construction
        if order.side is Side.BUY:
            if bar.open <= limit:
                return bar.open
            if bar.low <= limit:
                return limit
            return None
        if bar.open >= limit:
            return bar.open
        if bar.high >= limit:
            return limit
        return None

    def _execute(self, order: Order, raw_price: float, ts: pd.Timestamp) -> bool:
        """Apply slippage + fees and settle against the portfolio."""
        slip_rate = self.cost_model.slippage.rate(order.qty * raw_price)
        # slippage worsens the price in the direction of the trade
        price = raw_price * (1 + slip_rate) if order.side is Side.BUY else raw_price * (1 - slip_rate)
        notional = order.qty * price
        fee = self.cost_model.fee.fee(notional)
        try:
            if order.side is Side.BUY:
                self.portfolio.apply_buy(order.symbol, order.qty, price, fee)
            else:
                self.portfolio.apply_sell(order.symbol, order.qty, price, fee)
        except ValueError as exc:
            order.status = OrderStatus.REJECTED
            order.reject_reason = str(exc)
            return False
        order.status = OrderStatus.FILLED
        order.filled_at = ts
        order.fill_price = price
        order.fee_paid = fee
        return True

    # -- sizing helper -----------------------------------------------------

    def qty_for_cash_fraction(self, fraction: float, price: float) -> float:
        """Units purchasable with ``fraction`` of current cash at ``price``.

        Baseline fixed-percentage sizing (ROADMAP Fase 6). Leaves headroom for
        fee + slippage so the fill does not bounce on a cash shortfall.
        """
        if not 0 < fraction <= 1:
            raise ValueError("fraction must be in (0, 1]")
        if price <= 0:
            raise ValueError("price must be positive")
        budget = self.portfolio.cash * fraction
        # Mirror the execution math exactly: fee applies to the SLIPPED
        # notional (compounding, not additive), plus a hair of float headroom.
        slip_rate = self.cost_model.slippage.rate(price)
        unit_cost = price * (1 + slip_rate) * (1 + self.cost_model.fee.taker_rate)
        return max(budget / unit_cost * (1 - 1e-9), 0.0)
