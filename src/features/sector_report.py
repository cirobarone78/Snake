"""Human-readable equity sector rotation report (Fase 8).

Markdown briefing of which equity sectors/themes are strongest and weakest now,
committed as ``REPORT_EQUITY.md`` so it renders on GitHub like the crypto one.
Honest framing (VISION #9): present snapshot, not a prediction.
"""

from __future__ import annotations

from typing import cast

import pandas as pd

from src.features.sector_screener import screen_sectors


def format_sector_report_md(
    frame: pd.DataFrame,
    top_n: int = 10,
    snapshot_at: pd.Timestamp | str | None = None,
) -> str:
    """GitHub-friendly Markdown report from a sector snapshot frame."""
    if frame.empty:
        return "# Screener settori equity\n\n_Nessun dato disponibile._\n"

    ranked = screen_sectors(frame, top_n=len(frame))
    stamp = str(snapshot_at)[:16] if snapshot_at is not None else "n/d"
    strong = cast("pd.DataFrame", ranked.head(top_n))
    weak = cast("pd.DataFrame", ranked[ranked["signal"] == "weak"])

    out: list[str] = []
    out.append("# 🏛️ Screener settori / temi equity")
    out.append("")
    out.append(f"_Foto del momento (snapshot: **{stamp} UTC**) — **non è una previsione.**_")
    out.append("")
    out.append("## 🔥 Settori in forza ora")
    out.append("")
    out.append("| # | Settore / tema | Segnale | Forza | 5g | ~1 mese |")
    out.append("|--:|---|:-:|--:|--:|--:|")
    for i, row in enumerate(strong.to_dict("records"), start=1):
        name = str(row["name"])
        signal = str(row["signal"])
        out.append(
            f"| {i} | {name} | {signal} | {float(row['score']):.2f} | "
            f"{float(row['ret_5d_pct']):+.1f}% | {float(row['ret_21d_pct']):+.1f}% |"
        )

    out.append("")
    out.append("## 📉 In calo / rischio ora")
    out.append("")
    if weak.empty:
        out.append("_Nessun settore in chiara debolezza._")
    else:
        out.append("| Settore / tema | 5g | ~1 mese |")
        out.append("|---|--:|--:|")
        for row in weak.to_dict("records"):
            name = str(row["name"])
            out.append(
                f"| {name} | {float(row['ret_5d_pct']):+.1f}% | "
                f"{float(row['ret_21d_pct']):+.1f}% |"
            )

    out.append("")
    out.append("---")
    out.append(
        "> **Forza** = momentum 5g + ~1 mese (rank-based, robusto agli outlier). "
        "Settori via ETF liquidi (no selezione di singoli titoli). Rotazione "
        "**attuale**, non una previsione."
    )
    out.append("")
    out.append("_Generato automaticamente dal workflow `sector-history`._")
    out.append("")
    return "\n".join(out)
