"""Export move attribution to JSON for the dashboard "Eventi" section (Fase 7).

Turns the abnormal-move attribution (``move_attribution``) into a dashboard
payload: for each asset, the recent abrupt moves, each labelled market-wide /
asset-specific and annotated with the most plausible triggering news.

Honesty carried over (VISION #1): these are **candidate** catalysts ranked by
plausibility — association, not proven causation. A move with no news attached is
flagged as such. Pure transform over ``AbnormalMove`` lists; unit-testable offline.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.features.event_classify import classify_event
from src.features.move_attribution import AbnormalMove

DISCLAIMER = (
    "Eventi candidati ordinati per plausibilità (vicinanza temporale + sentiment "
    "coerente). Associazione, non causa. Non è consulenza finanziaria."
)


def _move_to_dict(move: AbnormalMove) -> dict[str, Any]:
    """One abnormal move as a JSON-friendly record."""
    events: list[dict[str, Any]] = []
    for e in move.candidate_events:
        title = str(e.get("title", ""))
        events.append(
            {
                "source": str(e.get("source", "")),
                "title": title,
                "url": str(e.get("url", "")),
                "sentiment": e.get("sentiment"),
                "relevance": e.get("relevance"),
                "event_type": classify_event(title),
            }
        )
    return {
        "date": move.date.date().isoformat(),
        "return_pct": round(move.return_pct, 2),
        "zscore": round(move.zscore, 2),
        "classification": move.classification,
        "market_return_pct": (
            round(move.market_return_pct, 2) if move.market_return_pct is not None else None
        ),
        "events": events,
    }


def build_events_payload(
    asset_moves: list[dict[str, Any]],
    generated_at: pd.Timestamp | str | None = None,
) -> dict[str, Any]:
    """Assemble the events payload.

    ``asset_moves`` is a list of ``{symbol, name, moves}`` where ``moves`` is a
    list of ``AbnormalMove`` (newest first). Returns the dashboard JSON dict.
    """
    assets: list[dict[str, Any]] = []
    for entry in asset_moves:
        moves = entry.get("moves", [])
        assets.append(
            {
                "symbol": entry["symbol"],
                "name": entry["name"],
                "universe": entry.get("universe", "crypto"),
                "moves": [_move_to_dict(m) for m in moves],
            }
        )
    stamp = pd.Timestamp(generated_at) if generated_at is not None else pd.Timestamp.now(tz="UTC")
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    return {
        "generated_at": stamp.isoformat(),
        "title": "Eventi e movimenti",
        "disclaimer": DISCLAIMER,
        "assets": assets,
    }
