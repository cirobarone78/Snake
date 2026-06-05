"""CLI: the probabilistic rotation layer on real history.

"Given a rotation state (a sector's cross-sectional momentum bucket), what did the
forward return look like historically?" Fetches years of sector-ETF closes, builds
a point-in-time panel, and prints the conditional forward-return table per bucket
(weak/mid/strong) vs the unconditional baseline, for a few horizons.

Honest by design (CLAUDE.md): the state is reconstructed point-in-time (no
look-ahead), but the reported ``n`` counts *overlapping* daily observations, so
bucket differences are **indicative, not significant**. This is a description of
the past distribution, never a promise about the future.

Run:
  uv run python -m src.ingestion.tier1.rotation_history_cli
  uv run python -m src.ingestion.tier1.rotation_history_cli --lookback 63 --start 2010-01-01
"""

from __future__ import annotations

import argparse

import pandas as pd

from src.assets.sectors import SECTOR_ETFS
from src.features.conditional_outcomes import rotation_outcomes
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

DEFAULT_START = "2012-01-01"
DEFAULT_HORIZONS = (5, 21, 63)  # ~1 week, ~1 month, ~1 quarter (trading days)


def build_panel(start: str) -> pd.DataFrame:
    """Fetch each sector ETF's daily close and assemble a date x symbol panel."""
    src = YahooFinanceSource()
    closes: dict[str, pd.Series] = {}
    for asset in SECTOR_ETFS:
        try:
            ohlcv = src.fetch_ohlcv(asset, start=start, interval="1d")
        except Exception:  # tolerate a flaky single feed
            continue
        if not ohlcv.empty:
            closes[asset.symbol] = ohlcv["close"]
    if not closes:
        return pd.DataFrame()
    return pd.concat(closes, axis=1).sort_index()


def main() -> None:
    parser = argparse.ArgumentParser(description="Probabilistic rotation layer on history.")
    parser.add_argument("--start", default=DEFAULT_START, help="History start date (YYYY-MM-DD).")
    parser.add_argument("--lookback", type=int, default=21, help="Momentum lookback (days).")
    parser.add_argument("--buckets", type=int, default=3, help="Cross-sectional buckets.")
    args = parser.parse_args()

    panel = build_panel(args.start)
    if panel.empty:
        raise SystemExit("No sector data fetched.")

    span = f"{panel.index.min().date()} → {panel.index.max().date()}"
    print(f"\n=== Layer probabilistico rotazione settoriale (equity) — {span} ===")
    print(f"Universo: {panel.shape[1]} ETF | lookback momentum: {args.lookback}g | "
          f"bucket cross-sectional: {args.buckets}")
    print("Ipotesi (scritte prima): H1 il momentum di settore persiste a 1-3 mesi "
          "(strong > baseline); H2 a 5g possibile lieve reversione; H3 differenze "
          "piccole e n gonfiato da overlap → indicativo.\n")

    for horizon in DEFAULT_HORIZONS:
        table = rotation_outcomes(
            panel, lookback=args.lookback, horizon=horizon, n_buckets=args.buckets
        )
        print(f"--- Forward {horizon}g | stato = bucket momentum {args.lookback}g ---")
        print(table.to_string(index=False))
        base = table[table["state"] == "ALL"].iloc[0]
        strong = table[table["state"] == "strong"]
        if not strong.empty:
            s = strong.iloc[0]
            d_hit = (s["hit_rate"] - base["hit_rate"]) * 100.0
            d_mean = s["mean_fwd_pct"] - base["mean_fwd_pct"]
            print(f"  strong vs baseline: hit-rate {d_hit:+.1f}pp, media {d_mean:+.2f}pp")
        print()

    print("Nota: stato ricostruito point-in-time (no look-ahead); n = osservazioni "
          "giornaliere SOVRAPPOSTE → differenze indicative, non significative. "
          "Descrizione del passato, non promessa sul futuro.")


if __name__ == "__main__":
    main()
