# pyright: strict, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Weekly sector-ETF rotation: from a ranking to a paper portfolio (WP4).

**This rule is not predictive, and the module says so in every direction it can.**
WP3 measured the 60-session relative momentum at an out-of-sample Spearman IC of
0,0010 (t = 0,08) — *below* a seeded random ranker — and every model's Brier
score came out worse than a constant (ADR-034). The adoption bar was not passed,
so the plan's own fallback applies: WP4 runs the plain momentum rule, declared
non-predictive, because the value being built here is the **measuring
apparatus** — an immutable ledger, a broker with real costs, a forward track
record — not an edge.

The rule, in full, with nothing hidden:

    take the ETFs with a defined ``rel_ret_60``, rank them, hold the top 5
    equal-weight, cap 20% per asset.

Three consequences of that being the whole rule:

- **The D7 confidence threshold is off** (ADR-036). D7 gates on a *calibrated*
  probability; there is none. Applied to a percentile rank it would never bind
  (the 5th of 20 names sits at 0,80 every week), which is a filter that looks
  like prudence and does nothing. The mechanism survives as
  ``confidence_threshold`` and is tested, but production passes ``None``.
- **Cash appears only for lack of names**, never for lack of conviction: fewer
  than 5 scoreable symbols leaves the remainder uninvested. Being fully invested
  is the neutral stance for a *relative* rotation measured against SPY — this
  portfolio is not a market timer and must not be read as one.
- **Orders fill on the next bar** through ``PaperBroker`` with the project's
  cost model, same as every other paper track in the repo (ADR-010/012/013). A
  weekly cadence means a decision taken on Monday's close fills at Tuesday's
  open, processed on the following run.

Idempotency is structural, not incidental: re-running the same decision date is
a no-op, because a cron that retries must not double a portfolio's turnover.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, cast

import pandas as pd

from src.execution.live_shadow import bars_after
from src.execution.orders import Order, OrderType, Side
from src.execution.paper_broker import PaperBroker
from src.execution.prediction_ledger import Factor, Prediction
from src.execution.scenarios import ScenarioStore

logger = logging.getLogger(__name__)

SCENARIO_ID = "etf_top5"
SCENARIO_CAPITAL = 10_000.0
"""Simulated capital for the rotation scenario (plan §WP4, decision D6)."""

SCORE_COLUMN = "rel_ret_60"
VOL_COLUMN = "vol_60"
TOP_N = 5
MAX_WEIGHT = 0.20
"""D6: top 5, equal weight, 20% cap. With 5 names the cap binds exactly."""

DEFAULT_HORIZONS: tuple[int, ...] = (20, 60)
"""Ledger horizons (D3): primary 20 sessions, secondary 60."""

RULE_ID = "momentum_rel_60"
RULE_VERSION = "momentum_rel_60@1"
BENCHMARK_SYMBOL = "SPY"

RULE_DESCRIPTION = (
    "Top 5 ETF per momentum relativo a 60 sedute contro SPY, equal weight, "
    "cap 20% per asset. Nessuna soglia di confidenza (ADR-036)."
)
NON_PREDICTIVE_REASON = (
    "Regola NON predittiva. ADR-034: la barra di adozione non è stata superata "
    "— IC Spearman OOS del momentum 0,0010 (t = 0,08), sotto il ranker casuale, "
    "e Brier peggiore della climatologia per ogni modello. Nessuna probabilità "
    "calibrata è disponibile, quindi non ne viene pubblicata nessuna (ADR-036)."
)

# Same frictions guard as the daily live-shadow runner: a sub-1% drift is noise,
# and trading it is a guaranteed cost against a signal already measured as zero.
MIN_TRADE_EQUITY_FRAC = 0.01
# Orders sized at today's close fill at the next open; 97% utilisation leaves
# room for an overnight gap plus fees so the fill does not bounce on cash.
CAPITAL_UTILIZATION = 0.97


@dataclass(frozen=True)
class RankedAsset:
    """One symbol's place in the week's cross-section, plus what drove it.

    ``score`` is the raw ``rel_ret_60`` — an observed trailing return, not a
    forecast — and ``rank`` is 1 for the strongest. ``realized_vol_60`` is
    likewise realised, never "expected".
    """

    symbol: str
    score: float
    rank: int
    universe_size: int
    close: float | None = None
    realized_vol_60: float | None = None
    target_weight: float = 0.0

    @property
    def selected(self) -> bool:
        return self.target_weight > 0.0

    @property
    def rank_pct(self) -> float:
        """Percentile of the score within the day's cross-section, in ``(0, 1]``."""
        return (self.universe_size - self.rank + 1) / self.universe_size


