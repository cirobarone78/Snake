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

ACCRUAL_IT: dict[str, str] = {
    "fee_burn": "le commissioni bruciano offerta",
    "staking_yield": "chi mette in staking incassa le commissioni",
    "buyback": "i ricavi finanziano riacquisti del token",
    "work_token": "serve possederlo per fornire il servizio",
    "gas_only": "serve per transare, ma non cattura ricavi",
    "monetary": "tesi monetaria: non cattura ricavi per scelta",
    "governance_only": "dà solo diritto di voto, nessun flusso",
    "none": "nessun legame fra prezzo e attività della rete",
    "unknown": "non ancora studiato",
}

EMISSION_IT: dict[str, str] = {
    "deflationary": "offerta in calo",
    "capped": "offerta con tetto massimo",
    "low_inflation": "inflazione contenuta",
    "high_inflation": "inflazione alta",
    "unlock_overhang": "sblocchi importanti ancora davanti",
    "unknown": "emissione non verificata",
}

DEV_IT: dict[str, str] = {
    "active": "sviluppo attivo",
    "moderate": "sviluppo moderato",
    "low": "sviluppo rado",
    "thin": "quasi nessuno sviluppo",
    "quiet_or_stale": "nessun commit recente, ma dato forse non aggiornato",
    "no_repo_data": "repository non mappato: dato assente",
}

VERDICT_IT: dict[str, str] = {
    "capture_present": "Il token cattura valore dalla rete",
    "capture_but_thin_dev": "Cattura valore, ma quasi nessuno sviluppo",
    "monetary_thesis": "Tesi monetaria (non cattura ricavi, per scelta)",
    "governance_only": "Solo governance: nessun flusso al detentore",
    "no_value_capture": "Nessun meccanismo di cattura del valore",
    "unresearched": "Economia del token non ancora studiata",
}

# Order the dossier so the reader meets the projects with a working mechanism
# first and the ones without it last — the point is the reason, not the rank.
VERDICT_ORDER: tuple[str, ...] = (
    "capture_present", "capture_but_thin_dev", "monetary_thesis",
    "unresearched", "governance_only", "no_value_capture",
)

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
    "La scheda dei progetti descrive **come è fatto** il token: chi cattura il "
    "valore, quanta offerta deve ancora arrivare, se qualcuno lo sviluppa. Non è "
    "una previsione e non è stata validata su dati storici — non esiste una serie "
    "abbastanza lunga e pulita per farlo.",
    "Manca il dato più importante: i **ricavi di protocollo**. Le fonti che li "
    "pubblicano (DefiLlama, Token Terminal) sono bloccate dalla policy di rete di "
    "questo ambiente. Senza, si può dire *se* un meccanismo di cattura esiste, non "
    "*quanto* valga: un burn enorme e uno simbolico oggi hanno lo stesso punteggio.",
    "L'economia dei token è **curata a mano** (con fonte e data), non scaricata da "
    "un'API. Copre i nomi principali; per gli altri il verdetto è "
    "'non studiato', che non è la stessa cosa di 'non ha fondamenta'.",
    "Survivorship bias: la classifica di oggi contiene solo chi è sopravvissuto. "
    "Gran parte della top 100 del 2018 non esiste più, e quelle monete non "
    "compaiono in questi dati.",
    "Su orizzonti di 5-10 anni le singole altcoin hanno un tasso di mortalità "
    "storicamente alto. Fondamenta solide riducono il rischio, non lo annullano: "
    "Bitcoin nel 2011 non avrebbe superato nessuno screen fondamentale.",
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


def _percent_article(pct: float) -> str:
    """Italian percentage with the right article ("l'80%", "il 65%")."""
    rounded = round(pct)
    article = "l'" if str(rounded).startswith(("8", "11")) else "il "
    return f"{article}{rounded}%"


def _text(value: object) -> str | None:
    """Non-empty string, else ``None`` — a blank cell is missing, not empty."""
    return value if isinstance(value, str) and value else None


def _int(value: object) -> int | None:
    n = _num(value)
    return None if n is None else int(n)


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
            "## Progetti: cosa c'è dietro il token",
            "",
            "Per ogni progetto: cosa fa, **se e come il valore che produce arriva a chi "
            "tiene il token**, quanta offerta deve ancora arrivare, e se qualcuno lo sta "
            "ancora sviluppando. Descrizione, non previsione.",
            "",
        ]
        lines += _dossier_lines(candidates)

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


