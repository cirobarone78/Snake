"""Compact price series export for the dashboard charts (Fase 7).

Turns daily close-price Series into a small, JSON-friendly time series (date +
value), trimmed to a recent window, so the static dashboard can draw real
stock-style line charts and sparklines without a charting backend.

Pure functions over pandas; unit-testable offline.
"""

from __future__ import annotations

from typing import Any, cast

import pandas as pd


def _points(series: pd.Series, window: int) -> list[dict[str, Any]]:
    """Last ``window`` ``{t, v}`` points of a daily close series (NaN dropped)."""
    s = cast("pd.Series", series.dropna()).tail(window)
    out: list[dict[str, Any]] = []
    for idx, value in s.items():
        ts = pd.Timestamp(cast("Any", idx))
        out.append({"t": ts.date().isoformat(), "v": round(float(cast("float", value)), 4)})
    return out


def build_market_series(
    closes: dict[str, pd.Series],
    names: dict[str, str] | None = None,
    window: int = 365,
    generated_at: pd.Timestamp | str | None = None,
) -> dict[str, Any]:
    """Assemble a multi-asset price-series payload for the hero chart.

    ``closes`` maps a symbol to its daily close Series. Each series is trimmed to
    the last ``window`` days. ``names`` gives display labels. The payload also
    carries, per series, the latest value and the window change in percent, so the
    chart can show "stock-style" values without recomputing them in the browser.
    """
    names = names or {}
    series: list[dict[str, Any]] = []
    for symbol, close in closes.items():
        points = _points(close, window)
        if not points:
            continue
        first_v = points[0]["v"]
        last_v = points[-1]["v"]
        change_pct = ((last_v / first_v) - 1.0) * 100.0 if first_v else None
        series.append(
            {
                "symbol": symbol,
                "name": names.get(symbol, symbol),
                "last": last_v,
                "change_pct": round(change_pct, 2) if change_pct is not None else None,
                "points": points,
            }
        )
    stamp = pd.Timestamp(generated_at) if generated_at is not None else pd.Timestamp.now(tz="UTC")
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    return {
        "generated_at": stamp.isoformat(),
        "title": "Andamento di mercato",
        "disclaimer": "Dati storici a fini educativi. Non è consulenza finanziaria.",
        "series": series,
    }


def sparkline_values(series: pd.Series, window: int = 60) -> list[float]:
    """Last ``window`` close values (rounded), for a compact card sparkline."""
    s = cast("pd.Series", series.dropna()).tail(window)
    return [round(float(cast("float", v)), 4) for v in s.to_numpy()]
