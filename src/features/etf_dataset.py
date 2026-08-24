# pyright: strict, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Point-in-time ETF panel: causal features + forward excess-return targets (WP2).

The question this dataset is built to answer (ADR-032, Fase 9) is **not** "does
the market go up?" but: *given today's state, with what probability does this
sector ETF beat the benchmark over the next 20 sessions?*. That is a
**cross-sectional, relative** question, so the panel is long-form
``(date, symbol)`` and every target is an **excess** return versus the benchmark
(SPY, decision D2), never an absolute one.

Design rules, non-negotiable (CLAUDE.md):

- **Causality**. Every feature at ``t`` uses only closes/volumes up to and
  including ``t`` (trailing windows, expanding cummax, same-day cross-sectional
  ranks). Adding bars after ``t`` cannot change a feature at ``t`` — this is
  asserted in the tests, not merely intended.
- **Targets are shifted forward**. ``excess_ret_20[t]`` is realised in
  ``(t, t+20]``. The last ``h`` rows of each symbol are NaN and are **never**
  filled: an unrealised future is missing data, not a zero.
- **No fetching here**. These are pure functions over pandas frames; the network
  lives in ``src/ingestion/tier1/build_etf_dataset.py``. Offline-testable
  (sandbox constraint) and asset-class-agnostic (ADR-014): the universe is just a
  frame of close columns — sector ETFs today, anything else tomorrow.

Two known simplifications, stated rather than hidden:

(a) **Adjusted prices.** The upstream Yahoo source fetches with
    ``auto_adjust=True``, so closes are split/dividend adjusted and the returns
    computed here are effectively **total returns**. That is the standard choice
    for a relative-strength study (dividends differ a lot between XLU and SMH,
    and ignoring them would bias the ranking against high-yield sectors), but it
    means these are *not* price returns and a live tracker of price-only quotes
    would not reproduce them exactly.

(b) **Survivorship.** The universe is the set of ETFs that exist **today**
    (D1). Residual survivorship bias is low — the SPDR Select Sector funds have
    traded since 1998 and none of the 20 has been liquidated — but it is not
    zero: a thematic ETF that launched, failed and closed before today would
    never enter this panel. The bias direction is optimistic and it is declared,
    not corrected.

On typing: the module is checked under ``pyright: strict``, minus the four rules
that fire only because ``pandas`` ships no ``py.typed`` marker (every pandas
member is then "partially unknown", which says nothing about this code). The
strict rules that *do* police what is written here — parameter and return
annotations, unnecessary casts, private usage — stay on.

