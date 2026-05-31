"""Human-readable "opportunities / risks now" report from the category screener.

Turns a categories snapshot (``CoinGeckoSource.fetch_categories`` / the persisted
``categories_latest.parquet``) into a plain-text briefing: which crypto narratives
are strongest right now, which are weakest, and the leading coins in each. This is
the consultable face of the screener — the user's "what should I look at now".

Honest framing (CLAUDE.md, VISION #9): this reports the **present snapshot**, not
a prediction. It says "these narratives are moving now", not "these will go up".
The probabilistic layer ("historically, after a state like this, what happened")
needs the accumulated history and is a separate, later step.

The formatting core is a pure function over a DataFrame, so it unit-tests offline.
"""

from __future__ import annotations

import pandas as pd

from src.features.screener import screen_categories, screen_movers


def _fmt_mcap(v: float) -> str:
    """Compact market-cap string ($1.2B / $340M)."""
    if pd.isna(v):
        return "n/a"
    if v >= 1e9:
        return f"${v / 1e9:.1f}B"
    return f"${v / 1e6:.0f}M"


def _lead_coins(raw: object, k: int = 3) -> str:
    """First ``k`` leading coins from a comma-joined string (``-`` if none)."""
    if raw is None or not isinstance(raw, str) or not raw:
        return "-"
    return ", ".join(raw.split(",")[:k])


def format_report(categories: pd.DataFrame, top_n: int = 8, movers_n: int = 5) -> str:
    """Build a plain-text screener briefing from a categories snapshot.

    Sections:
    - **Narrative in forza ORA**: top categories by composite strength score
      (move + turnover, outlier-robust), with signal label and leading coins.
    - **In calo / rischio ORA**: the weakest categories by 24h move.

    Pure function: no network, no I/O. An empty snapshot yields a short notice.
    """
    if categories.empty:
        return "Nessun dato di categoria disponibile (snapshot vuoto)."

    strong = screen_categories(categories, top_n=top_n)
    movers = screen_movers(categories, n=movers_n)

    lines: list[str] = []
    lines.append("=" * 64)
    lines.append("SCREENER NARRATIVE CRYPTO — foto del momento (non una previsione)")
    lines.append("=" * 64)

    lines.append("")
    lines.append(f"🔥 NARRATIVE IN FORZA ORA (top {len(strong)} per forza relativa)")
    lines.append("-" * 64)
    if strong.empty:
        lines.append("  (nessuna categoria sopra la soglia di market cap)")
    else:
        for row in strong.to_dict("records"):
            signal = str(row["signal"])
            lines.append(
                f"  [{signal:>7}] {str(row['name'])[:30]:30} "
                f"score {float(row['score']):.2f}  24h {float(row['change_24h_pct']):+5.1f}%  "
                f"mcap {_fmt_mcap(float(row['market_cap']))}"
            )
            lines.append(f"            coin: {_lead_coins(row['top_coins'])}")

    lines.append("")
    lines.append(f"📉 IN CALO / RISCHIO ORA (peggiori {movers_n} per 24h)")
    lines.append("-" * 64)
    losers = movers["losers"]
    if losers.empty:
        lines.append("  (nessuna categoria sopra la soglia di market cap)")
    else:
        for row in losers.to_dict("records"):
            lines.append(
                f"  {str(row['name'])[:30]:30} 24h {float(row['change_24h_pct']):+5.1f}%  "
                f"mcap {_fmt_mcap(float(row['market_cap']))}  ({_lead_coins(row['top_coins'])})"
            )

    lines.append("")
    lines.append("-" * 64)
    lines.append(
        "Nota: forza = mossa 24h + turnover (volume/mcap), robusta agli outlier.\n"
        "Micro-cap filtrate come rumore. Questa e' la rotazione ATTUALE, non una\n"
        "previsione: il potere predittivo storico richiede l'accumulo della history."
    )
    return "\n".join(lines)


def format_report_md(
    categories: pd.DataFrame,
    top_n: int = 8,
    movers_n: int = 5,
    snapshot_at: pd.Timestamp | str | None = None,
) -> str:
    """Build a GitHub-friendly **Markdown** screener briefing from a snapshot.

    Same content as ``format_report`` but as Markdown tables, so it renders
    nicely when committed as ``REPORT.md`` and viewed on GitHub (the user's
    "vedere il report senza lanciare comandi"). ``snapshot_at`` stamps the
    freshness; pure function, no I/O.
    """
    if categories.empty:
        return "# Screener narrative crypto\n\n_Nessun dato di categoria disponibile._\n"

    strong = screen_categories(categories, top_n=top_n)
    movers = screen_movers(categories, n=movers_n)
    stamp = str(snapshot_at)[:16] if snapshot_at is not None else "n/d"

    out: list[str] = []
    out.append("# 🧭 Screener narrative crypto")
    out.append("")
    out.append(f"_Foto del momento (snapshot: **{stamp} UTC**) — **non è una previsione.**_")
    out.append("")

    out.append("## 🔥 Narrative in forza ora")
    out.append("")
    out.append("| # | Narrativa | Segnale | Forza | 24h | Mcap | Coin guida |")
    out.append("|--:|---|:-:|--:|--:|--:|---|")
    for i, row in enumerate(strong.to_dict("records"), start=1):
        name = str(row["name"])
        signal = str(row["signal"])
        out.append(
            f"| {i} | {name} | {signal} | "
            f"{float(row['score']):.2f} | {float(row['change_24h_pct']):+.1f}% | "
            f"{_fmt_mcap(float(row['market_cap']))} | {_lead_coins(row['top_coins'])} |"
        )

    out.append("")
    out.append("## 📉 In calo / rischio ora")
    out.append("")
    out.append("| Narrativa | 24h | Mcap | Coin guida |")
    out.append("|---|--:|--:|---|")
    for row in movers["losers"].to_dict("records"):
        name = str(row["name"])
        out.append(
            f"| {name} | {float(row['change_24h_pct']):+.1f}% | "
            f"{_fmt_mcap(float(row['market_cap']))} | {_lead_coins(row['top_coins'])} |"
        )

    out.append("")
    out.append("---")
    out.append(
        "> **Forza** = mossa 24h + turnover (volume/market-cap), robusta agli "
        "outlier; micro-cap filtrate come rumore. Questa è la **rotazione "
        "attuale**, non una previsione: il potere predittivo storico richiede "
        "l'accumulo della history (in corso)."
    )
    out.append("")
    out.append("_Generato automaticamente dal workflow `category-history`._")
    out.append("")
    return "\n".join(out)

