"""Live-shadow daily runner (Fase 6): the paper portfolios come alive.

One run per day (cron): with price history up to the last completed daily bar
``T``, each scenario

1. **restores** its pending orders (decided on a previous run, ADR-010: they
   fill on the first bar after their creation) and processes every bar after
   ``last_processed`` up to ``T`` — fills happen at those bars' opens;
2. **decides**: computes momentum target weights as of ``T`` and submits the
   rebalancing market orders (created at ``T`` -> they will fill on ``T+1``,
   i.e. on the *next* run — never today);
3. **snapshots** equity at ``T`` close and persists everything (state, order
   audit trail, equity curve — committed per ADR-029).

Re-running on the same ``T`` is a no-op (idempotent): safe against cron
retries and manual runs.

Run:  uv run python -m src.execution.live_shadow
"""

from __future__ import annotations

import logging
from typing import Any, cast

import pandas as pd

from src.execution.orders import Order, OrderType, Side
from src.execution.paper_broker import Bar, PaperBroker
from src.execution.scenarios import ScenarioStore, ensure_default_scenarios
from src.execution.strategy import DEFAULT_LOOKBACK, momentum_target_weights

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Skip rebalancing trades smaller than this fraction of equity: fee churn
# protection (a 0.3% drift is noise, trading it is a guaranteed cost).
MIN_TRADE_EQUITY_FRAC = 0.01

# Structural cash reserve: orders sized today fill at TOMORROW's open, which
# in an uptrend is higher than today's close — sizing to 100% of equity would
# bounce on cash at fill time. 97% utilization absorbs overnight gaps up to
# ~2.5% plus fees/slippage; larger gaps reject (audited) and self-heal on the
# next day's re-decision.
CAPITAL_UTILIZATION = 0.97


def _bars_after(
    history: dict[str, pd.DataFrame], after: pd.Timestamp | None
) -> list[Bar]:
    """All bars strictly after ``after``, across symbols, in time order."""
    bars: list[Bar] = []
    for symbol, df in history.items():
        frame = df.sort_index()
        if after is not None:
            frame = frame.loc[frame.index > after]
        for ts, row in frame.iterrows():
            bars.append(
                Bar(
                    symbol=symbol,
                    ts=cast("pd.Timestamp", ts),
                    open=float(cast("float", row["open"])),
                    high=float(cast("float", row["high"])),
                    low=float(cast("float", row["low"])),
                    close=float(cast("float", row["close"])),
                )
            )
    bars.sort(key=lambda b: b.ts)
    return bars