A third property worth naming: assets with a short history (XLC 2018, BOTZ/CIBR
~2016, URA 2010, ICLN 2008, ITA 2006) are **kept** with NaN on the features their
history cannot support. Dropping them would silently reshape the universe over
time, which is exactly the kind of quiet bias this module exists to avoid.
"""

from __future__ import annotations

import hashlib
from typing import cast

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252
"""Annualisation factor for daily volatility (NYSE convention)."""

SCHEMA_VERSION = 1
"""Bump when the column set or a feature formula changes (invalidates caches)."""

DEFAULT_HORIZONS: tuple[int, ...] = (20, 60)
"""Primary horizon 20 sessions, secondary 60 (decision D3)."""

FEATURE_COLUMNS: list[str] = [
    "ret_5", "ret_20", "ret_60", "ret_126", "ret_252",
    "rel_ret_20", "rel_ret_60", "rel_ret_126",
    "vol_20", "vol_60", "downside_vol_60",
    "dist_sma50", "dist_sma200", "dist_52w_high", "drawdown",
    "beta_60", "corr_60",
    "volume_z20",
    "rank_rel_ret_60",
]
"""Phase-1 feature set (WP2). Adding a feature requires an ablation + an ADR."""

IDENTIFIER_COLUMNS: list[str] = ["date", "symbol"]
PRICE_COLUMNS: list[str] = ["close"]
"""``close`` travels with the panel as raw state (sizing, ledgers), not a feature."""


def target_columns(horizons: tuple[int, ...] = DEFAULT_HORIZONS) -> list[str]:
    """Target column names for ``horizons``: excess return + its sign, per horizon."""
    cols: list[str] = []
    for h in horizons:
        cols.extend([f"excess_ret_{h}", f"outperform_{h}"])
    return cols


# --- internal helpers -------------------------------------------------------


def _sorted_float_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_index().astype("float64")


def _common_index(closes: pd.DataFrame, benchmark: pd.Series) -> pd.DatetimeIndex:
    """Inner join of the universe and benchmark dates.

    Declared choice (WP2 acceptance test 5): a date the benchmark does not cover
    cannot produce an *excess* return, so it is dropped rather than filled with a
    forward-filled or zero benchmark move.
    """
    idx = pd.DatetimeIndex(closes.sort_index().index).intersection(
        pd.DatetimeIndex(benchmark.sort_index().index)
    )
    return cast("pd.DatetimeIndex", idx.sort_values())


def _trailing_return(closes: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """``close[t] / close[t-lookback] - 1`` (causal)."""
    return cast("pd.DataFrame", closes / closes.shift(lookback) - 1.0)


def _daily_returns(closes: pd.DataFrame) -> pd.DataFrame:
    return cast("pd.DataFrame", closes / closes.shift(1) - 1.0)


def _full_window_mask(returns: pd.DataFrame, window: int) -> pd.DataFrame:
    """True where the trailing ``window`` daily returns are all known.

    Guards the volatility features against being defined on a half-populated
    window right after a listing date.
    """
    counts = cast("pd.DataFrame", returns.notna().rolling(window).sum())
    return cast("pd.DataFrame", counts >= float(window))


def _rolling_vol(returns: pd.DataFrame, window: int) -> pd.DataFrame:
    """Annualised trailing volatility (population std, as in ``features/regime``)."""
    vol = cast("pd.DataFrame", returns.rolling(window).std(ddof=0))
    return cast("pd.DataFrame", vol * np.sqrt(TRADING_DAYS_PER_YEAR))


def _rolling_downside_vol(returns: pd.DataFrame, window: int) -> pd.DataFrame:
    """Annualised trailing std of the **negative** returns only.

    Positive days are masked to NaN and pandas' rolling std skips them, so the
    statistic is computed over the losses inside the window. Defined only where
    the whole window of returns is known (see ``_full_window_mask``), so a window
    that simply had few losses still reports a (small) downside vol rather than
    NaN.
    """
    losses = returns.where(returns < 0.0)
    vol = cast("pd.DataFrame", losses.rolling(window, min_periods=1).std(ddof=0))
    annualised = cast("pd.DataFrame", vol * np.sqrt(TRADING_DAYS_PER_YEAR))
    return annualised.where(_full_window_mask(returns, window))


def _dist_to_sma(closes: pd.DataFrame, window: int) -> pd.DataFrame:
    sma = cast("pd.DataFrame", closes.rolling(window).mean())
    return cast("pd.DataFrame", closes / sma - 1.0)


def _dist_to_rolling_high(closes: pd.DataFrame, window: int) -> pd.DataFrame:
    high = cast("pd.DataFrame", closes.rolling(window).max())
    return cast("pd.DataFrame", closes / high - 1.0)


def _drawdown(closes: pd.DataFrame) -> pd.DataFrame:
    """``close / expanding-max(close) - 1``: 0 at a new high, negative below it."""
    peak = closes.cummax()
    return cast("pd.DataFrame", closes / peak - 1.0)


def _rolling_beta_and_corr(
    returns: pd.DataFrame, benchmark_returns: pd.Series, window: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rolling OLS beta and correlation of each column against the benchmark."""
    bench_var = cast("pd.Series", benchmark_returns.rolling(window).var())
    betas: dict[str, pd.Series] = {}
    corrs: dict[str, pd.Series] = {}
    for col in returns.columns:
        series = cast("pd.Series", returns[col])
        cov = cast("pd.Series", series.rolling(window).cov(benchmark_returns))
        betas[str(col)] = cast("pd.Series", cov / bench_var)
        corrs[str(col)] = cast("pd.Series", series.rolling(window).corr(benchmark_returns))
    index = returns.index
    return (
        pd.DataFrame(betas, index=index),
        pd.DataFrame(corrs, index=index),
    )


