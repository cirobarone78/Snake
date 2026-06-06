"""JSON export of the rotation snapshots, for a static dashboard (Fase 7).

A machine-readable twin of the Markdown briefings (``screener_report`` /
``sector_report``). It reuses the **same structured screener output** — no Markdown
parsing — so the dashboard reads clean JSON while the existing reports keep working
untouched.

Honesty rules carried over (CLAUDE.md, and the dashboard brief): every payload
carries an educational ``disclaimer``; a missing/NaN field is ``null`` (never
invented); the schema describes the *present snapshot*, never a prediction or a
buy/sell call. Pure functions over DataFrames + a tiny writer; unit-testable
offline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pandas as pd

from src.assets.sectors import get_sector_by_symbol
from src.features.screener import screen_categories
from src.features.sector_screener import screen_sectors

DISCLAIMER = "Educational snapshot, not financial advice. No buy/sell recommendations."


def _num(value: object) -> float | None:
    """Plain float, or ``None`` for missing/NaN (never invent a value)."""
    if value is None or pd.isna(cast("float", value)):
        return None
    return float(cast("float", value))


def _round(value: float | None, ndigits: int) -> float | None:
    return None if value is None else round(value, ndigits)


def _iso(generated_at: pd.Timestamp | str | None) -> str:
    """ISO-8601 UTC timestamp; defaults to now."""
    ts = pd.Timestamp(generated_at) if generated_at is not None else pd.Timestamp.now(tz="UTC")
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.isoformat()


def _first_coin(raw: object) -> str | None:
    """Leading coin from a comma-joined ``top_coins`` string, else ``None``."""
    if isinstance(raw, str) and raw:
        return raw.split(",")[0].strip()
    return None


def crypto_report_dict(
    categories: pd.DataFrame,
    top_n: int = 8,
    generated_at: pd.Timestamp | str | None = None,
) -> dict[str, Any]:
    """Dashboard JSON payload for the crypto narrative rotation snapshot."""
    items: list[dict[str, Any]] = []
    if not categories.empty:
        strong = screen_categories(categories, top_n=top_n)
        for i, row in enumerate(strong.to_dict("records"), start=1):
            items.append(
                {
                    "rank": i,
                    "name": str(row["name"]),
                    "status": str(row["signal"]),
                    "strength": _round(_num(row["score"]), 4),
                    "change_24h": _round(_num(row["change_24h_pct"]), 2),
                    "market_cap": _num(row["market_cap"]),
                    "leader": _first_coin(row.get("top_coins")),
                    "note": None,
                }
            )
    return {
        "generated_at": _iso(generated_at),
        "title": "Crypto Narrative Rotation",
        "disclaimer": DISCLAIMER,
        "items": items,
    }


def equity_report_dict(
    sector_frame: pd.DataFrame,
    top_n: int = 10,
    generated_at: pd.Timestamp | str | None = None,
    spark: dict[str, list[float]] | None = None,
) -> dict[str, Any]:
    """Dashboard JSON payload for the equity sector/theme rotation snapshot.

    ``spark`` optionally maps a sector symbol to a short close-price series, embedded
    per item as ``spark`` so each card can draw a real mini price chart.
    """
    spark = spark or {}
    items: list[dict[str, Any]] = []
    if not sector_frame.empty:
        strong = screen_sectors(sector_frame, top_n=top_n)
        for i, row in enumerate(strong.to_dict("records"), start=1):
            symbol = str(row["symbol"])
            asset = get_sector_by_symbol(symbol)
            items.append(
                {
                    "rank": i,
                    "name": str(row["name"]),
                    "ticker": asset.yahoo_symbol if asset is not None else None,
                    "status": str(row["signal"]),
                    "strength": _round(_num(row["score"]), 4),
                    "change_5d": _round(_num(row["ret_5d_pct"]), 2),
                    "change_1m": _round(_num(row["ret_21d_pct"]), 2),
                    "spark": spark.get(symbol) or None,
                    "note": None,
                }
            )
    return {
        "generated_at": _iso(generated_at),
        "title": "Equity Sector Rotation",
        "disclaimer": DISCLAIMER,
        "items": items,
    }


def write_report_json(payload: dict[str, Any], path: str | Path) -> None:
    """Write a payload as pretty, UTF-8 JSON (creating parent dirs)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
