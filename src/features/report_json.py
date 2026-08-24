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
import math
from pathlib import Path
from typing import Any, cast

import pandas as pd

from src.assets.sectors import get_sector_by_symbol
from src.features.screener import screen_categories
from src.features.sector_screener import screen_sectors
from src.quality.data_quality import crypto_item_confidence, equity_item_confidence

DISCLAIMER = "Educational snapshot, not financial advice. No buy/sell recommendations."


def _num(value: object) -> float | None:
    """Plain float, or ``None`` for missing/NaN (never invent a value)."""
    if value is None or pd.isna(cast("float", value)):
        return None
    return float(cast("float", value))


def _round(value: float | None, ndigits: int) -> float | None:
    return None if value is None else round(value, ndigits)


def iso_timestamp(generated_at: pd.Timestamp | str | None) -> str:
    """ISO-8601 UTC timestamp; defaults to now.

    Public because every report payload in the project stamps itself the same
    way, and a second copy of this would be a second thing to get wrong.
    """
    ts = pd.Timestamp(generated_at) if generated_at is not None else pd.Timestamp.now(tz="UTC")
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.isoformat()


def _iso(generated_at: pd.Timestamp | str | None) -> str:
    """Backwards-compatible alias for :func:`iso_timestamp`."""
    return iso_timestamp(generated_at)


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
            market_cap = _num(row["market_cap"])
            change_24h = _num(row["change_24h_pct"])
            leader = _first_coin(row.get("top_coins"))
            conf = crypto_item_confidence(
                market_cap, has_change=change_24h is not None, has_leader=leader is not None
            )
            items.append(
                {
                    "rank": i,
                    "name": str(row["name"]),
                    "status": str(row["signal"]),
                    "strength": _round(_num(row["score"]), 4),
                    "data_confidence": conf.score,
                    "confidence_status": conf.status,
                    "confidence_reason": conf.reason,
                    "change_24h": _round(change_24h, 2),
                    "market_cap": market_cap,
                    "leader": leader,
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
    freshness_days: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Dashboard JSON payload for the equity sector/theme rotation snapshot.

    ``spark`` optionally maps a sector symbol to a short close-price series, embedded
    per item as ``spark`` so each card can draw a real mini price chart.
    ``freshness_days`` maps a symbol to the age (days) of its latest bar, used to
    compute the per-item ``data_confidence``.
    """
    spark = spark or {}
    freshness_days = freshness_days or {}
    items: list[dict[str, Any]] = []
    if not sector_frame.empty:
        strong = screen_sectors(sector_frame, top_n=top_n)
        for i, row in enumerate(strong.to_dict("records"), start=1):
            symbol = str(row["symbol"])
            asset = get_sector_by_symbol(symbol)
            change_5d = _num(row["ret_5d_pct"])
            change_1m = _num(row["ret_21d_pct"])
            # Missing age -> 0.0 (report is built right after fetch); fetch_sectors
            # passes real ages so a frozen feed is still caught.
            conf = equity_item_confidence(
                freshness_days.get(symbol, 0.0),
                has_5d=change_5d is not None,
                has_21d=change_1m is not None,
            )
            items.append(
                {
                    "rank": i,
                    "name": str(row["name"]),
                    "ticker": asset.yahoo_symbol if asset is not None else None,
                    "status": str(row["signal"]),
                    "strength": _round(_num(row["score"]), 4),
                    "data_confidence": conf.score,
                    "confidence_status": conf.status,
                    "confidence_reason": conf.reason,
                    "change_5d": _round(change_5d, 2),
                    "change_1m": _round(change_1m, 2),
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


def json_safe(value: Any) -> Any:
    """Recursively replace non-finite floats with ``None``.

    ``json.dumps`` writes NaN and Infinity as bare ``NaN``/``Infinity`` tokens.
    Python reads them back, but they are **not** valid JSON: ``JSON.parse``
    throws, so one undefined metric takes a whole dashboard view offline with
    no error message. It happened — the Spearman IC of the climatology ranker
    is undefined (a constant has no variance) and that single NaN made
    ``ranking_backtest.json`` unreadable in the browser. ``null`` is the
    honest encoding of "not defined", and it is what this module's docstring
    promised from the start.
    """
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in cast("dict[Any, Any]", value).items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in cast("list[Any]", list(value))]
    return value


def write_report_json(payload: dict[str, Any], path: str | Path) -> None:
    """Write a payload as pretty, UTF-8 JSON (creating parent dirs).

    ``allow_nan=False`` is the guard: after ``json_safe`` nothing non-finite
    should be left, and if a future payload smuggles one in we want a loud
    ``ValueError`` here rather than a silently broken dashboard tab.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(json_safe(payload), indent=2, ensure_ascii=False, allow_nan=False)
    p.write_text(text + "\n", encoding="utf-8")
