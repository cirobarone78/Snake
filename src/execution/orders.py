"""Order model for the execution layer (Fase 6, ADR-010).

An order is born ``pending`` at bar ``t`` and can only be evaluated against a
*later* bar — the no-look-ahead principle (ADR-010 #1) is enforced by the
broker, but the model carries the timestamps that make it auditable: when the
order was created, when (and at what price) it was filled or cancelled.

Long-only spot semantics for now (ADR: no leverage, no short): a SELL is only
valid against an existing position; the broker enforces it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from itertools import count
from typing import Final

import pandas as pd

_ORDER_SEQ: Final = count(1)


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(StrEnum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """One order in a scenario's audit trail.

    ``limit_price`` is required for LIMIT orders and ignored for MARKET.
    ``qty`` is in units of the asset (not cash), always positive; the side
    carries the direction. Fill fields stay ``None`` until the broker fills.
    """

    scenario_id: str
    symbol: str
    side: Side
    order_type: OrderType
    qty: float
    created_at: pd.Timestamp
    limit_price: float | None = None
    order_id: int = field(default_factory=lambda: next(_ORDER_SEQ))
    status: OrderStatus = OrderStatus.PENDING
    filled_at: pd.Timestamp | None = None
    fill_price: float | None = None
    fee_paid: float | None = None
    reject_reason: str | None = None

    def __post_init__(self) -> None:
        if self.qty <= 0:
            raise ValueError("qty must be positive")
        if self.order_type is OrderType.LIMIT and self.limit_price is None:
            raise ValueError("limit orders require limit_price")
        if self.limit_price is not None and self.limit_price <= 0:
            raise ValueError("limit_price must be positive")

    def to_record(self) -> dict[str, object]:
        """Flat dict for the parquet audit trail."""
        return {
            "order_id": self.order_id,
            "scenario_id": self.scenario_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "qty": self.qty,
            "limit_price": self.limit_price,
            "created_at": self.created_at,
            "status": self.status.value,
            "filled_at": self.filled_at,
            "fill_price": self.fill_price,
            "fee_paid": self.fee_paid,
            "reject_reason": self.reject_reason,
        }
