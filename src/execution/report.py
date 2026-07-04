"""Paper-portfolio report for the dashboard (Fase 6 / Fase 7).

Turns the committed scenario state (ADR-029) into
``public/data/paper_report.json`` — the data behind the dashboard "Paper"
tab. Metrics on the equity curve are the SAME functions the Fase 2 backtests
use (``summarize``): one measuring stick everywhere, per the ROADMAP
requirement. Metrics appear only once the curve has enough points to mean
anything (>= 5 daily observations); before that the report says so instead of
showing noise dressed as statistics.

Pure transform over the store; unit-testable offline.
"""

from __future__ import annotations

from typing import Any, cast

import pandas as pd

from src.backtest.metrics import DAILY_CRYPTO, summarize
from src.execution.scenarios import ScenarioStore

DISCLAIMER = (
    "Portafogli VIRTUALI (paper trading): nessun denaro reale. Ordini simulati "
    "col modello di costi del progetto, eseguiti alla barra successiva. "
    "Non è consulenza finanziaria."
)

MIN_POINTS_FOR_METRICS = 5


def _scenario_payload(
    store: ScenarioStore, scenario_id: str, marks: dict[str, float]
) -> dict[str, Any]:
    state = store.load(scenario_id)
    pf = state.portfolio

    # mark-to-market only where a price is available; report staleness rather
    # than crashing the whole report on one missing mark
    positions: list[dict[str, Any]] = []
    marked = True
    for symbol, pos in sorted(pf.positions.items()):
        price = marks.get(symbol)
        if price is None:
            marked = False
        positions.append(
            {
                "symbol": symbol,
                "qty": round(pos.qty, 8),
                "avg_cost": round(pos.avg_cost, 4),
                "price": round(price, 4) if price is not None else None,
                "value": round(pos.qty * price, 2) if price is not None else None,
                "pnl_pct": round((price / pos.avg_cost - 1) * 100, 2)
                if price is not None and pos.avg_cost > 0
                else None,
            }
        )

    curve = store.equity_curve(scenario_id)
    equity = float(curve.iloc[-1]) if len(curve) else pf.cash
    points = [
        {"t": cast("pd.Timestamp", ts).date().isoformat(), "v": round(float(v), 2)}
        for ts, v in curve.items()
    ]

    metrics: dict[str, Any] | None = None
    if len(curve) >= MIN_POINTS_FOR_METRICS:
        returns = curve.sort_index().pct_change().dropna()
        s = summarize(returns, periods_per_year=DAILY_CRYPTO)
        metrics = {
            "sharpe": round(s.sharpe, 2) if s.sharpe == s.sharpe else None,
            "max_drawdown_pct": round(s.max_drawdown * 100, 2),
            "time_underwater_pct": round(s.time_underwater * 100, 1)
            if s.time_underwater == s.time_underwater
            else None,
            "n_days": s.n_periods,
        }

    orders = store.orders(scenario_id)
    recent: list[dict[str, Any]] = []
    if not orders.empty:
        tail = orders.sort_values("created_at").tail(10)
        for _, row in tail.iterrows():
            r = cast("Any", row)  # pandas row access is untyped without stubs
            recent.append(
                {
                    "created_at": str(r["created_at"])[:10],
                    "symbol": str(r["symbol"]),
                    "side": str(r["side"]),
                    "qty": round(float(r["qty"]), 6),
                    "status": str(r["status"]),
                    "fill_price": round(float(r["fill_price"]), 4)
                    if pd.notna(r["fill_price"])
                    else None,
                }
            )

    return {
        "scenario_id": scenario_id,
        "initial_cash": state.initial_cash,
        "equity": round(equity, 2),
        "cash": round(pf.cash, 2),
        "return_pct": round((equity / state.initial_cash - 1) * 100, 2),
        "realized_pnl": round(pf.realized_pnl, 2),
        "fees_paid": round(pf.fees_paid, 2),
        "fully_marked": marked,
        "last_processed": str(state.last_processed)[:10] if state.last_processed else None,
        "positions": positions,
        "targets": state.last_targets,
        "metrics": metrics,
        "curve": points,
        "recent_orders": recent,
    }


def build_paper_report(
    store: ScenarioStore,
    marks: dict[str, float],
    generated_at: pd.Timestamp | None = None,
) -> dict[str, Any]:
    """Assemble the dashboard payload for every registered scenario."""
    stamp = generated_at if generated_at is not None else pd.Timestamp.now(tz="UTC")
    scenarios = [_scenario_payload(store, sid, marks) for sid in sorted(store.registry())]
    return {
        "generated_at": stamp.isoformat(),
        "title": "Paper trading",
        "disclaimer": DISCLAIMER,
        "scenarios": scenarios,
    }
