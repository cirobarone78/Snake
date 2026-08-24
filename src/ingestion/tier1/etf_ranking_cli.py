# pyright: strict, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Weekly ETF rotation runner: decide, record, trade on paper (WP4).

One run per week (Monday, decision D5). With daily bars up to the last completed
session ``T`` the runner

1. **fetches** the 20 sector/theme ETFs plus SPY and checks every feed for
   staleness — a frozen ticker is the failure mode this project has already been
   bitten by (ADR-026);
2. **rebuilds the WP2 panel** from those same bars, so features and prices come
   from one fetch and cannot disagree;
3. **decides**: top 5 by ``rel_ret_60``, equal weight, cap 20% — the rule
   declared *non-predictive* by ADR-034, with the D7 threshold off (ADR-036);
4. **writes the ledger row for every symbol before the outcome exists**, then
   backfills the outcomes whose horizon has finally matured;
5. **submits the rebalance** to the paper broker (fills on the next bar) and
   writes the two dashboard payloads.

**Fail-safe**: if any feed is stale, or the WP3 validation report is older than
``MAX_VALIDATION_AGE_DAYS``, the run writes ``status: "stale"`` payloads, appends
nothing to the ledger and does **not** rebalance. A portfolio traded on stale
prices produces a track record that measures the data pipeline, not the rule.

The plan's fail-safe names "a calibration older than N weeks". There is no
calibration in production (ADR-036), so the clause maps onto the artefact that
does exist: the pre-registered validation. If nobody has re-validated in six
months, the rule keeps running but the dashboard says so.

Run:  uv run python -m src.ingestion.tier1.etf_ranking_cli

Yahoo is unreachable from the development sandbox (``fc.yahoo.com`` is blocked by
the egress allowlist), so this runs in CI — the ``etf-ranking`` workflow.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, cast

import pandas as pd

from src.assets.asset import Asset, get_asset_by_symbol
from src.assets.sectors import SECTOR_ETFS
from src.execution.etf_rotation import (
    DEFAULT_HORIZONS,
    SCENARIO_CAPITAL,
    SCENARIO_ID,
    decide_from_panel,
    ensure_scenario,
    run_weekly,
    to_predictions,
)
from src.execution.prediction_ledger import DEFAULT_LEDGER_PATH, PredictionLedger
from src.execution.rotation_report import (
    STATUS_OK,
    STATUS_STALE,
    benchmark_summary,
    rotation_model_dict,
    rotation_report_dict,
)
from src.execution.scenarios import ScenarioStore
from src.features.etf_dataset import assemble, build_feature_panel, build_targets, dataset_metadata
from src.features.report_json import iso_timestamp, write_report_json
from src.ingestion.freshness import FreshnessResult, check_freshness, last_timestamp_of
from src.ingestion.tier1.build_etf_dataset import benchmark_regime
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BENCHMARK_SYMBOL = "SPY"
REPORT_PATH = Path("public/data/ranking_report.json")
MODEL_PATH = Path("public/data/ranking_model.json")
VALIDATION_PATH = Path("public/data/ranking_backtest.json")

# Enough history for a 252-session feature warm-up plus slack, without refetching
# two decades every week.
DEFAULT_LOOKBACK_DAYS = 900
# A daily equity feed older than 5 sessions is a frozen ticker, not a long weekend.
MAX_AGE_DAYS = 5.0
# Six months without a re-validation: keep running, say so loudly.
MAX_VALIDATION_AGE_DAYS = 182.0


def fetch_history(
    source: YahooFinanceSource, assets: list[Asset], start: str, now: pd.Timestamp | None = None
) -> tuple[dict[str, pd.DataFrame], list[FreshnessResult]]:
    """Daily OHLCV per asset, completed bars only, with a freshness verdict each.

    Today's partial bar is dropped: only a closed session may fill an order or
    feed a feature. A symbol that fails to fetch is logged and skipped — the
    freshness list then shows it missing rather than the run pretending it saw a
    full universe.
    """
    reference = now if now is not None else pd.Timestamp.now(tz="UTC")
    today = reference.normalize()
    history: dict[str, pd.DataFrame] = {}
    checks: list[FreshnessResult] = []
    for asset in assets:
        try:
            frame = source.fetch_ohlcv(asset, start=start, interval="1d").sort_index()
        except Exception:
            logger.exception("fetch failed for %s (%s)", asset.symbol, asset.yahoo_symbol)
            checks.append(check_freshness(None, MAX_AGE_DAYS, name=asset.symbol, now=reference))
            continue
        # empty first: an empty frame carries no DatetimeIndex to slice on
        if not frame.empty:
            frame = frame.loc[frame.index < today]
        if frame.empty:
            logger.warning("no completed bars for %s", asset.symbol)
            checks.append(check_freshness(None, MAX_AGE_DAYS, name=asset.symbol, now=reference))
            continue
        history[asset.symbol] = frame
        checks.append(
            check_freshness(
                last_timestamp_of(frame), MAX_AGE_DAYS, name=asset.symbol, now=reference
            )
        )
    return history, checks