def _volume_zscore(volumes: pd.DataFrame, window: int) -> pd.DataFrame:
    """Trailing z-score of volume. Zero-variance windows give NaN, not infinity."""
    mean = cast("pd.DataFrame", volumes.rolling(window).mean())
    std = cast("pd.DataFrame", volumes.rolling(window).std(ddof=0))
    std = std.where(std > 0.0)
    return cast("pd.DataFrame", (volumes - mean) / std)


def _rank_pct_row(values: np.ndarray) -> np.ndarray:
    """Cross-sectional percentile rank in ``[0, 1]``, NaN-preserving.

    Same convention as the screeners' ``_rank_pct`` (rank of the sorted order
    divided by ``n-1``), extended to skip missing assets: a symbol with no value
    that day gets NaN, and a **degenerate** universe (one ranked asset) gets the
    neutral 0.5 rather than an arbitrary extreme.
    """
    out = np.full(values.shape, np.nan, dtype="float64")
    valid = ~np.isnan(values)
    n = int(valid.sum())
    if n == 0:
        return out
    if n == 1:
        out[valid] = 0.5
        return out
    ranked = values[valid]
    order = np.argsort(np.argsort(ranked, kind="stable"), kind="stable").astype("float64")
    out[valid] = order / (n - 1)
    return out


def _cross_sectional_rank(frame: pd.DataFrame) -> pd.DataFrame:
    """Per-date percentile rank of each column (causal: one day at a time)."""
    ranked = np.apply_along_axis(
        _rank_pct_row, 1, frame.to_numpy(dtype="float64")
    ) if len(frame) else np.zeros((0, frame.shape[1]), dtype="float64")
    return pd.DataFrame(ranked, index=frame.index, columns=frame.columns)


def _to_long(
    wide: dict[str, pd.DataFrame], index: pd.DatetimeIndex, symbols: list[str]
) -> pd.DataFrame:
    """Stack aligned wide frames into a long ``(date, symbol, ...)`` frame.

    Row order is the deterministic product ``date x symbol`` (both sorted), which
    is what makes two builds on the same input byte-identical.
    """
    multi = pd.MultiIndex.from_product([index, symbols], names=["date", "symbol"])
    data: dict[str, np.ndarray] = {}
    for name, frame in wide.items():
        aligned = frame.reindex(index=index, columns=symbols)
        data[name] = aligned.to_numpy(dtype="float64").ravel()
    return pd.DataFrame(data, index=multi).reset_index()


# --- public API -------------------------------------------------------------


