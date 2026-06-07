"""Cross-source price validation (data-quality review #3).

A single feed can lie silently: the POL case (Yahoo frozen at ~0.22 while CoinGecko
showed ~0.084) was a *fresh-looking* but wrong number. Comparing the same asset's
price across two independent sources catches exactly that — a large divergence
flags the data as suspect, separate from freshness.

Pure function over two prices; unit-testable offline.
"""

from __future__ import annotations

from dataclasses import dataclass

MATCH = "match"
MISMATCH = "mismatch"
SINGLE = "single_source"


@dataclass(frozen=True)
class CrossSourceResult:
    """Outcome of comparing one asset's price across two sources."""

    status: str
    divergence_pct: float | None
    reason: str


def cross_source_check(
    primary: float | None,
    secondary: float | None,
    tol_pct: float = 3.0,
) -> CrossSourceResult:
    """Compare two prices for the same asset.

    Divergence is the absolute difference over the mean, in percent. Within
    ``tol_pct`` -> ``match``; beyond -> ``mismatch`` (suspect data); a missing or
    non-positive price -> ``single_source`` (can't cross-check). The default 3%
    tolerance absorbs the normal Yahoo-close-vs-CoinGecko-now intraday gap while
    still catching a frozen/wrong feed (which diverges by tens of percent).
    """
    if primary is None or secondary is None or primary <= 0 or secondary <= 0:
        return CrossSourceResult(SINGLE, None, "una sola fonte disponibile")
    mean = (primary + secondary) / 2.0
    divergence = abs(primary - secondary) / mean * 100.0
    if divergence <= tol_pct:
        return CrossSourceResult(MATCH, round(divergence, 2), f"fonti concordi (Δ {divergence:.1f}%)")
    return CrossSourceResult(MISMATCH, round(divergence, 2), f"divergenza {divergence:.1f}% tra le fonti")
