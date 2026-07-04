"""Execution layer (ADR-010, ADR-011, ADR-012, ADR-013) — Fase 6.

PaperBroker simulates spot execution with the same cost model as the Fase 2
backtests, no-look-ahead fills (order at t -> next bar), long-only, and
scenario-based portfolios with audit-preserving reset/fork (ADR-011).
A future LiveBroker would share the ``Broker`` interface — but live trading
stays out of scope per ADR-004.
"""

from __future__ import annotations

from src.execution.orders import Order, OrderStatus, OrderType, Side
from src.execution.paper_broker import Bar, Broker, PaperBroker, default_cost_model
from src.execution.portfolio import Portfolio, Position
from src.execution.scenarios import (
    DEFAULT_SCENARIOS,
    ScenarioState,
    ScenarioStore,
    ensure_default_scenarios,
)

__all__ = [
    "DEFAULT_SCENARIOS",
    "Bar",
    "Broker",
    "Order",
    "OrderStatus",
    "OrderType",
    "PaperBroker",
    "Portfolio",
    "Position",
    "ScenarioState",
    "ScenarioStore",
    "Side",
    "default_cost_model",
    "ensure_default_scenarios",
]