def build_feature_panel(
    closes: pd.DataFrame,
    volumes: pd.DataFrame | None,
    benchmark: pd.Series,
) -> pd.DataFrame:
    """Long-form ``(date, symbol)`` frame of the phase-1 causal features.

    ``closes`` is a date-indexed frame with one close column per ETF, ``volumes``
    the matching volume frame (``None``, or a frame missing some columns, simply
    yields NaN ``volume_z20``), ``benchmark`` the benchmark close series (SPY).
    Dates are the **inner join** of universe and benchmark (see ``_common_index``).

    Rows are emitted for every ``(date, symbol)`` whose close is known — a symbol
    that had not listed yet contributes no rows, but a symbol with a short history
    keeps its rows with NaN on the long-window features (never dropped, never
    filled). Output columns: ``date``, ``symbol``, ``close``, then
    ``FEATURE_COLUMNS`` in order.
    """
    if closes.empty:
        return pd.DataFrame(columns=IDENTIFIER_COLUMNS + PRICE_COLUMNS + FEATURE_COLUMNS)

    index = _common_index(closes, benchmark)
    symbols = [str(c) for c in closes.columns]
    px = _sorted_float_frame(closes).reindex(index=index)
    bench = cast("pd.Series", _sorted_float_frame(benchmark.to_frame("b")).reindex(index=index)["b"])

    ret = _daily_returns(px)
    bench_ret = cast("pd.Series", bench / bench.shift(1) - 1.0)
    beta_60, corr_60 = _rolling_beta_and_corr(ret, bench_ret, 60)

    bench_frame = pd.DataFrame({s: bench for s in symbols}, index=index)
    rel: dict[int, pd.DataFrame] = {}
    for k in (20, 60, 126):
        asset_k = _trailing_return(px, k)
        bench_k = _trailing_return(bench_frame, k)
        rel[k] = cast("pd.DataFrame", asset_k - bench_k)

    if volumes is None:
        vol_z = pd.DataFrame(np.nan, index=index, columns=symbols)
    else:
        vol_aligned = _sorted_float_frame(volumes).reindex(index=index, columns=symbols)
        vol_z = _volume_zscore(vol_aligned, 20)

    wide: dict[str, pd.DataFrame] = {
        "close": px,
        "ret_5": _trailing_return(px, 5),
        "ret_20": _trailing_return(px, 20),
        "ret_60": _trailing_return(px, 60),
        "ret_126": _trailing_return(px, 126),
        "ret_252": _trailing_return(px, 252),
        "rel_ret_20": rel[20],
        "rel_ret_60": rel[60],
        "rel_ret_126": rel[126],
        "vol_20": _rolling_vol(ret, 20),
        "vol_60": _rolling_vol(ret, 60),
        "downside_vol_60": _rolling_downside_vol(ret, 60),
        "dist_sma50": _dist_to_sma(px, 50),
        "dist_sma200": _dist_to_sma(px, 200),
        "dist_52w_high": _dist_to_rolling_high(px, 252),
        "drawdown": _drawdown(px),
        "beta_60": beta_60,
        "corr_60": corr_60,
        "volume_z20": vol_z,
        "rank_rel_ret_60": _cross_sectional_rank(rel[60]),
    }

    long = _to_long(wide, index, symbols)
    listed = cast("pd.Series", long["close"]).notna()
    long = cast("pd.DataFrame", long[listed]).reset_index(drop=True)
    return cast("pd.DataFrame", long[IDENTIFIER_COLUMNS + PRICE_COLUMNS + FEATURE_COLUMNS])


def build_targets(
    closes: pd.DataFrame,
    benchmark: pd.Series,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
) -> pd.DataFrame:
    """Forward excess-return targets versus the benchmark, per horizon.

    For each ``h``: ``excess_ret_h[t] = fwd_h(asset)[t] - fwd_h(benchmark)[t]``
    where ``fwd_h(x)[t] = x[t+h]/x[t] - 1`` — the value at ``t`` is the outcome
    realised in ``(t, t+h]``, known only at ``t+h``. ``outperform_h`` is its
    strict sign (1.0 when the excess is positive, 0.0 when it is zero or
    negative), left NaN wherever the excess is NaN: the unrealised tail is
    missing, not a loss.

    Long-form ``(date, symbol)`` on the same inner-join index and the same
    "close is known" row filter as ``build_feature_panel``, so the two frames
    align row-for-row.
    """
    for h in horizons:
        if h <= 0:
            raise ValueError(f"horizon must be positive, got {h}")
    cols = target_columns(horizons)
    if closes.empty:
        return pd.DataFrame(columns=IDENTIFIER_COLUMNS + cols)

    index = _common_index(closes, benchmark)
    symbols = [str(c) for c in closes.columns]
    px = _sorted_float_frame(closes).reindex(index=index)
    bench = cast("pd.Series", _sorted_float_frame(benchmark.to_frame("b")).reindex(index=index)["b"])
    bench_frame = pd.DataFrame({s: bench for s in symbols}, index=index)

    wide: dict[str, pd.DataFrame] = {"close": px}
    for h in horizons:
        fwd_asset = cast("pd.DataFrame", px.shift(-h) / px - 1.0)
        fwd_bench = cast("pd.DataFrame", bench_frame.shift(-h) / bench_frame - 1.0)
        excess = cast("pd.DataFrame", fwd_asset - fwd_bench)
        wide[f"excess_ret_{h}"] = excess
        wide[f"outperform_{h}"] = cast(
            "pd.DataFrame", (excess > 0.0).astype("float64").where(excess.notna())
        )

    long = _to_long(wide, index, symbols)
    listed = cast("pd.Series", long["close"]).notna()
    long = cast("pd.DataFrame", long[listed]).reset_index(drop=True)
    return cast("pd.DataFrame", long[IDENTIFIER_COLUMNS + cols])


