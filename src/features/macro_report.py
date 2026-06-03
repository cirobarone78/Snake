"""Human-readable macro "climate" report from FRED series (Fase 8).

Crypto/equity screeners say *what* is rotating; this says *what the weather is*
— the macro backdrop that conditions all markets. We turn a handful of FRED
series into a plain snapshot: current level, recent change, and a coarse
risk-on / risk-off reading, committed as ``REPORT_MACRO.md``.

Honest framing (VISION #9, #1): this is a **descriptive snapshot of conditions**,
not a market prediction. "Rates rising + dollar strong + curve inverted" is a
cautious backdrop, but it is context, not a signal to buy/sell.

The reading logic is a pure function over a dict of current values, so it
unit-tests offline with no network.
"""

from __future__ import annotations

import pandas as pd

# The FRED series we summarise, with human labels and units.
MACRO_LABELS: dict[str, str] = {
    "DFF": "Fed funds rate",
    "DGS2": "2Y Treasury",
    "DGS10": "10Y Treasury",
    "DTWEXBGS": "Broad dollar index",
    "CPIAUCSL": "CPI (inflation level)",
    "M2SL": "M2 money supply",
    "UNRATE": "Unemployment rate",
}


def yield_curve_slope(latest: dict[str, float]) -> float | None:
    """10Y minus 2Y (percentage points). ``None`` if either is missing."""
    t10 = latest.get("DGS10")
    t2 = latest.get("DGS2")
    if t10 is None or t2 is None or pd.isna(t10) or pd.isna(t2):
        return None
    return float(t10) - float(t2)


def climate_reading(latest: dict[str, float], change_30d: dict[str, float]) -> str:
    """Coarse risk-on / risk-off / mixed label from levels + 30d changes.

    Heuristic, transparent, deliberately simple (not a model): counts
    "cautious" signals — rising rates, strengthening dollar, an inverted yield
    curve. 2+ cautious -> risk-off; 0 -> risk-on; else mixed. It is a *summary*
    of the backdrop, never a trade signal.
    """
    cautious = 0
    considered = 0

    rate_chg = change_30d.get("DFF")
    if rate_chg is not None and not pd.isna(rate_chg):
        considered += 1
        if rate_chg > 0:
            cautious += 1

    dollar_chg = change_30d.get("DTWEXBGS")
    if dollar_chg is not None and not pd.isna(dollar_chg):
        considered += 1
        if dollar_chg > 0:
            cautious += 1

    slope = yield_curve_slope(latest)
    if slope is not None:
        considered += 1
        if slope < 0:  # inverted curve = classic recession warning
            cautious += 1

    if considered == 0:
        return "indeterminato (dati insufficienti)"
    if cautious >= 2:
        return "🔴 risk-off (cauto)"
    if cautious == 0:
        return "🟢 risk-on (favorevole)"
    return "🟡 misto"


def _fmt(v: float | None) -> str:
    if v is None or pd.isna(v):
        return "n/d"
    return f"{v:.2f}"


def format_macro_report_md(
    latest: dict[str, float],
    change_30d: dict[str, float],
    snapshot_at: pd.Timestamp | str | None = None,
) -> str:
    """GitHub-friendly Markdown macro climate report.

    ``latest`` maps FRED series_id -> current value; ``change_30d`` maps
    series_id -> change over ~30 days (same units). Both may be partial.
    """
    if not latest:
        return "# Clima macro\n\n_Nessun dato macro disponibile._\n"

    stamp = str(snapshot_at)[:16] if snapshot_at is not None else "n/d"
    slope = yield_curve_slope(latest)

    out: list[str] = []
    out.append("# 🌡️ Clima macro (USA)")
    out.append("")
    out.append(
        f"_Foto del momento (snapshot: **{stamp} UTC**) — contesto, **non una previsione.**_"
    )
    out.append("")
    out.append(f"**Lettura di fondo: {climate_reading(latest, change_30d)}**")
    out.append("")
    out.append("| Indicatore | Valore | Δ ~30g |")
    out.append("|---|--:|--:|")
    for sid, label in MACRO_LABELS.items():
        if sid not in latest:
            continue
        chg = change_30d.get(sid)
        chg_str = "n/d" if chg is None or pd.isna(chg) else f"{chg:+.2f}"
        out.append(f"| {label} | {_fmt(latest.get(sid))} | {chg_str} |")
    if slope is not None:
        sign = "invertita ⚠️" if slope < 0 else "normale"
        out.append(f"| **Curva 10Y-2Y** | **{slope:+.2f}** | {sign} |")

    out.append("")
    out.append("---")
    out.append(
        "> Lettura euristica e trasparente: tassi in salita + dollaro forte + "
        "curva invertita = contesto cauto. È un **riassunto del clima**, non un "
        "segnale operativo. La macro conta a orizzonti lunghi (settimane/mesi)."
    )
    out.append("")
    out.append("_Generato automaticamente dal workflow `macro-history`._")
    out.append("")
    return "\n".join(out)