@dataclass(frozen=True)
class RotationDecision:
    """The complete weekly decision: what was ranked, what is held, and why."""

    as_of: pd.Timestamp
    ranked: list[RankedAsset]
    regime: str = "unknown"
    rule: str = RULE_ID
    rule_version: str = RULE_VERSION
    predictive: bool = False
    dataset_version: str = "unknown"
    excluded: list[str] = field(default_factory=list)

    @property
    def weights(self) -> dict[str, float]:
        return {a.symbol: a.target_weight for a in self.ranked if a.target_weight > 0.0}

    @property
    def cash_weight(self) -> float:
        return max(0.0, 1.0 - sum(self.weights.values()))


def target_weights(
    scores: dict[str, float],
    top_n: int = TOP_N,
    max_weight: float = MAX_WEIGHT,
    probabilities: dict[str, float] | None = None,
    confidence_threshold: float | None = None,
) -> dict[str, float]:
    """Equal-weight targets over the ``top_n`` highest scores, capped.

    Symbols with a missing or non-finite score are not ranked at all: a NaN is
    "we do not know yet" (warm-up, short history), and guessing its place would
    quietly reshape the universe over time.

    ``confidence_threshold`` is the D7 mechanism, **disabled in production**
    (ADR-036). When it is not ``None``, ``probabilities`` must supply a
    calibrated ``P(outperform)`` per symbol and any selected name below the
    threshold is dropped, its weight staying in cash — the "liquidità parziale"
    of D7, generalised from the 5th-ranked name to every selected name. Passing
    a threshold without probabilities is a programming error, not a silent
    no-op.

    Ties are broken by symbol name so the same input always produces the same
    portfolio; an arbitrary but stable tie-break beats an arbitrary unstable one.
    """
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    if not 0.0 < max_weight <= 1.0:
        raise ValueError("max_weight must be in (0, 1]")
    if confidence_threshold is not None and probabilities is None:
        raise ValueError("confidence_threshold requires probabilities (ADR-036)")

    ranked = _sorted_scores(scores)
    selected = [symbol for symbol, _ in ranked[:top_n]]

    if confidence_threshold is not None:
        probs = probabilities or {}
        selected = [s for s in selected if probs.get(s, float("nan")) >= confidence_threshold]

    if not selected:
        return {}
    weight = min(1.0 / top_n, max_weight)
    return {symbol: weight for symbol in selected}


def _sorted_scores(scores: dict[str, float]) -> list[tuple[str, float]]:
    """Finite scores, strongest first, ties broken by symbol for determinism."""
    finite = [(s, float(v)) for s, v in scores.items() if pd.notna(v)]
    return sorted(finite, key=lambda kv: (-kv[1], kv[0]))


def rank_universe(
    scores: dict[str, float],
    closes: dict[str, float] | None = None,
    vols: dict[str, float] | None = None,
    top_n: int = TOP_N,
    max_weight: float = MAX_WEIGHT,
    probabilities: dict[str, float] | None = None,
    confidence_threshold: float | None = None,
) -> list[RankedAsset]:
    """Full cross-section, strongest first, with the target weight attached.

    The whole universe is returned, not only the holdings: the ledger records
    every name it looked at, so a later reader can compute an information
    coefficient on the live decisions instead of only on the winners.
    """
    ordered = _sorted_scores(scores)
    weights = target_weights(
        scores,
        top_n=top_n,
        max_weight=max_weight,
        probabilities=probabilities,
        confidence_threshold=confidence_threshold,
    )
    universe_size = len(ordered)
    closes = closes or {}
    vols = vols or {}
    out: list[RankedAsset] = []
    for position, (symbol, score) in enumerate(ordered, start=1):
        vol = vols.get(symbol)
        close = closes.get(symbol)
        out.append(
            RankedAsset(
                symbol=symbol,
                score=score,
                rank=position,
                universe_size=universe_size,
                close=None if close is None or pd.isna(close) else float(close),
                realized_vol_60=None if vol is None or pd.isna(vol) else float(vol),
                target_weight=weights.get(symbol, 0.0),
            )
        )
    return out


