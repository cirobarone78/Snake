# pyright: strict, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Run the pre-registered ranking validation and write its report (WP3, ADR-034).

Loads the WP2 panel, runs every model through the walk-forward protocol frozen in
ADR-034, and writes the verdict on H1/H2/H3 — whatever it is. The report has a
mandatory "what did NOT work" section: in this project a negative result is the
deliverable, not a failure to hide.

Run:  uv run python -m src.ingestion.tier1.ranking_backtest_cli

Outputs:
  docs/REPORT_RANKING.md          human-readable verdict + tables
  public/data/ranking_backtest.json   the same numbers for the WP5 dashboard

Requires ``data/processed/etf_panel.parquet`` (build it with
``python -m src.ingestion.tier1.build_etf_dataset``). Both steps need Yahoo, so
both run in CI rather than in the sandbox.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, cast

import pandas as pd

from src.backtest.ranking_backtest import (
    SESSIONS_PER_WEEK,
    concat_predictions,
    embargo_gap_days,
    fold_summary,
    realised_excess,
    split_halves,
    walk_forward_predict,
)
from src.backtest.ranking_metrics import (
    hit_rate_outperform,
    information_coefficient,
    summarize_spread,
    top_minus_bottom,
)
from src.execution.paper_broker import default_cost_model
from src.features.etf_dataset import FEATURE_COLUMNS
from src.features.report_json import iso_timestamp, write_report_json
from src.models.calibration import (
    brier_score,
    brier_skill_score,
    expected_calibration_error,
    reliability_table,
)
from src.models.etf_ranker import (
    ClimatologyBaseline,
    LogisticRanker,
    MomentumRanker,
    RandomRanker,
    RankerModel,
    RidgeRanker,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

PANEL_PATH = Path("data/processed/etf_panel.parquet")
REPORT_PATH = Path("docs/REPORT_RANKING.md")
JSON_PATH = Path("public/data/ranking_backtest.json")

# Walk-forward geometry, in weekly samples (decision D5). 3 years of weekly
# cross-sections to fit, 1 year out-of-sample per fold.
TRAIN_WEEKS = 156
TEST_WEEKS = 52

# ADR-034 adoption bar.
IC_BAR = 0.03


def build_models(features: list[str]) -> list[RankerModel]:
    """The pre-registered model set: two controls, one baseline, two candidates."""
    return [
        MomentumRanker(column="rel_ret_60"),
        LogisticRanker(features=features, C=0.1, seed=0),
        RidgeRanker(features=features, alpha=10.0),
        RandomRanker(seed=0),
        ClimatologyBaseline(),
    ]


def evaluate_model(
    panel: pd.DataFrame, model: RankerModel, horizon: int, excess_column: str
) -> dict[str, Any]:
    """Full walk-forward evaluation of one model at one horizon."""
    target = f"outperform_{horizon}"
    embargo_weeks = max(1, round(horizon / SESSIONS_PER_WEEK))
    folds = walk_forward_predict(
        panel, model, target=target,
        train_weeks=TRAIN_WEEKS, test_weeks=TEST_WEEKS, embargo_weeks=embargo_weeks,
    )
    preds = concat_predictions(folds)
    if preds.empty:
        return {"model": model.name, "horizon": horizon, "n_predictions": 0}

    preds = preds.copy()
    preds["excess"] = realised_excess(panel, preds, excess_column)
    costs = default_cost_model()

    def _block(block: pd.DataFrame) -> dict[str, Any]:
        if block.empty:
            return {}
        dates = cast("pd.Series", block["date"])
        score = cast("pd.Series", block["score"])
        rank = cast("pd.Series", block["rank"])
        excess = cast("pd.Series", block["excess"])
        proba = cast("pd.Series", block["proba"])
        target = cast("pd.Series", block["target"])
        ic = information_coefficient(dates, score, excess)
        spread = top_minus_bottom(dates, rank, excess, q=0.2, costs=costs)
        gross = summarize_spread(spread, "gross")
        net = summarize_spread(spread, "net")
        base_rate = float(target.dropna().mean())
        return {
            "n": len(block),
            "ic_spearman": ic["spearman"], "ic_pearson": ic["pearson"],
            "ic_t": ic["spearman_t"], "n_dates": ic["n_dates"],
            "brier": brier_score(proba, target),
            "brier_skill_vs_climatology": brier_skill_score(
                proba, target, reference=base_rate * (1.0 - base_rate)
            ),
            "ece": expected_calibration_error(proba, target),
            "hit_rate": hit_rate_outperform(proba, target),
            "tmb_gross_mean": gross["mean"], "tmb_net_mean": net["mean"],
            "tmb_net_t": net["t"], "tmb_positive_share": net["positive_share"],
            "base_rate": base_rate,
        }

    first, second = split_halves(preds)
    return {
        "model": model.name,
        "horizon": horizon,
        "n_predictions": len(preds),
        "n_folds": len(folds),
        "embargo_weeks": embargo_weeks,
        "embargo_gap_days": embargo_gap_days(folds),
        "overall": _block(preds),
        "first_half": _block(first),
        "second_half": _block(second),
        "reliability": reliability_table(
            cast("pd.Series", preds["proba"]), cast("pd.Series", preds["target"])
        ).to_dict("records"),
        "folds": fold_summary(folds).to_dict("records"),
    }


def verdicts(results: list[dict[str, Any]], horizon: int) -> dict[str, Any]:
    """Judge H1/H2/H3 and the adoption bar against the pre-registered thresholds."""
    by_name = {r["model"]: r for r in results if r["horizon"] == horizon and r.get("overall")}
    mom = by_name.get("momentum", {})
    log = by_name.get("logistic", {})

    mom_ic = float(mom.get("overall", {}).get("ic_spearman", float("nan")))
    h1 = bool(mom_ic > 0.0)

    log_brier = float(log.get("overall", {}).get("brier", float("nan")))
    mom_brier = float(mom.get("overall", {}).get("brier", float("nan")))
    h2 = bool(log_brier < mom_brier)

    # H3 is judged on the best candidate by OOS IC, in BOTH halves separately.
    candidates = [by_name[n] for n in ("momentum", "logistic", "ridge") if n in by_name]
    best = max(
        candidates,
        key=lambda r: (
            float(r["overall"]["ic_spearman"])
            if pd.notna(r["overall"]["ic_spearman"]) else float("-inf")
        ),
        default={},
    )
    h3 = False
    best_name = str(best.get("model", "n/a"))
    if best:
        f = float(best.get("first_half", {}).get("tmb_net_mean", float("nan")))
        s = float(best.get("second_half", {}).get("tmb_net_mean", float("nan")))
        h3 = bool(pd.notna(f) and pd.notna(s) and f > 0.0 and s > 0.0)

    best_ic = float(best.get("overall", {}).get("ic_spearman", float("nan"))) if best else float("nan")
    best_brier = float(best.get("overall", {}).get("brier", float("nan"))) if best else float("nan")
    clim_brier = float(
        by_name.get("climatology", {}).get("overall", {}).get("brier", float("nan"))
    )
    bar = bool(
        pd.notna(best_ic) and best_ic >= IC_BAR
        and h3
        and pd.notna(best_brier) and pd.notna(clim_brier) and best_brier <= clim_brier
    )
    return {
        "horizon": horizon,
        "H1_momentum_ic_positive": h1, "H1_value": mom_ic,
        "H2_logistic_beats_momentum_brier": h2,
        "H2_logistic_brier": log_brier, "H2_momentum_brier": mom_brier,
        "H3_tmb_net_positive_both_halves": h3, "H3_best_model": best_name,
        "adoption_bar_passed": bar,
        "best_ic": best_ic, "best_brier": best_brier, "climatology_brier": clim_brier,
    }


def _fmt(x: object, nd: int = 4) -> str:
    if isinstance(x, (int, float)) and pd.notna(x):
        return f"{float(x):.{nd}f}"
    return "n/d"


def _yes(flag: object) -> str:
    return "✅ **vera**" if bool(flag) else "❌ **falsa**"


def format_report(
    results: list[dict[str, Any]], all_verdicts: list[dict[str, Any]],
    horizons: list[int], generated_at: str, panel_rows: int, features: list[str],
) -> str:
    """The report a human reads. Italian, per CLAUDE.md."""
    v20 = next((v for v in all_verdicts if v["horizon"] == 20), {})
    lines: list[str] = [
        "# Report — Ranking ETF probabilistico (WP3)",
        "",
        "> Esito della validazione **pre-registrata** in ADR-034. Le ipotesi e le",
        "> soglie sono state committate *prima* di questo run: il timestamp git lo",
        "> dimostra. Nessuna soglia è stata spostata dopo aver visto i numeri.",
        "",
        f"**Generato**: {generated_at} · **Panel**: {panel_rows} righe · "
        f"**Feature**: {len(features)} · **Orizzonte primario**: 20 sedute",
        "",
        "## Verdetto",
        "",
    ]
    if v20:
        lines += [
            f"- **H1** (IC Spearman del momentum 60g > 0 a 20 sedute): {_yes(v20['H1_momentum_ic_positive'])} "
            f"— IC = `{_fmt(v20['H1_value'])}`",
            f"- **H2** (la logistica batte il momentum in Brier): {_yes(v20['H2_logistic_beats_momentum_brier'])} "
            f"— logistica `{_fmt(v20['H2_logistic_brier'])}` vs momentum `{_fmt(v20['H2_momentum_brier'])}`",
            f"- **H3** (spread top-bottom netto costi > 0 in *entrambe* le metà OOS): "
            f"{_yes(v20['H3_tmb_net_positive_both_halves'])} — modello migliore: `{v20['H3_best_model']}`",
            "",
            f"### Barra di adozione: {'✅ **SUPERATA**' if v20['adoption_bar_passed'] else '❌ **NON superata**'}",
            "",
            f"Richiede IC ≥ {IC_BAR} **e** H3 vera **e** Brier ≤ climatologia. "
            f"Misurato: IC `{_fmt(v20['best_ic'])}`, Brier `{_fmt(v20['best_brier'])}` "
            f"vs climatologia `{_fmt(v20['climatology_brier'])}`.",
            "",
        ]
        if not v20["adoption_bar_passed"]:
            lines += [
                "**Conseguenza operativa** (già scritta in ADR-034 prima del run): WP4",
                "procede con il **momentum semplice** come regola dichiaratamente",
                "*non predittiva*. Il ledger delle previsioni e l'infrastruttura di",
                "portafoglio valgono comunque — servono a misurare, non a guadagnare.",
                "",
            ]
    for h in horizons:
        lines += [f"## Orizzonte {h} sedute", "",
                  "| Modello | n | IC Spearman | IC t | Brier | Skill vs clim. | ECE | Hit rate | TMB lordo | TMB netto | TMB > 0 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in results:
            if r["horizon"] != h or not r.get("overall"):
                continue
            o = r["overall"]
            lines.append(
                f"| `{r['model']}` | {o['n']} | {_fmt(o['ic_spearman'])} | {_fmt(o['ic_t'], 2)} | "
                f"{_fmt(o['brier'])} | {_fmt(o['brier_skill_vs_climatology'])} | {_fmt(o['ece'])} | "
                f"{_fmt(o['hit_rate'], 3)} | {_fmt(o['tmb_gross_mean'])} | {_fmt(o['tmb_net_mean'])} | "
                f"{_fmt(o['tmb_positive_share'], 2)} |"
            )
        lines += ["", "### Le due metà OOS (H3 richiede il segno in entrambe)", "",
                  "| Modello | IC 1ª metà | IC 2ª metà | TMB netto 1ª | TMB netto 2ª |",
                  "|---|---:|---:|---:|---:|"]
        for r in results:
            if r["horizon"] != h or not r.get("overall"):
                continue
            a, b = r.get("first_half", {}), r.get("second_half", {})
            lines.append(
                f"| `{r['model']}` | {_fmt(a.get('ic_spearman'))} | {_fmt(b.get('ic_spearman'))} | "
                f"{_fmt(a.get('tmb_net_mean'))} | {_fmt(b.get('tmb_net_mean'))} |"
            )
        lines.append("")

    primary = next((r for r in results if r["horizon"] == 20 and r["model"] == "logistic"), None)
    if primary and primary.get("reliability"):
        lines += ["## Reliability table — logistica, 20 sedute", "",
                  "Se le probabilità fossero calibrate, `osservata` ≈ `predetta` in ogni banda.", "",
                  "| Banda | n | Predetta | Osservata | Scarto |", "|---|---:|---:|---:|---:|"]
        for row in cast("list[dict[str, Any]]", primary["reliability"]):
            lines.append(
                f"| {_fmt(row['lower'], 2)}-{_fmt(row['upper'], 2)} | {row['n']} | "
                f"{_fmt(row['mean_predicted'], 3)} | {_fmt(row['observed_frequency'], 3)} | "
                f"{_fmt(row['gap'], 3)} |"
            )
        lines.append("")

    lines += [
        "## Cosa NON ha funzionato",
        "",
        "Sezione obbligatoria (`CLAUDE.md`: gli esperimenti falliti vanno tracciati).",
        "",
    ]
    for h in horizons:
        v = next((x for x in all_verdicts if x["horizon"] == h), None)
        if not v:
            continue
        if not v["H1_momentum_ic_positive"]:
            lines.append(f"- **{h}g — momentum relativo 60g**: IC OOS `{_fmt(v['H1_value'])}`, non positivo. "
                         "Coerente con il risultato già noto sui 20 ETF settoriali (STATUS.md): "
                         "inseguire i settori forti non paga.")
        if not v["H2_logistic_beats_momentum_brier"]:
            lines.append(f"- **{h}g — logistica sulle feature WP2**: Brier `{_fmt(v['H2_logistic_brier'])}` "
                         f"contro `{_fmt(v['H2_momentum_brier'])}` del momentum: non lo batte. "
                         "19 feature causali non aggiungono potere predittivo rispetto a una regola a costo zero.")
        if not v["H3_tmb_net_positive_both_halves"]:
            lines.append(f"- **{h}g — spread top-bottom**: non positivo in entrambe le metà OOS "
                         "al netto dei costi. Un segno che regge solo in una metà è un regime, non un edge.")
    lines += [
        "",
        "### Varianti provate e scartate",
        "",
        "- **Ridge sull'excess return** invece della logistica sul segno: stessa famiglia",
        "  di feature, target continuo anziché binario. In tabella come `ridge`.",
        "- **Senza calibrazione isotonic**: la calibrazione non cambia l'ordinamento",
        "  (è monotona), quindi non cambia l'IC; l'effetto è solo sul Brier.",
        "- Nessun tuning iterativo degli iperparametri sullo stesso test set: vietato dal",
        "  piano (§WP3 «non fare»), ed è il modo classico di fabbricare un edge inesistente.",
        "",
        "## Protocollo",
        "",
        f"- Walk-forward su **date** (mai una cross-section spezzata a metà): train {TRAIN_WEEKS} "
        f"settimane, test {TEST_WEEKS}, campionamento **settimanale al lunedì** (D5).",
        "- **Embargo** = orizzonte: le ultime righe di train, il cui target si realizza dentro",
        "  il test, vengono scartate. Senza, il fold è contaminato.",
        "- **Calibrazione isotonic fit solo sul train** di ogni fold.",
        "- **Costi**: `default_cost_model()`, round trip pieno su entrambe le gambe — carico",
        "  pessimistico di proposito, rende H3 più difficile da passare, non più facile.",
        "- **Controlli negativi**: `random` (seed fisso) e `climatology` (frequenza del train).",
        "",
        "> ⚠️ Le date consecutive condividono finestre forward sovrapposte: le statistiche t",
        "> riportate sono indicative, non inferenziali — il campione effettivo è più piccolo",
        "> di `n_dates`.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the pre-registered ETF ranking validation.")
    parser.add_argument("--panel", type=Path, default=PANEL_PATH)
    parser.add_argument("--horizons", type=int, nargs="+", default=[20, 60])
    args = parser.parse_args()

    panel_path = cast("Path", args.panel)
    if not panel_path.exists():
        raise SystemExit(
            f"Panel not found at {panel_path}. Build it first:\n"
            "  uv run python -m src.ingestion.tier1.build_etf_dataset"
        )
    panel = pd.read_parquet(panel_path)
    logger.info("Loaded panel: %d rows x %d cols", len(panel), panel.shape[1])

    from src.backtest.ranking_backtest import weekly_sample

    weekly = weekly_sample(panel)
    logger.info(
        "Weekly (Monday) sample: %d rows, %d dates",
        len(weekly), cast("pd.Series", weekly["date"]).nunique(),
    )

    features = [c for c in FEATURE_COLUMNS if c in weekly.columns]
    horizons = cast("list[int]", args.horizons)
    results: list[dict[str, Any]] = []
    for horizon in horizons:
        for model in build_models(features):
            logger.info("Evaluating %s at horizon %d...", model.name, horizon)
            results.append(
                evaluate_model(weekly, model, horizon, excess_column=f"excess_ret_{horizon}")
            )
    all_verdicts = [verdicts(results, h) for h in horizons]

    generated_at = iso_timestamp(None)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        format_report(results, all_verdicts, horizons, generated_at, len(panel), features),
        encoding="utf-8",
    )
    write_report_json(
        {
            "generated_at": generated_at,
            "panel_rows": len(panel),
            "weekly_rows": len(weekly),
            "features": features,
            "train_weeks": TRAIN_WEEKS, "test_weeks": TEST_WEEKS, "ic_bar": IC_BAR,
            "verdicts": all_verdicts,
            "results": results,
        },
        JSON_PATH,
    )
    logger.info("Wrote %s and %s", REPORT_PATH, JSON_PATH)
    for v in all_verdicts:
        logger.info(
            "VERDICT h=%d: H1=%s H2=%s H3=%s bar=%s (IC=%.4f best_brier=%.4f clim=%.4f)",
            v["horizon"], v["H1_momentum_ic_positive"], v["H2_logistic_beats_momentum_brier"],
            v["H3_tmb_net_positive_both_halves"], v["adoption_bar_passed"],
            v["best_ic"], v["best_brier"], v["climatology_brier"],
        )


if __name__ == "__main__":
    main()
