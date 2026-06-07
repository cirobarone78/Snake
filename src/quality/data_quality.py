"""Data confidence scoring — kept separate from signal strength (Fase 7).

The screeners say *how strong* a move is (``signal_strength``); this module says
*how much we should trust the data* behind it (``data_confidence``). A strong move
on thin, stale, or illiquid data deserves less trust than a modest move on fresh,
liquid, cross-checked data — and the dashboard should show both, never conflate
them (the review's key point).

Confidence is a transparent blend of a few honest signals we already have:
freshness (age of the underlying data), liquidity (market cap as a proxy), and
completeness (are the expected fields present). No prediction, no ML — just a
trust score in ``[0, 1]`` with a human-readable reason. Pure functions,
unit-testable offline.
"""

from __future__ import annotations

from dataclasses import dataclass

# Confidence status buckets.
VALID = "valid"
SUSPICIOUS = "suspicious"
LOW = "low"
STALE = "stale"


@dataclass(frozen=True)
class DataConfidence:
    """Trust in the data behind a row: score, status bucket, and why."""

    score: float
    status: str
    reason: str


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def freshness_score(age_days: float | None, soft: float = 2.0, hard: float = 7.0) -> float:
    """1.0 if data is at most ``soft`` days old, decaying linearly to 0 at ``hard``.

    ``None`` (unknown age) scores 0 — we do not trust data we cannot date.
    """
    if age_days is None:
        return 0.0
    if age_days <= soft:
        return 1.0
    if age_days >= hard:
        return 0.0
    return _clamp(1.0 - (age_days - soft) / (hard - soft))


def liquidity_score(market_cap: float | None, mid: float = 1e8, high: float = 1e9) -> float:
    """Liquidity proxy from market cap: large = reliable, micro = treat with care."""
    if market_cap is None:
        return 0.4
    if market_cap >= high:
        return 1.0
    if market_cap >= mid:
        return 0.7
    return 0.35


def _status(score: float, stale: bool = False) -> str:
    if stale:
        return STALE
    if score >= 0.80:
        return VALID
    if score >= 0.55:
        return SUSPICIOUS
    return LOW


def crypto_item_confidence(
    market_cap: float | None,
    has_change: bool,
    has_leader: bool,
    snapshot_age_days: float | None = 0.0,
) -> DataConfidence:
    """Confidence for a crypto category row (liquidity-driven, plus freshness)."""
    liq = liquidity_score(market_cap)
    fr = freshness_score(snapshot_age_days)
    comp = 1.0 if (has_change and has_leader) else 0.75
    score = round(_clamp(0.55 * liq + 0.30 * fr + 0.15 * comp), 2)
    reasons: list[str] = []
    if liq <= 0.35:
        reasons.append("liquidità bassa")
    elif liq < 1.0:
        reasons.append("capitalizzazione media")
    if fr < 1.0:
        reasons.append("dato non freschissimo")
    if comp < 1.0:
        reasons.append("campi incompleti")
    reason = "dati solidi" if not reasons else ", ".join(reasons)
    return DataConfidence(score, _status(score, stale=fr == 0.0), reason)


def equity_item_confidence(
    age_days: float | None,
    has_5d: bool,
    has_21d: bool,
) -> DataConfidence:
    """Confidence for an equity sector ETF row (freshness-driven; ETFs are liquid)."""
    fr = freshness_score(age_days)
    comp = 1.0 if (has_5d and has_21d) else 0.7
    score = round(_clamp(0.65 * fr + 0.20 * 1.0 + 0.15 * comp), 2)
    reasons: list[str] = []
    if fr == 0.0:
        reasons.append("feed potenzialmente fermo")
    elif fr < 1.0:
        reasons.append("prezzo non aggiornato di recente")
    if comp < 1.0:
        reasons.append("momentum incompleto")
    reason = "ETF liquido, dati freschi" if not reasons else ", ".join(reasons)
    return DataConfidence(score, _status(score, stale=fr == 0.0), reason)