def decide_from_panel(
    panel: pd.DataFrame,
    as_of: pd.Timestamp | None = None,
    dataset_version: str = "unknown",
    top_n: int = TOP_N,
    max_weight: float = MAX_WEIGHT,
    confidence_threshold: float | None = None,
) -> RotationDecision:
    """Build the week's decision from the WP2 panel's latest cross-section.

    ``as_of`` defaults to the panel's last date. Only rows *at* that date are
    used — the panel is point-in-time by construction (WP2), so this reads one
    day's state and nothing about the future.
    """
    if panel.empty:
        raise ValueError("empty panel: nothing to rank")
    dates = pd.to_datetime(cast("pd.Series", panel["date"]))
    decision_date = cast("pd.Timestamp", dates.max() if as_of is None else pd.Timestamp(as_of))
    cross = cast("pd.DataFrame", panel[dates == decision_date])
    if cross.empty:
        raise ValueError(f"no panel rows at {decision_date}")

    symbols = [str(s) for s in cast("pd.Series", cross["symbol"])]
    raw_scores = [float(v) for v in cast("pd.Series", cross[SCORE_COLUMN])]
    scores = dict(zip(symbols, raw_scores, strict=True))
    closes = (
        dict(zip(symbols, [float(v) for v in cast("pd.Series", cross["close"])], strict=True))
        if "close" in cross.columns
        else {}
    )
    vols = (
        dict(zip(symbols, [float(v) for v in cast("pd.Series", cross[VOL_COLUMN])], strict=True))
        if VOL_COLUMN in cross.columns
        else {}
    )
    regimes = [str(r) for r in cast("pd.Series", cross["regime"])] if "regime" in cross.columns else []
    regime = regimes[0] if regimes else "unknown"

    ranked = rank_universe(
        scores,
        closes=closes,
        vols=vols,
        top_n=top_n,
        max_weight=max_weight,
        confidence_threshold=confidence_threshold,
    )
    excluded = sorted(s for s in symbols if s not in {a.symbol for a in ranked})
    if excluded:
        logger.info("Not scoreable at %s (missing %s): %s", decision_date.date(), SCORE_COLUMN, excluded)
    return RotationDecision(
        as_of=decision_date,
        ranked=ranked,
        regime=regime,
        dataset_version=dataset_version,
        excluded=excluded,
    )


def to_predictions(
    decision: RotationDecision,
    emitted_at: pd.Timestamp,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    tickers: dict[str, str] | None = None,
) -> list[Prediction]:
    """Ledger rows for the whole ranked universe, one per symbol per horizon.

    Every forecast field is left ``None`` and ``confidence`` is
    ``not_applicable``: the rule is declared non-predictive, and the schema
    refuses anything else (ADR-036). What travels instead is the observed state
    that produced the ranking.
    """
    tickers = tickers or {}
    emitted = emitted_at if emitted_at.tzinfo is not None else emitted_at.tz_localize("UTC")
    cutoff = decision.as_of if decision.as_of.tzinfo is not None else decision.as_of.tz_localize("UTC")
    rows: list[Prediction] = []
    for horizon in horizons:
        for asset in decision.ranked:
            rows.append(
                Prediction(
                    emitted_at=emitted.isoformat(),
                    data_cutoff=cutoff.isoformat(),
                    model_version=decision.rule_version,
                    dataset_version=decision.dataset_version,
                    asset=asset.symbol,
                    ticker=tickers.get(asset.symbol),
                    benchmark=BENCHMARK_SYMBOL,
                    horizon_days=horizon,
                    predictive=decision.predictive,
                    rule=decision.rule,
                    non_predictive_reason=None if decision.predictive else NON_PREDICTIVE_REASON,
                    selection_score=asset.score,
                    selection_rank=asset.rank,
                    universe_size=asset.universe_size,
                    realized_vol_60=asset.realized_vol_60,
                    selected=asset.selected,
                    target_weight=asset.target_weight,
                    regime=decision.regime,
                    top_factors=[
                        Factor(
                            name=SCORE_COLUMN,
                            direction="positive" if asset.score > 0 else "negative",
                            value=asset.score,
                        )
                    ],
                )
            )
    return rows


def ensure_scenario(store: ScenarioStore, scenario_id: str = SCENARIO_ID) -> str:
    """Create the rotation scenario on first use; returns its id."""
    if scenario_id not in store.registry():
        store.create(scenario_id, SCENARIO_CAPITAL)
        logger.info("created scenario %s with %.0f", scenario_id, SCENARIO_CAPITAL)
    return scenario_id