def _timestamp(value: object) -> pd.Timestamp | None:
    """``pd.Timestamp`` or ``None`` — ``NaT`` is a missing value, not a date."""
    if value is None:
        return None
    parsed = pd.Timestamp(cast("Any", value))
    return None if parsed is pd.NaT else cast("pd.Timestamp", parsed)


def build_panel(
    history: dict[str, pd.DataFrame], benchmark: pd.DataFrame
) -> tuple[pd.DataFrame, str]:
    """WP2 panel from bars already in memory; returns ``(panel, dataset_version)``.

    Same functions as ``build_etf_dataset`` — the panel this decides on is the
    panel WP3 validated on, or the validation would be about a different dataset.
    """
    closes = pd.DataFrame({s: cast("pd.Series", f["close"]) for s, f in history.items()})
    volumes = pd.DataFrame({s: cast("pd.Series", f["volume"]) for s, f in history.items()})
    bench_close = cast("pd.Series", benchmark["close"])
    features = build_feature_panel(closes, volumes, bench_close)
    targets = build_targets(closes, bench_close, horizons=DEFAULT_HORIZONS)
    panel = assemble(features, targets, benchmark_regime(bench_close))
    version = str(dataset_metadata(panel)["schema_hash"])
    return panel, version


def validation_status(
    path: Path = VALIDATION_PATH, now: pd.Timestamp | None = None
) -> tuple[dict[str, Any] | None, str | None]:
    """WP3 verdict summary and, if any, the reason it should not be trusted today.

    A missing report is not fatal — the first run of a fresh checkout should not
    be blocked by an artefact a workflow produces — but it is reported, because
    "we never validated" and "we validated and it failed" are different states
    and the dashboard must not blur them.
    """
    if not path.exists():
        return None, "validation report missing (public/data/ranking_backtest.json)"
    payload = cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))
    generated = str(payload.get("generated_at", ""))
    verdicts = cast("list[dict[str, Any]]", payload.get("verdicts", []))
    primary = next((v for v in verdicts if int(v.get("horizon", 0)) == 20), None)
    summary: dict[str, Any] = {
        "generated_at": generated or None,
        "train_weeks": payload.get("train_weeks"),
        "test_weeks": payload.get("test_weeks"),
        "ic_bar": payload.get("ic_bar"),
        "verdict_20d": primary,
    }
    if not generated:
        return summary, "validation report has no timestamp"
    reference = now if now is not None else pd.Timestamp.now(tz="UTC")
    check = check_freshness(
        _timestamp(generated), MAX_VALIDATION_AGE_DAYS, name="ranking_backtest", now=reference
    )
    summary["age_days"] = round(check.age_days, 1) if check.age_days is not None else None
    if not check.is_fresh:
        return summary, check.message()
    return summary, None


def scenario_snapshot(
    store: ScenarioStore, scenario_id: str, marks: dict[str, float]
) -> dict[str, Any]:
    """Portfolio state for the model payload (positions marked where possible)."""
    state = store.load(scenario_id)
    positions = [
        {
            "symbol": symbol,
            "qty": round(pos.qty, 8),
            "avg_cost": round(pos.avg_cost, 4),
            "price": round(marks[symbol], 4) if symbol in marks else None,
            "value": round(pos.qty * marks[symbol], 2) if symbol in marks else None,
        }
        for symbol, pos in sorted(state.portfolio.positions.items())
    ]
    curve = store.equity_curve(scenario_id)
    priced = {s: p for s, p in marks.items() if s in state.portfolio.positions}
    equity = (
        state.portfolio.equity(priced)
        if len(priced) == len(state.portfolio.positions)
        else float(cast("float", curve.iloc[-1])) if len(curve) else state.portfolio.cash
    )
    return {
        "scenario_id": scenario_id,
        "initial_cash": state.initial_cash,
        "cash": round(state.portfolio.cash, 2),
        "equity": round(equity, 2),
        "return_pct": round((equity / state.initial_cash - 1.0) * 100.0, 2),
        "realized_pnl": round(state.portfolio.realized_pnl, 2),
        "fees_paid": round(state.portfolio.fees_paid, 2),
        "positions": positions,
        "last_processed": str(state.last_processed) if state.last_processed else None,
        "equity_points": len(curve),
        "started_at": str(curve.index[0]) if len(curve) else None,
    }


def _asset_labels() -> tuple[dict[str, str], dict[str, str]]:
    names = {a.symbol: a.name for a in SECTOR_ETFS}
    tickers = {a.symbol: a.yahoo_symbol or a.symbol for a in SECTOR_ETFS}
    return names, tickers


