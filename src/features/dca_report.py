"""Reports for the accumulation plan: the Markdown briefing and the JSON twin.

Two faces of the same content, built from the same structured frames (no Markdown
parsing anywhere): ``format_report`` for ``REPORT_DCA.md`` and the CLI,
``dca_report_dict`` for ``public/data/dca_report.json`` and the dashboard tab.

The wording carries a specific burden. ``dca_backtest`` established that the
sleeve rule earns **no** return edge — it lands at the 54th percentile against
200 seeds of random picking, which is the statistical signature of a coin flip.
What it does do, consistently and in the out-of-sample half, is keep the sleeve
near its target allocation. A report that let a reader infer "the app tells me
what will go up" would be worse than no report, so the validated numbers travel
*with* the recommendation instead of living in a document nobody opens.

Italian text (CLAUDE.md: docs and user-facing copy in Italian, code in English).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pandas as pd

from src.features.report_json import iso_timestamp, write_report_json

DISCLAIMER = (
    "Contenuto educativo, non consulenza finanziaria. Nessuna previsione: "
    "la scelta proposta serve a rispettare l'allocazione decisa, non a indovinare "
    "quale asset salirà."
)

# Results of the validation study in ``dca_backtest``, recorded here so the
# recommendation can never be read without them. Recomputable at any time with
# `dca_cli --validate`; see ADR-030 for the full write-up.
EVIDENCE: dict[str, Any] = {
    "window": "2020-04-10 → 2026-08-24",
    "n_purchases": 77,
    "fee_pct": 0.5,
    "vs_split_full": 1.013,
    "vs_split_first_half": 1.192,
    "vs_split_second_half": 0.907,
    "random_percentile": 54.5,
    "weight_drift_pp_rule": 80.2,
    "weight_drift_pp_split": 101.6,
    "weight_drift_pp_rule_oos": 5.33,
    "weight_drift_pp_split_oos": 30.48,
    "momentum_random_percentile": 40.5,
}

REASON_IT: dict[str, str] = {
    "underweight_vs_target": "è il più sotto peso rispetto al target",
    "mildly_underweight": "è leggermente sotto peso rispetto al target",
    "cheapest_in_range": "è il più basso nel proprio intervallo recente",
    "best_blend": "ha il punteggio più alto sul mix dei criteri",
    "not_selected": "non selezionato questo mese",
}

REJECT_IT: dict[str, str] = {
    "already_held": "già in portafoglio",
    "stablecoin_or_pegged": "stablecoin o token ancorato",
    "wrapped_or_derivative": "wrapped/derivato di un altro asset",
    "market_cap_below_floor": "capitalizzazione sotto la soglia",
    "illiquid": "volume troppo basso rispetto alla capitalizzazione",
    "turnover_anomaly": "volume anomalo rispetto alla capitalizzazione",
}

FLAG_IT: dict[str, str] = {
    "meme": "meme coin",
    "exchange_token": "token di exchange",
    "privacy": "privacy",
    "rwa": "real world assets",
    "ai": "AI",
    "stablecoin_adjacent": "area stablecoin",
}

CAVEATS: tuple[str, ...] = (
    "La regola sulla quota satellite NON ha battuto la divisione in parti uguali: "
    "sul campione completo è al 54° percentile contro 200 estrazioni casuali. "
    "Serve a mantenere l'allocazione, non a guadagnare di più.",
    "Comprare l'asset più forte del momento ('momentum') è risultato peggiore del "
    "caso (40° percentile): è l'istinto più comune ed è quello che ha reso meno.",
    "Le candidate sono filtrate su criteri meccanici (dimensione, liquidità, età "
    "minima dimostrabile). Nessun giudizio su tecnologia, team o prospettive.",
    "Survivorship bias: la classifica di oggi contiene solo chi è sopravvissuto. "
    "Gran parte della top 100 del 2018 non esiste più, e quelle monete non "
    "compaiono in questi dati.",
    "Su orizzonti di 5-10 anni le singole altcoin hanno un tasso di mortalità "
    "storicamente alto. La soglia di capitalizzazione è un indizio di solidità, "
    "non una garanzia.",
)


def _fmt_mcap(value: object) -> str:
    """Compact market-cap string ($1.2B / $340M), ``n/a`` when missing."""
    if value is None or pd.isna(cast("float", value)):
        return "n/a"
    v = float(cast("float", value))
    if v >= 1e9:
        return f"${v / 1e9:.1f}B"
    return f"${v / 1e6:.0f}M"


def _num(value: object) -> float | None:
    if value is None or pd.isna(cast("float", value)):
        return None
    return float(cast("float", value))


def _round(value: float | None, ndigits: int) -> float | None:
    return None if value is None else round(value, ndigits)


def _pct(value: object, digits: int = 1) -> str:
    n = _num(value)
    return "n/a" if n is None else f"{n:.{digits}f}%"


def _flags_it(raw: object) -> str:
    if not isinstance(raw, str) or not raw:
        return ""
    return ", ".join(FLAG_IT.get(f.strip(), f.strip()) for f in raw.split(","))


ESTIMATED_NOTE = (
    "I pesi qui sotto sono **stimati** replicando il piano dalla data di inizio: "
    "il sistema non conosce le quantità realmente possedute. Inserendole in "
    "`config/dca_plan.yaml` (`holdings_units`) lo scarto dal target diventa esatto."
)


def format_report(
    ranked: pd.DataFrame,
    candidates: pd.DataFrame | None = None,
    rejected: pd.DataFrame | None = None,
    sleeve_eur: float = 10.0,
    holdings_estimated: bool = False,
) -> str:
    """Markdown briefing: this month's sleeve pick, the evidence, the candidates.

    ``ranked`` comes from ``dca_advisor.advise``; ``candidates``/``rejected`` from
    ``dca_candidates.screen_candidates``. ``holdings_estimated`` prints the note
    that the weights are a replay rather than a real position — the pick reads as
    authoritative otherwise, and it is not. Pure function — no I/O, no network.
    """
    lines: list[str] = ["# Piano di accumulo", ""]

    if ranked.empty:
        lines += ["Nessun dato disponibile per la quota satellite.", ""]
    else:
        top = ranked.iloc[0]
        reason = REASON_IT.get(str(top["reason"]), str(top["reason"]))
        lines += [
            f"## Quota da {sleeve_eur:.0f}€: **{top['symbol']}**",
            "",
            f"Motivo: {reason}.",
            "",
        ]
        if holdings_estimated:
            lines += [f"> ⚠️ {ESTIMATED_NOTE}", ""]
        lines += [
            "| # | Asset | Peso ora | Target | Scarto | Posizione nel range | Punteggio |",
            "|---|-------|----------|--------|--------|---------------------|-----------|",
        ]
        for row in ranked.to_dict("records"):
            weight_now = _num(row["weight_now"])
            gap = _num(row["gap_pp"])
            discount = _num(row["discount"])
            lines.append(
                f"| {row['rank']} | {row['symbol']} "
                f"| {'n/a' if weight_now is None else f'{weight_now * 100:.1f}%'} "
                f"| {row['weight_target'] * 100:.1f}% "
                f"| {'n/a' if gap is None else f'{gap:+.1f} pp'} "
                f"| {'n/a' if discount is None else f'{discount * 100:.0f}%'} "
                f"| {row['score']:.3f} |"
            )
        lines += [
            "",
            "### Cosa dice la verifica storica",
            "",
            f"Backtest sui flussi reali ({EVIDENCE['window']}, "
            f"{EVIDENCE['n_purchases']} acquisti, commissioni {EVIDENCE['fee_pct']}%):",
            "",
            f"- **Rendimento: nessun vantaggio.** Rapporto con la divisione in parti "
            f"uguali {EVIDENCE['vs_split_full']:.3f} sul periodo completo, ma "
            f"{EVIDENCE['vs_split_first_half']:.2f} nella prima metà e "
            f"{EVIDENCE['vs_split_second_half']:.2f} nella seconda: si alterna, "
            f"quindi è rumore. Contro 200 estrazioni casuali sta al "
            f"{EVIDENCE['random_percentile']}° percentile.",
            f"- **Allocazione: vantaggio reale e stabile.** Distanza finale dal target "
            f"{EVIDENCE['weight_drift_pp_rule']:.0f} pp contro "
            f"{EVIDENCE['weight_drift_pp_split']:.0f} pp della divisione fissa; nella "
            f"metà out-of-sample {EVIDENCE['weight_drift_pp_rule_oos']:.1f} pp contro "
            f"{EVIDENCE['weight_drift_pp_split_oos']:.1f} pp.",
            f"- **Comprare il più forte è la strategia peggiore**: "
            f"{EVIDENCE['momentum_random_percentile']}° percentile, sotto il caso.",
            "",
        ]

    if candidates is not None and not candidates.empty:
        lines += [
            "## Candidate per un accumulo a lungo termine",
            "",
            "Monete che superano i filtri meccanici. Nessun giudizio di merito: "
            "sono i nomi da studiare, non da comprare al buio.",
            "",
            "| # | Asset | Cap. | Liquidità | Età min. | Da max | Note |",
            "|---|-------|------|-----------|----------|--------|------|",
        ]
        for row in candidates.to_dict("records"):
            turnover = _num(row["turnover"])
            age = _num(row["min_age_years"])
            notes = _flags_it(row.get("flags"))
            if row.get("diversifying"):
                notes = f"{notes}, diversifica" if notes else "diversifica"
            lines.append(
                f"| {row['rank']} | {row['symbol']} ({row['name']}) "
                f"| {_fmt_mcap(row['market_cap'])} "
                f"| {'n/a' if turnover is None else f'{turnover * 100:.1f}%'} "
                f"| {'n/a' if age is None else f'{age:.1f} anni'} "
                f"| {_pct(row['ath_change_pct'], 0)} "
                f"| {notes or '-'} |"
            )
        lines.append("")

    if rejected is not None and not rejected.empty:
        counts = rejected["reason"].value_counts()
        lines += ["### Escluse dal filtro", ""]
        lines += [
            f"- {REJECT_IT.get(str(reason), str(reason))}: {int(count)}"
            for reason, count in counts.items()
        ]
        lines.append("")

    lines += ["## Limiti", ""]
    lines += [f"- {c}" for c in CAVEATS]
    lines += ["", f"> {DISCLAIMER}", ""]
    return "\n".join(lines)


def dca_report_dict(
    ranked: pd.DataFrame,
    candidates: pd.DataFrame | None = None,
    rejected: pd.DataFrame | None = None,
    plan: dict[str, Any] | None = None,
    sleeve_eur: float = 10.0,
    holdings_estimated: bool = False,
    generated_at: pd.Timestamp | str | None = None,
) -> dict[str, Any]:
    """Dashboard JSON payload for the accumulation plan.

    Mirrors the Markdown report field for field. Missing values are ``null``,
    never invented, and ``evidence``/``caveats`` ride along with the pick so the
    dashboard cannot render the recommendation without its own refutation.
    """
    items: list[dict[str, Any]] = []
    for row in ranked.to_dict("records") if not ranked.empty else []:
        items.append(
            {
                "rank": int(row["rank"]),
                "symbol": str(row["symbol"]),
                "price": _round(_num(row["price"]), 6),
                "weight_now": _round(_num(row["weight_now"]), 4),
                "weight_target": _round(_num(row["weight_target"]), 4),
                "gap_pp": _round(_num(row["gap_pp"]), 2),
                "discount": _round(_num(row["discount"]), 4),
                "score": _round(_num(row["score"]), 4),
                "reason": str(row["reason"]),
                "reason_it": REASON_IT.get(str(row["reason"]), str(row["reason"])),
            }
        )

    candidate_items: list[dict[str, Any]] = []
    for row in candidates.to_dict("records") if candidates is not None and not candidates.empty else []:
        flags = row.get("flags")
        candidate_items.append(
            {
                "rank": int(row["rank"]),
                "symbol": str(row["symbol"]),
                "name": str(row["name"]),
                "market_cap": _num(row["market_cap"]),
                "market_cap_rank": _round(_num(row["market_cap_rank"]), 0),
                "turnover": _round(_num(row["turnover"]), 5),
                "min_age_years": _round(_num(row["min_age_years"]), 2),
                "ath_change_pct": _round(_num(row["ath_change_pct"]), 2),
                "categories": str(row["categories"]) if isinstance(row["categories"], str) else None,
                "flags": str(flags) if isinstance(flags, str) else None,
                "flags_it": _flags_it(flags) or None,
                "diversifying": bool(row["diversifying"]),
                "score": _round(_num(row["score"]), 4),
            }
        )

    rejected_summary: dict[str, int] = {}
    if rejected is not None and not rejected.empty:
        rejected_summary = {
            str(reason): int(count) for reason, count in rejected["reason"].value_counts().items()
        }

    return {
        "generated_at": iso_timestamp(generated_at),
        "title": "Piano di accumulo",
        "disclaimer": DISCLAIMER,
        "plan": plan or {},
        "sleeve_eur": sleeve_eur,
        "holdings_estimated": holdings_estimated,
        "holdings_note": ESTIMATED_NOTE if holdings_estimated else None,
        "pick": items[0]["symbol"] if items else None,
        "items": items,
        "evidence": dict(EVIDENCE),
        "candidates": candidate_items,
        "rejected_summary": rejected_summary,
        "rejected_labels": dict(REJECT_IT),
        "caveats": list(CAVEATS),
    }


def write_markdown(text: str, path: str | Path) -> None:
    """Write the Markdown briefing (creating parent dirs)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


__all__ = [
    "CAVEATS",
    "DISCLAIMER",
    "ESTIMATED_NOTE",
    "EVIDENCE",
    "dca_report_dict",
    "format_report",
    "write_markdown",
    "write_report_json",
]
