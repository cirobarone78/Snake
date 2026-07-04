"""Portfolio state: cash, positions, P&L (Fase 6, ADR-010).

Pure bookkeeping — no market opinions, no order logic. The broker mutates the
portfolio through ``apply_buy``/``apply_sell`` (which enforce the accounting
identities) and reads ``equity`` against a price snapshot. Average-cost basis
for realized P&L (the common spot-exchange convention).

Long-only invariants live here: cash can never go negative (a buy larger than
cash is the *broker's* job to reject, but the portfolio double-checks) and a
sell can never exceed the held quantity.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Position:
    """An open long position, average-cost basis."""

    qty: float = 0.0
    avg_cost: float = 0.0  # per-unit cost including buy fees

    @property
    def cost_basis(self) -> float:
        return self.qty * self.avg_cost


@dataclass
class Portfolio:
    """Cash + positions for one scenario."""

    cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0
    fees_paid: float = 0.0

    def apply_buy(self, symbol: str, qty: float, price: float, fee: float) -> None:
        """Buy ``qty`` at ``price`` paying ``fee``; fee is capitalised into cost."""
        if qty <= 0 or price <= 0 or fee < 0:
            raise ValueError("invalid buy parameters")
        total = qty * price + fee
        if total > self.cash + 1e-9:
            raise ValueError("insufficient cash for buy")
        self.cash -= total
        self.fees_paid += fee
        pos = self.positions.setdefault(symbol, Position())
        new_qty = pos.qty + qty
        pos.avg_cost = (pos.cost_basis + total) / new_qty
        pos.qty = new_qty

    def apply_sell(self, symbol: str, qty: float, price: float, fee: float) -> float:
        """Sell ``qty`` at ``price`` paying ``fee``; returns the realized P&L."""
        if qty <= 0 or price <= 0 or fee < 0:
            raise ValueError("invalid sell parameters")
        pos = self.positions.get(symbol)
        if pos is None or qty > pos.qty + 1e-9:
            raise ValueError("cannot sell more than held (long-only)")
        proceeds = qty * price - fee
        pnl = proceeds - qty * pos.avg_cost
        self.cash += proceeds
        self.fees_paid += fee
        self.realized_pnl += pnl
        pos.qty -= qty
        if pos.qty <= 1e-12:
            del self.positions[symbol]
        return pnl

    def equity(self, prices: dict[str, float]) -> float:
        """Cash + mark-to-market of open positions at ``prices``.

        Every open position must have a price — a missing mark is a data bug
        upstream and silently pricing at zero would corrupt the equity curve.
        """
        value = self.cash
        for symbol, pos in self.positions.items():
            if symbol not in prices:
                raise KeyError(f"no mark price for open position {symbol!r}")
            value += pos.qty * prices[symbol]
        return value

    def unrealized_pnl(self, prices: dict[str, float]) -> float:
        return sum(
            pos.qty * prices[symbol] - pos.cost_basis
            for symbol, pos in self.positions.items()
            if symbol in prices
        )

    def to_record(self) -> dict[str, object]:
        """Flat snapshot for persistence (positions serialized per symbol)."""
        return {
            "cash": self.cash,
            "realized_pnl": self.realized_pnl,
            "fees_paid": self.fees_paid,
            "positions": {
                s: {"qty": p.qty, "avg_cost": p.avg_cost} for s, p in self.positions.items()
            },
        }

    @classmethod
    def from_record(cls, rec: dict[str, object]) -> Portfolio:
        raw_positions = rec.get("positions") or {}
        if not isinstance(raw_positions, dict):
            raise ValueError("positions must be a mapping")
        positions: dict[str, Position] = {}
        for sym, p in raw_positions.items():
            if not isinstance(p, dict):
                raise ValueError("position record must be a mapping")
            positions[str(sym)] = Position(qty=float(p["qty"]), avg_cost=float(p["avg_cost"]))
        return cls(
            cash=float(rec["cash"]),  # type: ignore[arg-type]
            positions=positions,
            realized_pnl=float(rec.get("realized_pnl", 0.0)),  # type: ignore[arg-type]
            fees_paid=float(rec.get("fees_paid", 0.0)),  # type: ignore[arg-type]
        )