def assemble(
    features: pd.DataFrame,
    targets: pd.DataFrame,
    regime: pd.Series,
) -> pd.DataFrame:
    """Join features, targets and the per-date market regime into one panel.

    ``regime`` is a date-indexed label series — in production
    ``combine_regimes(classify_regime(spy), classify_vol_regime(spy_returns))``,
    i.e. a 4-state ``bull/bear x high/low vol`` label computed from benchmark
    **prices only** (decision D12: no macro in phase 1, and prices keep the label
    causal). Dates the regime does not cover are labelled ``"unknown"`` rather
    than guessed or forward-filled.

    Features are the spine (left join): a ``(date, symbol)`` with no target row
    keeps NaN targets. Row order is ``(date, symbol)`` and the schema is recorded
    in ``.attrs`` for ``dataset_metadata``.
    """
    merged = features.merge(
        targets, on=IDENTIFIER_COLUMNS, how="left", validate="one_to_one"
    )
    labels = regime.astype("object")
    labels = cast("pd.Series", labels[~pd.Index(labels.index).duplicated(keep="last")])
    # reindex, not map: a duplicate-free date -> label lookup that leaves the
    # dates the regime does not cover as NaN, which then become "unknown".
    aligned = labels.reindex(pd.DatetimeIndex(merged["date"]))
    merged["regime"] = [
        "unknown" if pd.isna(v) else str(v) for v in aligned.to_numpy(dtype="object")
    ]

    ordered = merged.sort_values(IDENTIFIER_COLUMNS).reset_index(drop=True)
    target_cols = [c for c in ordered.columns if c.startswith(("excess_ret_", "outperform_"))]
    ordered.attrs["schema_version"] = SCHEMA_VERSION
    ordered.attrs["features"] = list(FEATURE_COLUMNS)
    ordered.attrs["targets"] = target_cols
    return ordered


def coverage_report(panel: pd.DataFrame) -> pd.DataFrame:
    """Per-symbol coverage: rows, date range, and the share of missing features.

    The report a human reads before trusting a build: a symbol whose history
    starts in 2018 *should* show a high missing share on the 252-day features,
    and one that shows an unexpected gap is a broken feed, not a short history.
    """
    if panel.empty:
        return pd.DataFrame(
            columns=["symbol", "rows", "first_date", "last_date", "missing_feature_pct"]
        )
    present = [c for c in FEATURE_COLUMNS if c in panel.columns]
    rows: list[dict[str, object]] = []
    for symbol, group in panel.groupby("symbol", sort=True):
        block = cast("pd.DataFrame", group[present])
        total = int(block.size)
        missing = int(block.isna().to_numpy().sum())
        dates = cast("pd.Series", group["date"])
        rows.append(
            {
                "symbol": str(symbol),
                "rows": len(group),
                "first_date": str(dates.min())[:10],
                "last_date": str(dates.max())[:10],
                "missing_feature_pct": (100.0 * missing / total) if total else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def dataset_metadata(panel: pd.DataFrame) -> dict[str, object]:
    """Reproducibility metadata for a built panel (written next to the parquet).

    Carries the schema hash so a downstream consumer can refuse a panel built
    with a different feature set instead of silently training on it.
    """
    columns = [str(c) for c in panel.columns]
    schema_hash = hashlib.sha256(",".join(columns).encode("utf-8")).hexdigest()[:16]
    features = cast("list[str]", panel.attrs.get("features", FEATURE_COLUMNS))
    targets = cast("list[str]", panel.attrs.get("targets", target_columns()))
    dates = cast("pd.Series", panel["date"]) if "date" in panel.columns else pd.Series([], dtype="object")
    symbols = (
        sorted({str(s) for s in cast("pd.Series", panel["symbol"])})
        if "symbol" in panel.columns
        else []
    )
    return {
        "schema_version": panel.attrs.get("schema_version", SCHEMA_VERSION),
        "schema_hash": schema_hash,
        "rows": len(panel),
        "columns": columns,
        "features": list(features),
        "targets": list(targets),
        "symbols": symbols,
        "n_symbols": len(symbols),
        "date_start": str(dates.min())[:10] if len(dates) else None,
        "date_end": str(dates.max())[:10] if len(dates) else None,
    }
