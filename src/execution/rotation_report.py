# pyright: strict, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Dashboard payloads for the weekly ETF rotation (WP4, contract for WP5).

Two JSON files, two questions:

- ``ranking_report.json`` — *what does the rule say this week?* The ranked
  universe, the holdings, the observed state behind each name.
- ``ranking_model.json`` — *why should anyone believe it?* The honest answer is
  "they should not, yet", and this payload carries that answer as data: the
  ADR-034 verdict, the adoption bar it failed, the absence of a calibration, and
  the live scoreboard of resolved ledger rows.

Every payload declares ``predictive: false`` at the top level and repeats the
notice in ``non_predictive_notice``. That is deliberate duplication: a renderer
that reads only one of the two still cannot present the ranking as a forecast,
and a payload that loses the caveat during a refactor fails its schema test.

The forecast fields (``probability_outperform``, ``expected_excess_return``,
``expected_volatility``) appear in every item and are always ``null`` under this
rule (ADR-036). They stay in the contract so WP5 can build one renderer and so
a future calibrated model does not reshape the payload — but ``null`` is the
only value the non-predictive path can produce, and the tests hold that line.

Pure functions over already-computed state; no network, no filesystem reads.
"""

from __future__ import annotations

from typing import Any, cast

import pandas as pd

from src.backtest.benchmark import buy_and_hold_equity
from src.execution.etf_rotation import (
    BENCHMARK_SYMBOL,
    NON_PREDICTIVE_REASON,
    RULE_DESCRIPTION,
    RotationDecision,
)
from src.execution.prediction_ledger import PredictionLedger

REPORT_TITLE = "Rotazione ETF settoriali — regola dichiaratamente non predittiva"
MODEL_TITLE = "Modello di ranking ETF — stato della validazione"

DISCLAIMER = (
    "Portafoglio VIRTUALE (paper trading): nessun denaro reale, nessuna "
    "raccomandazione di acquisto o vendita. La regola di selezione è stata "
    "misurata come NON predittiva (ADR-034): serve a validare l'infrastruttura "
    "di misura, non a generare rendimento."
)
NON_PREDICTIVE_NOTICE = (
    "⚠️ Questa classifica NON è una previsione. La barra di adozione di WP3 non è "
    "stata superata: il momentum relativo a 60 sedute è risultato indistinguibile "
    "dal caso fuori campione (IC 0,0010, t = 0,08) e nessuna probabilità calibrata "
    "è disponibile. I campi di probabilità restano vuoti apposta (ADR-036)."
)
STALE_NOTICE = (
    "Dati non aggiornati: nessun nuovo ranking è stato emesso e il portafoglio "
    "non è stato ribilanciato."
)

STATUS_OK = "ok"
STATUS_STALE = "stale"


def _round(value: float | None, ndigits: int) -> float | None:
    return None if value is None or pd.isna(value) else round(float(value), ndigits)


def rotation_report_dict(
    decision: RotationDecision | None,
    generated_at: str,
    ledger: PredictionLedger,
    status: str = STATUS_OK,
    status_reason: str | None = None,
    names: dict[str, str] | None = None,
    tickers: dict[str, str] | None = None,
    freshness_days: dict[str, float] | None = None,
    horizons: tuple[int, ...] = (20, 60),
    max_past: int = 60,
) -> dict[str, Any]:
    """The "Opportunità" payload: this week's cross-section plus past outcomes.

    ``decision`` may be ``None`` when the run was aborted by the freshness
    guard: the payload then carries ``status: "stale"`` and an empty item list,
    which the dashboard must render as an explicit empty state rather than as
    "no opportunities today".
    """
    names = names or {}
    tickers = tickers or {}
    freshness_days = freshness_days or {}

    items: list[dict[str, Any]] = []
    if decision is not None:
        for asset in decision.ranked:
            items.append(
                {
                    "rank": asset.rank,
                    "asset": asset.symbol,
                    "ticker": tickers.get(asset.symbol),
                    "name": names.get(asset.symbol, asset.symbol),
                    "selected": asset.selected,
                    "target_weight": _round(asset.target_weight, 4),
                    "selection_score": _round(asset.score, 6),
                    "selection_rank_pct": _round(asset.rank_pct, 4),
                    "realized_vol_60": _round(asset.realized_vol_60, 4),
                    "close": _round(asset.close, 4),
                    "regime": decision.regime,
                    # Always null under the non-predictive rule (ADR-036).
                    "probability_outperform": None,
                    "expected_excess_return": None,
                    "expected_volatility": None,
                    "confidence": "not_applicable",
                    "top_factors": [
                        {"name": "rel_ret_60", "direction": "positive" if asset.score > 0 else "negative"}
                    ],
                    "freshness_days": _round(freshness_days.get(asset.symbol), 2),
                }
            )

    return {
        "generated_at": generated_at,
        "title": REPORT_TITLE,
        "status": status,
        "status_reason": status_reason if status != STATUS_OK else None,
        "stale_notice": STALE_NOTICE if status != STATUS_OK else None,
        "predictive": False,
        "rule": decision.rule if decision is not None else None,
        "rule_version": decision.rule_version if decision is not None else None,
        "rule_description": RULE_DESCRIPTION,
        "non_predictive_notice": NON_PREDICTIVE_NOTICE,
        "non_predictive_reason": NON_PREDICTIVE_REASON,
        "confidence_threshold": None,
        "confidence_threshold_note": (
            "Soglia D7 disattivata: richiedeva una probabilità calibrata, che non "
            "esiste sotto questa regola (ADR-036)."
        ),
        "disclaimer": DISCLAIMER,
        "as_of": str(decision.as_of) if decision is not None else None,
        "benchmark": BENCHMARK_SYMBOL,
        "regime": decision.regime if decision is not None else "unknown",
        "horizons": list(horizons),
        "universe_size": len(decision.ranked) if decision is not None else 0,
        "not_scoreable": list(decision.excluded) if decision is not None else [],
        "cash_weight": _round(decision.cash_weight, 4) if decision is not None else None,
        "items": items,
        "past_predictions": past_predictions(ledger, limit=max_past),
    }


def past_predictions(ledger: PredictionLedger, limit: int = 60) -> list[dict[str, Any]]:
    """Resolved ledger rows, most recent first — the forward track record.

    Only rows with an ``outcome`` appear: an unresolved row says nothing yet,
    and showing it next to resolved ones invites reading a pending bet as a
    result.
    """
    resolved = [r for r in ledger.raw_records() if r.get("outcome")]
    resolved.sort(key=lambda r: str(r.get("emitted_at", "")), reverse=True)
    out: list[dict[str, Any]] = []
    for record in resolved[:limit]:
        outcome = cast("dict[str, Any]", record["outcome"])
        out.append(
            {
                "emitted_at": record.get("emitted_at"),
                "asset": record.get("asset"),
                "horizon_days": record.get("horizon_days"),
                "selected": record.get("selected"),
                "selection_rank": record.get("selection_rank"),
                "excess_return": _round(cast("float", outcome.get("excess_return")), 6),
                "outperformed": outcome.get("outperformed"),
                "resolved_price_date": outcome.get("resolved_price_date"),
            }
        )
    return out


def ledger_scoreboard(ledger: PredictionLedger, horizon: int = 20) -> dict[str, Any]:
    """Live tally of the resolved rows at one horizon, selections vs the rest.

    Reported without a verdict attached. With a rule already measured as
    indistinguishable from chance, a hit rate above 0,5 over a handful of weeks
    is what luck looks like — the payload gives the counts and lets the reader
    keep that in mind, and ``n_resolved`` is there precisely so a small sample
    cannot hide.
    """
    rows = [
        r
        for r in ledger.raw_records()
        if r.get("outcome") and int(r.get("horizon_days", 0)) == horizon
    ]
    selected = [r for r in rows if bool(r.get("selected"))]

    def _stats(block: list[dict[str, Any]]) -> dict[str, Any]:
        if not block:
            return {"n": 0, "hit_rate": None, "mean_excess": None}
        excesses = [float(cast("dict[str, Any]", r["outcome"])["excess_return"]) for r in block]
        hits = [
            1.0 if bool(cast("dict[str, Any]", r["outcome"])["outperformed"]) else 0.0
            for r in block
        ]
        return {
            "n": len(block),
            "hit_rate": _round(sum(hits) / len(hits), 4),
            "mean_excess": _round(sum(excesses) / len(excesses), 6),
        }

    return {
        "horizon_days": horizon,
        "n_resolved": len(rows),
        "n_pending": sum(
            1
            for r in ledger.raw_records()
            if not r.get("outcome") and int(r.get("horizon_days", 0)) == horizon
        ),
        "selected": _stats(selected),
        "universe": _stats(rows),
        "caveat": (
            "Conteggi grezzi, non un verdetto: la regola è già stata misurata come "
            "indistinguibile dal caso, quindi un hit rate sopra 0,5 su poche "
            "settimane è compatibile con la fortuna."
        ),
    }


def benchmark_summary(
    closes: dict[str, pd.Series],
    benchmark_close: pd.Series,
    start: pd.Timestamp | None,
    initial_capital: float,
) -> dict[str, Any]:
    """SPY buy-and-hold and equal-weight-universe equity over the live window.

    Both are computed on the *same* window as the paper scenario, from ``start``
    onwards: a benchmark measured over a different period is not a benchmark.
    ``None`` values mean the window is too short to say anything, which is the
    truthful answer in the first weeks of a forward run.
    """
    if start is None:
        return {"start": None, "spy_buy_and_hold": None, "equal_weight": None}

    def _final(series: pd.Series) -> dict[str, Any] | None:
        window = series.dropna().sort_index()
        window = window.loc[window.index >= start]
        if len(window) < 2:
            return None
        curve = buy_and_hold_equity(window, initial_capital=initial_capital)
        final = float(cast("float", curve.iloc[-1]))
        return {
            "equity": round(final, 2),
            "return_pct": round((final / initial_capital - 1.0) * 100.0, 2),
            "points": len(curve),
        }

    equal_weight_series = _equal_weight_index(closes, start)
    return {
        "start": str(start),
        "initial_capital": initial_capital,
        "spy_buy_and_hold": _final(benchmark_close),
        "equal_weight": _final(equal_weight_series) if equal_weight_series is not None else None,
    }


def _equal_weight_index(
    closes: dict[str, pd.Series], start: pd.Timestamp
) -> pd.Series | None:
    """Equal-weight, rebalanced-daily index of the universe from ``start``.

    Built from the mean of each symbol's price *relative* to its own first
    observation in the window, so symbols with different price levels get equal
    weight rather than the most expensive one dominating.
    """
    normalised: list[pd.Series] = []
    for series in closes.values():
        window = series.dropna().sort_index()
        window = window.loc[window.index >= start]
        if len(window) < 2:
            continue
        base = float(cast("float", window.iloc[0]))
        if base <= 0:
            continue
        normalised.append(window / base)
    if not normalised:
        return None
    frame = pd.concat(normalised, axis=1)
    return frame.mean(axis=1, skipna=True)


def rotation_model_dict(
    generated_at: str,
    decision: RotationDecision | None,
    ledger: PredictionLedger,
    status: str = STATUS_OK,
    status_reason: str | None = None,
    validation: dict[str, Any] | None = None,
    scenario: dict[str, Any] | None = None,
    benchmarks: dict[str, Any] | None = None,
    freshness: list[dict[str, Any]] | None = None,
    horizons: tuple[int, ...] = (20, 60),
) -> dict[str, Any]:
    """The "Modello" payload: what was validated, what failed, what is running.

    ``validation`` is the relevant slice of ``public/data/ranking_backtest.json``
    (WP3) — carried here so the dashboard can show the verdict next to the live
    portfolio instead of asking the reader to correlate two tabs.
    """
    return {
        "generated_at": generated_at,
        "title": MODEL_TITLE,
        "status": status,
        "status_reason": status_reason if status != STATUS_OK else None,
        "predictive": False,
        "model_adopted": None,
        "rule": decision.rule if decision is not None else None,
        "rule_version": decision.rule_version if decision is not None else None,
        "rule_description": RULE_DESCRIPTION,
        "dataset_version": decision.dataset_version if decision is not None else None,
        "non_predictive_notice": NON_PREDICTIVE_NOTICE,
        "non_predictive_reason": NON_PREDICTIVE_REASON,
        "adoption_bar": {
            "passed": False,
            "reference": "ADR-034",
            "requirement": (
                "IC Spearman OOS ≥ 0,03 E spread top-bottom netto costi positivo in "
                "entrambe le metà OOS E Brier ≤ climatologia."
            ),
            "outcome": (
                "Non superata: solo la prima condizione è soddisfatta. Il segno del "
                "TMB non regge nella seconda metà OOS e il Brier di ogni modello è "
                "peggiore della climatologia (0,2501)."
            ),
        },
        "calibration": {
            "available": False,
            "method": "isotonic (WP3)",
            "reason": (
                "La calibrazione isotonic, fit sul solo train, non trasferisce fuori "
                "campione: nella banda 0,90-1,00 la logistica predice 0,974 e si "
                "realizza 0,461. Nessuna probabilità viene pubblicata."
            ),
        },
        "confidence_threshold": None,
        "confidence_threshold_note": (
            "D7 disattivata (ADR-036): una soglia su una probabilità che non esiste "
            "sarebbe un filtro finto."
        ),
        "validation": validation,
        "scenario": scenario,
        "benchmarks": benchmarks,
        "freshness": freshness or [],
        "scoreboard": [ledger_scoreboard(ledger, horizon=h) for h in horizons],
        "ledger": {
            "path": str(ledger.path),
            "rows": len(ledger.raw_records()),
        },
        "disclaimer": DISCLAIMER,
    }