def run_daily(
    store: ScenarioStore,
    history: dict[str, pd.DataFrame],
    lookback: int = DEFAULT_LOOKBACK,
) -> dict[str, dict[str, Any]]:
    """Advance every scenario to the last completed bar in ``history``.

    ``history`` maps symbol -> OHLC frame (daily, tz-aware index) up to and
    including the decision bar ``T``. Returns a per-scenario summary dict
    (for logging/reporting). Idempotent per ``T``.
    """
    if not history:
        raise ValueError("empty history")
    t_last = cast(
        "pd.Timestamp", min(cast("pd.Timestamp", df.index.max()) for df in history.values())
    )  # common last bar
    closes_at_t = {
        s: float(cast("float", df.sort_index()["close"].iloc[-1])) for s, df in history.items()
    }

    summaries: dict[str, dict[str, Any]] = {}
    for scenario_id in ensure_default_scenarios(store):
        state = store.load(scenario_id)
        if state.last_processed is not None and state.last_processed >= t_last:
            logger.info("%s: already processed %s, no-op", scenario_id, t_last.date())
            summaries[scenario_id] = {"skipped": True}
            continue

        broker = PaperBroker(state.portfolio)
        broker.pending = store.load_pending(scenario_id)

        # 1. fills: every bar after last_processed, oldest first
        touched: list[Order] = []
        for bar in _bars_after(history, state.last_processed):
            touched.extend(broker.process_bar(bar))

        # 2. decide as of T. The strategy is "long while momentum is positive":
        # we trade on SIGNAL CHANGES (plus self-healing after rejected fills),
        # never on daily drift — chasing the exact weight every day is
        # rebalance drag, i.e. guaranteed fee churn for no signal.
        closes_hist = {
            s: cast("pd.Series", df.sort_index()["close"]) for s, df in history.items()
        }
        targets = momentum_target_weights(closes_hist, lookback=lookback)
        equity = state.portfolio.equity(closes_at_t)
        pending_symbols = {o.symbol for o in broker.pending}
        new_orders: list[Order] = []
        for symbol, target_w in targets.items():
            price = closes_at_t[symbol]
            pos = state.portfolio.positions.get(symbol)
            current_val = (pos.qty if pos else 0.0) * price
            target_val = target_w * CAPITAL_UTILIZATION * equity
            prev_w = state.last_targets.get(symbol, 0.0)
            signal_changed = abs(target_w - prev_w) > 1e-9
            # self-heal: signal already on but the position is missing/half
            # (e.g. a fill bounced on a big gap) and nothing is in flight
            underfilled = (
                target_w > 0
                and current_val < 0.5 * target_val
                and symbol not in pending_symbols
            )
            if not (signal_changed or underfilled):
                continue
            delta_val = target_val - current_val
            if abs(delta_val) < MIN_TRADE_EQUITY_FRAC * equity:
                continue
            side = Side.BUY if delta_val > 0 else Side.SELL
            qty = abs(delta_val) / price
            if side is Side.SELL and pos is not None:
                qty = min(qty, pos.qty)
            if qty <= 0:
                continue
            order = Order(
                scenario_id=scenario_id, symbol=symbol, side=side,
                order_type=OrderType.MARKET, qty=qty, created_at=t_last,
            )
            new_orders.append(broker.submit(order))
        state.last_targets = {s: w for s, w in targets.items() if w > 0}

        # 3. snapshot + persist (orders upserted: fills update their record)
        store.append_orders(scenario_id, touched + new_orders)
        store.append_equity(scenario_id, t_last, equity=equity, cash=state.portfolio.cash)
        state.last_processed = t_last
        store.save(state)

        summaries[scenario_id] = {
            "as_of": str(t_last),
            "equity": round(equity, 2),
            "cash": round(state.portfolio.cash, 2),
            "fills": len(touched),
            "new_orders": len(new_orders),
            "targets": {s: round(w, 3) for s, w in targets.items() if w > 0},
        }
        logger.info("%s: %s", scenario_id, summaries[scenario_id])
    return summaries


def main() -> None:
    """Fetch Tier 1 daily bars and advance the paper scenarios (cron entry)."""
    from src.assets.asset import TIER1_ASSETS
    from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

    src = YahooFinanceSource()
    start = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=DEFAULT_LOOKBACK * 4)).date().isoformat()
    history: dict[str, pd.DataFrame] = {}
    for asset in TIER1_ASSETS:
        try:
            df = src.fetch_ohlcv(asset, start=start, interval="1d").sort_index()
        except Exception:
            logger.exception("fetch failed for %s", asset.symbol)
            continue
        if df.empty:
            continue
        # drop today's partial bar: only completed daily bars may fill orders
        today = pd.Timestamp.now(tz="UTC").normalize()
        df = df.loc[df.index < today]
        if not df.empty:
            history[asset.symbol] = df

    if len(history) < len(TIER1_ASSETS):
        missing = {a.symbol for a in TIER1_ASSETS} - set(history)
        logger.warning("missing history for %s — proceeding without them", sorted(missing))
    if not history:
        raise SystemExit("no price history available, aborting run")

    store = ScenarioStore()
    summaries = run_daily(store, history)
    logger.info("live-shadow run complete: %s", {k: v.get("equity") for k, v in summaries.items()})


if __name__ == "__main__":
    main()
