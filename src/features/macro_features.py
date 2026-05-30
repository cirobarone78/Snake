"""Macro features from FRED series, point-in-time safe (Fase 4).

Turns the raw FRED series (``value`` column, ``timestamp`` UTC index, one file
per series under ``data/raw/fred/{freq}/{SERIES_ID}.parquet``) into model-ready
daily features aligned to a price calendar, **without look-ahead**.

The hard part is *release timing*. FRED stamps a monthly series (CPI, M2,
UNRATE) at its **reference month** (e.g. the January CPI carries the date
2025-01-01), but that figure is only **published ~1-2 months later**. Using it
on the reference date would leak the future into the model — exactly the
look-ahead bias flagged in notebook 03 (ROADMAP debt). FRED's ALFRED vintage API
gives true release dates; pending that, we apply an explicit, conservative
**publication lag per series** and document it. Daily market series (Fed funds,
Treasury yields, broad dollar) are effectively same-day, so their lag is 0.

Pipeline, all causal by construction:

1. ``apply_publication_lag``: shift each series forward by its known publication
   delay, so a value is only "known" on/after its real release date.
2. ``to_daily``: forward-fill onto a daily calendar (a monthly figure stays in
   force until the next release) — the value at day ``t`` is the latest one
   *released on or before* ``t``.
3. ``align_macro_to_index``: reindex onto a price index (e.g. BTC trading days),
   ffill, so each price bar sees only already-released macro.
4. ``build_macro_features``: assemble levels + transforms (changes, YoY,
   yield-curve slope) that the Fase 1 EDA flagged as the informative ones.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final, cast

import pandas as pd

DEFAULT_FRED_DIR = Path("data/raw/fred")

# Conservative publication lag per series (calendar days from FRED reference
# date to first public release). Daily market series are same-day (0). Monthly
# macro is released with a delay; we use a safe upper bound rather than the
# exact (variable) release date until ALFRED vintages are wired in.
PUBLICATION_LAG_DAYS: Final[dict[str, int]] = {
    "DFF": 0,  # effective fed funds rate, daily
    "DGS2": 0,  # 2Y Treasury, daily
    "DGS10": 0,  # 10Y Treasury, daily
    "DTWEXBGS": 0,  # broad dollar index, daily (released next business day)
    "CPIAUCSL": 45,  # CPI: ~2nd week of the following month -> ~45d safe bound
    "M2SL": 45,  # M2: released ~4 weeks after month end
    "UNRATE": 35,  # unemployment: first Friday of the following month
}


def load_fred_series(series_id: str, fred_dir: Path = DEFAULT_FRED_DIR) -> pd.Series:
    """Load one FRED series as a ``value`` Series (UTC ``timestamp`` index).

    Searches ``fred_dir`` recursively for ``{series_id}.parquet`` (stored under a
    per-frequency subdir). Raises ``FileNotFoundError`` if absent.
    """
    matches = list(fred_dir.rglob(f"{series_id}.parquet"))
    if not matches:
        raise FileNotFoundError(
            f"FRED series {series_id} not found under {fred_dir} "
            f"(run `uv run python -m src.ingestion.tier1.fetch_fred`)"
        )
    df = pd.read_parquet(matches[0])
    return cast("pd.Series", df["value"]).rename(series_id)


def apply_publication_lag(series: pd.Series, lag_days: int) -> pd.Series:
    """Shift a series forward by ``lag_days`` so values land on their release date.

    A reference-dated observation at day ``d`` becomes available at ``d +
    lag_days``. ``lag_days=0`` is a no-op (daily market series). Negative lags
    are rejected (would create look-ahead).
    """
    if lag_days < 0:
        raise ValueError("lag_days must be >= 0 (a negative lag is look-ahead)")
    if lag_days == 0 or series.empty:
        return series.copy()
    shifted = series.copy()
    shifted.index = pd.DatetimeIndex(series.index) + pd.Timedelta(days=lag_days)
    return shifted


def to_daily(series: pd.Series) -> pd.Series:
    """Forward-fill a (possibly sparse/monthly) series onto a daily UTC calendar.

    The value at day ``t`` is the most recent observation with index ``<= t``
    (step function, no interpolation, no back-fill). Leading days before the
    first observation are dropped.
    """
    if series.empty:
        return series.copy()
    idx = pd.DatetimeIndex(series.index)
    daily_index = pd.date_range(idx.min(), idx.max(), freq="D", tz=idx.tz)
    return cast("pd.Series", series.reindex(daily_index).ffill())


def align_macro_to_index(series: pd.Series, target_index: pd.DatetimeIndex) -> pd.Series:
    """Reindex a (release-lagged) series onto ``target_index``, forward-filled.

    Each target bar sees the latest value released on or before it. Bars before
    the first release are NaN (the model has no macro yet — never guessed).
    """
    if series.empty:
        return pd.Series(index=target_index, dtype="float64", name=series.name)
    combined = series.reindex(series.index.union(target_index)).ffill()
    return cast("pd.Series", combined.reindex(target_index))


def yoy_change(series: pd.Series, periods: int = 365) -> pd.Series:
    """Year-over-year change on a daily series (``periods`` days back).

    The Fase 1 EDA found BTC vs CPI **YoY** = -0.40 (the macro signal lives at
    the YoY horizon, not intraday). Uses a label shift so each value compares to
    the one ~1 year earlier on the same daily grid.
    """
    return cast("pd.Series", series - series.shift(periods)).rename(f"{series.name}_yoy")


def build_macro_features(
    price_index: pd.DatetimeIndex,
    fred_dir: Path = DEFAULT_FRED_DIR,
    publication_lag: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Assemble point-in-time-safe macro features aligned to ``price_index``.

    Loads the standard FRED series, applies each one's publication lag, projects
    onto a daily calendar, aligns to the price index, and derives the transforms
    the EDA flagged as informative:

    - ``rate_2y``, ``rate_10y``, ``fed_funds``: level of rates (daily, lag 0)
    - ``yield_curve_slope`` = 10Y - 2Y (recession signal; inverted ~26% of days)
    - ``broad_dollar``: DXY-equivalent level (crypto headwind when strong)
    - ``cpi_yoy``, ``m2_yoy``: YoY inflation / money supply (lagged to release)
    - ``unemployment``: level (lagged to release)

    Every column is causal: at price bar ``t`` it reflects only macro **released
    on or before** ``t``. Series missing from disk are skipped (logged via a
    column simply not appearing), so the function degrades gracefully.
    """
    lags = publication_lag or PUBLICATION_LAG_DAYS

    def prepared(series_id: str) -> pd.Series | None:
        try:
            raw = load_fred_series(series_id, fred_dir)
        except FileNotFoundError:
            return None
        lagged = apply_publication_lag(raw, lags.get(series_id, 0))
        return align_macro_to_index(to_daily(lagged), price_index)

    out = pd.DataFrame(index=price_index)
    out.index.name = "date"

    dff = prepared("DFF")
    dgs2 = prepared("DGS2")
    dgs10 = prepared("DGS10")
    dxy = prepared("DTWEXBGS")
    cpi = prepared("CPIAUCSL")
    m2 = prepared("M2SL")
    unrate = prepared("UNRATE")

    if dff is not None:
        out["fed_funds"] = dff
    if dgs2 is not None:
        out["rate_2y"] = dgs2
    if dgs10 is not None:
        out["rate_10y"] = dgs10
    if dgs2 is not None and dgs10 is not None:
        out["yield_curve_slope"] = dgs10 - dgs2
    if dxy is not None:
        out["broad_dollar"] = dxy
    if cpi is not None:
        out["cpi_yoy"] = yoy_change(cpi)
    if m2 is not None:
        out["m2_yoy"] = yoy_change(m2)
    if unrate is not None:
        out["unemployment"] = unrate

    return out
