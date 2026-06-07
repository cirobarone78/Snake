"""Event-type classification from a headline (Fase 7).

Upgrades attribution from "here is a headline" to "this is a *regulatory* / *hack* /
*macro* event", using a transparent keyword lexicon — no ML, no API. The goal (from
the data-quality review): answer not only "is sentiment positive?" but "what *type*
of event is this?", so the dashboard can say "2 regulatory, 1 hack".

Word-boundary matching avoids false positives (e.g. "war" must not match
"forward"). First matching type wins, in a deliberate priority order. Pure
function, unit-testable offline.
"""

from __future__ import annotations

import re

OTHER = "other"

# (type, keywords) in priority order: the first type with a whole-word match wins.
_LEXICON: list[tuple[str, list[str]]] = [
    ("hack", ["hack", "hacked", "exploit", "breach", "stolen", "drained", "attack"]),
    ("regulation", ["sec", "regulation", "regulatory", "regulator", "ban", "banned", "mica", "crackdown"]),
    ("legal", ["lawsuit", "court", "sues", "sued", "settlement", "charges", "fraud", "probe"]),
    ("fed", ["fed", "fomc", "powell", "rate cut", "rate hike", "interest rate", "rate decision"]),
    ("inflation", ["inflation", "cpi", "ppi", "pce"]),
    ("macro", ["gdp", "unemployment", "recession", "payrolls", "jobs report"]),
    ("geopolitical", ["war", "israel", "iran", "russia", "ukraine", "hezbollah", "sanctions", "sanction", "tariff", "tariffs", "geopolitical"]),
    ("etf_flow", ["etf", "etfs", "inflow", "inflows", "outflow", "outflows"]),
    ("earnings", ["earnings", "revenue", "quarterly results", "guidance", "profit"]),
    ("listing", ["listing", "listed on", "lists"]),
    ("delisting", ["delist", "delisting", "delisted"]),
    ("upgrade", ["mainnet", "hard fork", "halving", "upgrade", "testnet", "launches", "launch"]),
    ("partnership", ["partnership", "partners with", "integration", "collaboration", "teams up"]),
]


def classify_event(title: str | None) -> str:
    """Return the event type for a headline, or ``"other"`` if none match."""
    text = (title or "").lower()
    if not text.strip():
        return OTHER
    for event_type, keywords in _LEXICON:
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                return event_type
    return OTHER