def run_weekly(
    store: ScenarioStore,
    history: dict[str, pd.DataFrame],
    decision: RotationDecision,
    scenario_id: str = SCENARIO_ID,
) -> dict[str, Any]:
    """Fill what the past week allows, then submit this week's rebalance.

    ``history`` maps symbol -> OHLC frame up to the decision bar. The order is
    always the same and it matters: **fills first, decision second**. Deciding
    before processing the outstanding bars would let this week's target be
    computed against a portfolio state that has not happened yet.

    Orders created now carry ``decision.as_of`` and therefore cannot fill until
    a strictly later bar — the next run's replay. Re-running the same decision
    date does nothing at all.
    """
    if not history:
        raise ValueError("empty history")
    ensure_scenario(store, scenario_id)
    state = store.load(scenario_id)
    t_last = decision.as_of

    if state.last_processed is not None and state.last_processed >= t_last:
        logger.info("%s: already processed %s, no-op", scenario_id, t_last.date())
        return {"scenario_id": scenario_id, "skipped": True, "as_of": str(t_last)}

    broker = PaperBroker(state.portfolio)
    broker.pending = store.load_pending(scenario_id)

    # 1. fills for every bar since the last run (weekly cadence -> ~5 bars)
    touched: list[Order] = []
    for bar in bars_after(history, state.last_processed):
        if bar.ts > t_last:
            break  # never process past the decision bar
        touched.extend(broker.process_bar(bar))

    # 2. mark to market at the decision bar and rebalance towards the targets
    closes_at_t = _closes_at(history, t_last)
    targets = decision.weights
    missing_marks = [s for s in state.portfolio.positions if s not in closes_at_t]
    if missing_marks:
        raise KeyError(f"no mark price at {t_last} for open positions {sorted(missing_marks)}")
    equity = state.portfolio.equity(closes_at_t)

    new_orders = _rebalance_orders(
        scenario_id=scenario_id,
        portfolio_symbols=set(state.portfolio.positions) | set(targets),
        targets=targets,
        closes=closes_at_t,
        equity=equity,
        broker=broker,
        state_positions={s: p.qty for s, p in state.portfolio.positions.items()},
        created_at=t_last,
    )
    state.last_targets = dict(targets)

    # 3. persist: audit trail, equity point, state
    store.append_orders(scenario_id, touched + new_orders)
    store.append_equity(scenario_id, t_last, equity=equity, cash=state.portfolio.cash)
    state.last_processed = t_last
    store.save(state)

    summary: dict[str, Any] = {
        "scenario_id": scenario_id,
        "as_of": str(t_last),
        "equity": round(equity, 2),
        "cash": round(state.portfolio.cash, 2),
        "fills": len(touched),
        "new_orders": len(new_orders),
        "targets": {s: round(w, 3) for s, w in targets.items()},
        "cash_weight": round(decision.cash_weight, 3),
        "predictive": decision.predictive,
    }
    logger.info("%s: %s", scenario_id, summary)
    return summary


def _closes_at(history: dict[str, pd.DataFrame], ts: pd.Timestamp) -> dict[str, float]:
    """Close per symbol at or before ``ts`` (the price the decision could see)."""
    marks: dict[str, float] = {}
    for symbol, frame in history.items():
        window = frame.sort_index()
        window = window.loc[window.index <= ts]
        if window.empty:
            continue
        marks[symbol] = float(cast("float", window["close"].iloc[-1]))
    return marks


def _rebalance_orders(
    scenario_id: str,
    portfolio_symbols: set[str],
    targets: dict[str, float],
    closes: dict[str, float],
    equity: float,
    broker: PaperBroker,
    state_positions: dict[str, float],
    created_at: pd.Timestamp,
) -> list[Order]:
    """Market orders that move current holdings towards ``targets``.

    Sells are emitted before buys so the cash they raise is available to the
    buys — except that with t+1 fills both legs settle on the same later bar
    anyway, which is why ``CAPITAL_UTILIZATION`` keeps a reserve rather than
    assuming perfect sequencing.
    """
    pending_symbols = {o.symbol for o in broker.pending}
    legs: list[tuple[Side, str, float]] = []
    for symbol in sorted(portfolio_symbols):
        price = closes.get(symbol)
        if price is None or price <= 0:
            continue
        held_qty = state_positions.get(symbol, 0.0)
        current_val = held_qty * price
        target_val = targets.get(symbol, 0.0) * CAPITAL_UTILIZATION * equity
        delta_val = target_val - current_val
        if abs(delta_val) < MIN_TRADE_EQUITY_FRAC * equity:
            continue
        if symbol in pending_symbols:
            # an order for this symbol is still working: doubling it would
            # double the position when both fill on the same bar
            continue
        qty = abs(delta_val) / price
        side = Side.BUY if delta_val > 0 else Side.SELL
        if side is Side.SELL:
            qty = min(qty, held_qty)
        if qty <= 0:
            continue
        legs.append((side, symbol, qty))

    legs.sort(key=lambda leg: (leg[0] is not Side.SELL, leg[1]))
    orders: list[Order] = []
    for side, symbol, qty in legs:
        orders.append(
            broker.submit(
                Order(
                    scenario_id=scenario_id,
                    symbol=symbol,
                    side=side,
                    order_type=OrderType.MARKET,
                    qty=qty,
                    created_at=created_at,
                )
            )
        )
    return orders
