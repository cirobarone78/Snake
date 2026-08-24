# pyright: strict, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Build the point-in-time ETF panel from Yahoo daily bars (WP2, ADR-032).

Fetches the 20 sector/theme ETFs of the rotation universe (decision D1) plus the
SPY benchmark (D2), builds the causal feature panel and the forward excess-return
targets of ``src/features/etf_dataset``, attaches the price-only market regime,
and writes the result to ``data/processed/`` (gitignored: it is derived data,
rebuildable from this command).

Run:  uv run python -m src.ingestion.tier1.build_etf_dataset

Outputs:
  data/processed/etf_panel.parquet       the long-form (date, symbol) panel
  data/processed/etf_panel_meta.json     schema, coverage, provenance

The fetch is the only impure part of WP2 and it lives here on purpose: the
feature module must stay offline-testable, because the development sandbox
cannot reach ``fc.yahoo.com`` (yfinance's cookie bootstrap) while CI can. If this
script fails locally with a Yahoo error, that is the sandbox — run it in CI.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import cast

import pandas as pd

from src.assets.asset import Asset, get_asset_by_symbol
from src.assets.sectors import SECTOR_ETFS
from src.features.etf_dataset import (
    DEFAULT_HORIZONS,
    assemble,
    build_feature_panel,
    build_targets,
    coverage_report,
    dataset_metadata,
)
from src.features.regime import classify_regime, classify_vol_regime, combine_regimes
from src.ingestion.freshness import check_freshness, last_timestamp_of
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

OUT_DIR = Path("data/processed")
PANEL_PATH = OUT_DIR / "etf_panel.parquet"
META_PATH = OUT_DIR / "etf_panel_meta.json"
BENCHMARK_SYMBOL = "SPY"

# 2005 predates every fund in the universe except the 1998 SPDR sector series,
# so the panel starts as early as the data allows without a per-fund calendar.
# Funds that listed later (ITA 2006, ICLN 2008, URA 2010, BOTZ/CIBR ~2016,
# XLC 2018) simply contribute no rows before their first bar — they are never
# excluded, and their long-window features stay NaN until the history supports
# them (see the etf_dataset docstring).
DEFAULT_START = "2005-01-01"
# A daily feed more than 5 sessions old is a frozen ticker, not a long weekend.
MAX_AGE_DAYS = 5.0


def _fetch_close_volume(
    source: YahooFinanceSource, assets: list[Asset], start: str
) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    """Fetch daily bars per asset, returning the close and volume series.

    A symbol that fails or comes back empty is logged and skipped rather than
    aborting the build: a 20-fund panel missing one fund is still useful, a
    silent half-panel is not — the coverage report at the end makes the gap
    visible.
    """
    closes: dict[str, pd.Series] = {}
    volumes: dict[str, pd.Series] = {}
    for asset in assets:
        try:
            ohlcv = source.fetch_ohlcv(asset, start=start, interval="1d")
        except Exception:
            logger.exception("Failed to fetch %s (%s)", asset.symbol, asset.yahoo_symbol)
            continue
        if ohlcv.empty:
            logger.warning("No data for %s (%s)", asset.symbol, asset.yahoo_symbol)
            continue
        fresh = check_freshness(
            last_timestamp_of(ohlcv), max_age_days=MAX_AGE_DAYS, name=asset.symbol
        )
        if not fresh.is_fresh:
            logger.warning("STALE FEED: %s", fresh.message())
        closes[asset.symbol] = cast("pd.Series", ohlcv["close"])
        volumes[asset.symbol] = cast("pd.Series", ohlcv["volume"])
    return closes, volumes


def benchmark_regime(benchmark: pd.Series) -> pd.Series:
    """4-state ``trend x vol`` regime from benchmark prices only (decision D12).

    Public because the weekly rotation runner (WP4) rebuilds the same panel from
    bars it has already fetched, and a second definition of "the regime" would be
    a second thing to keep in sync.

    Both classifiers are causal (trailing SMA, trailing realised vol vs its own
    trailing median), so the label at ``t`` is knowable at ``t``. No macro series
    enters phase 1: a revised FRED print would be look-ahead in disguise.
    """
    returns = cast("pd.Series", benchmark / benchmark.shift(1) - 1.0)
    return combine_regimes(classify_regime(benchmark), classify_vol_regime(returns))


def build(start: str = DEFAULT_START) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Fetch, build and return ``(panel, coverage)``; ``None`` when data is missing."""
    benchmark_asset = get_asset_by_symbol(BENCHMARK_SYMBOL)
    if benchmark_asset is None:  # pragma: no cover - registry is a constant
        raise RuntimeError(f"{BENCHMARK_SYMBOL} missing from the asset registry")

    source = YahooFinanceSource()
    bench_closes, _ = _fetch_close_volume(source, [benchmark_asset], start)
    benchmark = bench_closes.get(BENCHMARK_SYMBOL)
    if benchmark is None or benchmark.empty:
        logger.error("No benchmark data (%s): cannot build excess returns.", BENCHMARK_SYMBOL)
        return None

    closes, volumes = _fetch_close_volume(source, SECTOR_ETFS, start)
    if not closes:
        logger.error("No ETF data fetched; nothing to build.")
        return None

    close_frame = pd.DataFrame(closes)
    volume_frame = pd.DataFrame(volumes)
    features = build_feature_panel(close_frame, volume_frame, benchmark)
    targets = build_targets(close_frame, benchmark, horizons=DEFAULT_HORIZONS)
    panel = assemble(features, targets, benchmark_regime(benchmark))
    return panel, coverage_report(panel)


def _log_coverage(coverage: pd.DataFrame, panel: pd.DataFrame) -> None:
    logger.info("Coverage by symbol (rows / range / missing feature share):")
    for row in coverage.to_dict("records"):
        logger.info(
            "  %-14s %6d rows  %s -> %s  missing %5.1f%%",
            row["symbol"], row["rows"], row["first_date"], row["last_date"],
            row["missing_feature_pct"],
        )
    regimes = cast("pd.Series", panel["regime"]).value_counts()
    logger.info("Regime mix: %s", ", ".join(f"{k}={v}" for k, v in regimes.items()))
    for horizon in DEFAULT_HORIZONS:
        col = f"outperform_{horizon}"
        realised = cast("pd.Series", panel[col]).dropna()
        share = float(realised.mean()) if len(realised) else float("nan")
        logger.info(
            "Target %s: %d realised rows, unconditional outperformance %.3f",
            col, len(realised), share,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default=DEFAULT_START, help="first bar to fetch (YYYY-MM-DD)")
    args = parser.parse_args()

    built = build(start=str(args.start))
    if built is None:
        return
    panel, coverage = built

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL_PATH, engine="pyarrow", compression="snappy", index=False)

    meta = dataset_metadata(panel)
    meta["source"] = "yahoo"
    meta["fetch_start"] = str(args.start)
    meta["built_at"] = str(pd.Timestamp.now(tz="UTC").floor("s"))
    meta["benchmark"] = BENCHMARK_SYMBOL
    meta["horizons"] = list(DEFAULT_HORIZONS)
    meta["coverage"] = coverage.to_dict("records")
    META_PATH.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")

    _log_coverage(coverage, panel)
    logger.info(
        "Wrote %d rows x %d columns -> %s (meta -> %s)",
        len(panel), len(panel.columns), PANEL_PATH, META_PATH,
    )


if __name__ == "__main__":
    main()