def _dossier_lines(candidates: pd.DataFrame) -> list[str]:
    """Per-project dossier, grouped by verdict so the *reason* leads, not the rank."""
    records = candidates.to_dict("records")
    lines: list[str] = []
    seen: set[str] = set()
    ordered = [
        *(v for v in VERDICT_ORDER if any(str(r.get("verdict")) == v for r in records)),
        *sorted({str(r.get("verdict")) for r in records} - set(VERDICT_ORDER)),
    ]
    for verdict in ordered:
        group = [r for r in records if str(r.get("verdict")) == verdict]
        if not group:
            continue
        lines += [f"### {VERDICT_IT.get(verdict, verdict)}", ""]
        for row in group:
            symbol = str(row.get("symbol") or "")
            if symbol in seen:
                continue
            seen.add(symbol)
            lines += _dossier_entry(row)
        lines.append("")
    return lines


def _dossier_entry(row: dict[str, Any]) -> list[str]:
    """One project's card: what it is, who captures the value, what dilutes it."""
    symbol = str(row.get("symbol") or "")
    name = str(row.get("name") or "")
    what = row.get("what_it_does")
    lines = [f"**{symbol} — {name}**", ""]
    if isinstance(what, str) and what:
        lines += [what, ""]
    accrual = str(row.get("accrual") or "unknown")
    note = row.get("accrual_note")
    detail = f" {note}" if isinstance(note, str) and note else ""
    lines.append(f"- **Cattura del valore**: {ACCRUAL_IT.get(accrual, accrual)}.{detail}")

    emission = str(row.get("emission") or "unknown")
    fdv = _num(row.get("fdv_ratio"))
    dilution = EMISSION_IT.get(emission, emission)
    if fdv is not None and fdv > 1.01:
        # FDV/mcap is the readable form of "how much supply is still to come".
        dilution += f" — valutazione diluita {fdv:.2f} volte la capitalizzazione attuale"
    lines.append(f"- **Offerta**: {dilution}.")

    dev = str(row.get("dev_status") or "no_repo_data")
    commits = _num(row.get("commits_4w"))
    dev_text = DEV_IT.get(dev, dev)
    if commits is not None and dev not in {"no_repo_data"}:
        dev_text += f" ({commits:.0f} commit in 4 settimane)"
    lines.append(f"- **Sviluppo**: {dev_text}.")

    age = _num(row.get("age_years"))
    if age is not None:
        source = str(row.get("age_source") or "")
        qualifier = " almeno" if source == "atl_lower_bound" else ""
        lines.append(f"- **Età**:{qualifier} {age:.1f} anni.")

    confidence = _num(row.get("confidence"))
    if confidence is not None and confidence < 1.0:
        lines.append(
            "- ⚠️ Scheda incompleta: nota solo per "
            f"{_percent_article(confidence * 100)} dei criteri."
        )
    lines.append("")
    return lines


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
    candidate_rows = (
        candidates.to_dict("records") if candidates is not None and not candidates.empty else []
    )
    for row in candidate_rows:
        accrual = str(row.get("accrual") or "unknown")
        emission = str(row.get("emission") or "unknown")
        dev = str(row.get("dev_status") or "no_repo_data")
        verdict = str(row.get("verdict") or "unresearched")
        candidate_items.append(
            {
                "rank": int(row["rank"]) if row.get("rank") is not None else None,
                "symbol": str(row.get("symbol") or ""),
                "name": str(row.get("name") or ""),
                "what_it_does": _text(row.get("what_it_does")),
                "accrual": accrual,
                "accrual_it": ACCRUAL_IT.get(accrual, accrual),
                "accrual_note": _text(row.get("accrual_note")),
                "emission": emission,
                "emission_it": EMISSION_IT.get(emission, emission),
                "fdv_ratio": _round(_num(row.get("fdv_ratio")), 3),
                "circulating_pct": _round(_num(row.get("circulating_pct")), 2),
                "dev_status": dev,
                "dev_status_it": DEV_IT.get(dev, dev),
                "commits_4w": _int(row.get("commits_4w")),
                "age_years": _round(_num(row.get("age_years")), 2),
                "age_source": _text(row.get("age_source")),
                "verdict": verdict,
                "verdict_it": VERDICT_IT.get(verdict, verdict),
                "score": _round(_num(row.get("score")), 4),
                "confidence": _round(_num(row.get("confidence")), 4),
                "market_cap": _num(row.get("market_cap")),
                "categories": _text(row.get("categories")),
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
        "verdict_order": list(VERDICT_ORDER),
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
