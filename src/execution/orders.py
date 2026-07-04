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
from uuid import uuid4

import pandas as pd


def _new_order_id() -> str:
    """Process-independent id: pending orders survive across cron runs, so a
    per-process counter would collide between runs. 12 hex chars are plenty
    for a single sequential writer."""
    return uuid4().hex[:12]


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
    order_id: str = field(default_factory=_new_order_id)
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

    @classmethod
    def from_record(cls, rec: dict[str, object]) -> Order:
        """Rebuild an order from its parquet record (cross-run pending)."""

        def _opt_float(v: object) -> float | None:
            return None if v is None or pd.isna(v) else float(v)  # type: ignore[arg-type]

        def _opt_ts(v: object) -> pd.Timestamp | None:
            return None if v is None or pd.isna(v) else pd.Timestamp(v)  # type: ignore[arg-type]

        reject = rec.get("reject_reason")
        return cls(
            scenario_id=str(rec["scenario_id"]),
            symbol=str(rec["symbol"]),
            side=Side(str(rec["side"])),
            order_type=OrderType(str(rec["order_type"])),
            qty=float(rec["qty"]),  # type: ignore[arg-type]
            created_at=pd.Timestamp(rec["created_at"]),  # type: ignore[arg-type]
            limit_price=_opt_float(rec.get("limit_price")),
            order_id=str(rec["order_id"]),
            status=OrderStatus(str(rec["status"])),
            filled_at=_opt_ts(rec.get("filled_at")),
            fill_price=_opt_float(rec.get("fill_price")),
            fee_paid=_opt_float(rec.get("fee_paid")),
            reject_reason=None if reject is None or pd.isna(reject) else str(reject),  # type: ignore[arg-type]
        )