def _freshness_payload(checks: list[FreshnessResult]) -> list[dict[str, Any]]:
    return [
        {
            "name": c.name,
            "last_timestamp": str(c.last_timestamp) if c.last_timestamp is not None else None,
            "age_days": round(c.age_days, 2) if c.age_days is not None else None,
            "is_fresh": c.is_fresh,
        }
        for c in checks
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the weekly ETF rotation (WP4).")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--scenario", default=SCENARIO_ID)
    parser.add_argument(
        "--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS, help="history to fetch"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="decide and report without writing state"
    )
    args = parser.parse_args()

    now = pd.Timestamp.now(tz="UTC")
    start = (now - pd.Timedelta(days=int(cast("int", args.lookback_days)))).date().isoformat()
    source = YahooFinanceSource()

    benchmark_asset = get_asset_by_symbol(BENCHMARK_SYMBOL)
    if benchmark_asset is None:  # pragma: no cover - the registry is a constant
        raise SystemExit(f"{BENCHMARK_SYMBOL} missing from the asset registry")

    bench_history, bench_checks = fetch_history(source, [benchmark_asset], start, now=now)
    history, checks = fetch_history(source, SECTOR_ETFS, start, now=now)
    checks = bench_checks + checks

    generated_at = iso_timestamp(now)
    ledger = PredictionLedger(cast("Path", args.ledger))
    names, tickers = _asset_labels()
    store = ScenarioStore()
    scenario_id = str(args.scenario)

    benchmark = bench_history.get(BENCHMARK_SYMBOL)
    stale = [c for c in checks if not c.is_fresh]
    validation, validation_warning = validation_status(now=now)

    reasons: list[str] = []
    if benchmark is None or benchmark.empty:
        reasons.append(f"no benchmark bars for {BENCHMARK_SYMBOL}")
    if not history:
        reasons.append("no ETF bars fetched")
    if stale:
        reasons.append("stale feeds: " + ", ".join(c.message() for c in stale))
    if validation_warning:
        reasons.append(validation_warning)

    if reasons:
        reason = " | ".join(reasons)
        logger.error("FAIL-SAFE: %s", reason)
        logger.error("No ledger row appended and no rebalance: writing stale payloads.")
        _write_payloads(
            decision=None,
            generated_at=generated_at,
            ledger=ledger,
            status=STATUS_STALE,
            status_reason=reason,
            names=names,
            tickers=tickers,
            checks=checks,
            validation=validation,
            scenario=None,
            benchmarks=None,
        )
        raise SystemExit(1)

    assert benchmark is not None
    panel, dataset_version = build_panel(history, benchmark)
    decision = decide_from_panel(panel, dataset_version=dataset_version)
    logger.info(
        "Decision %s | regime=%s | universe=%d | targets=%s | cash=%.1f%%",
        decision.as_of.date(), decision.regime, len(decision.ranked),
        decision.weights, 100.0 * decision.cash_weight,
    )

    predictions = to_predictions(decision, emitted_at=now, tickers=tickers)
    if cast("bool", args.dry_run):
        logger.info("Dry run: %d ledger rows withheld, no orders submitted.", len(predictions))
        return

    appended = ledger.append(predictions)
    logger.info("Ledger: %d new rows (%d total)", appended, len(ledger.raw_records()))

    closes = {s: cast("pd.Series", f["close"]) for s, f in history.items()}
    bench_close = cast("pd.Series", benchmark["close"])
    resolved = ledger.backfill_outcomes(closes, bench_close, now=now)
    logger.info("Ledger: %d outcomes resolved", resolved)

    ensure_scenario(store, scenario_id)
    summary = run_weekly(store, history, decision, scenario_id=scenario_id)
    logger.info("Scenario: %s", summary)

    marks = {
        s: float(cast("float", f.sort_index()["close"].iloc[-1])) for s, f in history.items()
    }
    snapshot = scenario_snapshot(store, scenario_id, marks)
    started_at = snapshot.get("started_at")
    benchmarks = benchmark_summary(
        closes,
        bench_close,
        _timestamp(started_at),
        initial_capital=SCENARIO_CAPITAL,
    )

    _write_payloads(
        decision=decision,
        generated_at=generated_at,
        ledger=ledger,
        status=STATUS_OK,
        status_reason=None,
        names=names,
        tickers=tickers,
        checks=checks,
        validation=validation,
        scenario=snapshot,
        benchmarks=benchmarks,
    )


def _write_payloads(
    decision: Any,
    generated_at: str,
    ledger: PredictionLedger,
    status: str,
    status_reason: str | None,
    names: dict[str, str],
    tickers: dict[str, str],
    checks: list[FreshnessResult],
    validation: dict[str, Any] | None,
    scenario: dict[str, Any] | None,
    benchmarks: dict[str, Any] | None,
) -> None:
    freshness_days = {
        c.name: c.age_days for c in checks if c.age_days is not None
    }
    write_report_json(
        rotation_report_dict(
            decision,
            generated_at=generated_at,
            ledger=ledger,
            status=status,
            status_reason=status_reason,
            names=names,
            tickers=tickers,
            freshness_days=freshness_days,
            horizons=DEFAULT_HORIZONS,
        ),
        REPORT_PATH,
    )
    write_report_json(
        rotation_model_dict(
            generated_at=generated_at,
            decision=decision,
            ledger=ledger,
            status=status,
            status_reason=status_reason,
            validation=validation,
            scenario=scenario,
            benchmarks=benchmarks,
            freshness=_freshness_payload(checks),
            horizons=DEFAULT_HORIZONS,
        ),
        MODEL_PATH,
    )
    logger.info("Wrote %s and %s", REPORT_PATH, MODEL_PATH)


if __name__ == "__main__":
    main()
