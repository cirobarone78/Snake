"""CLI: explain an asset's recent abrupt moves with candidate events (Fase 3).

Fetches an asset's prices + the collected news history and prints the recent
abnormal moves, each labelled market-wide / asset-specific and annotated with the
most plausible triggering news (recency + sentiment aligned with the move).

Honest by design (VISION #1): it lists *candidate* catalysts ranked by
plausibility — association, not proven causation. A move with no news attached is
flagged as such (it may be leverage/liquidations with no headline).

Run:
  uv run python -m src.ingestion.tier1.attribution_cli BTC
  uv run python -m src.ingestion.tier1.attribution_cli SOL --z 3 --days 60
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.assets.asset import get_asset_by_symbol
from src.features.move_attribution import attribute_moves
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

NEWS_PATH = Path("data/news_history/news.parquet")


def main() -> None:
    parser = argparse.ArgumentParser(description="Explain abrupt price moves with events.")
    parser.add_argument("symbol", help="Asset symbol, e.g. BTC, ETH, SOL, LINK, POL.")
    parser.add_argument("--z", type=float, default=2.5, help="Abnormality z-threshold.")
    parser.add_argument("--days", type=int, default=90, help="Lookback window in days.")
    parser.add_argument("--max", type=int, default=8, help="Max moves to show.")
    args = parser.parse_args()

    asset = get_asset_by_symbol(args.symbol.upper())
    if asset is None:
        raise SystemExit(f"Unknown symbol: {args.symbol}")
    if not NEWS_PATH.exists():
        raise SystemExit(f"News history not found at {NEWS_PATH}.")

    news = pd.read_parquet(NEWS_PATH)
    start = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=args.days + 40)).date().isoformat()
    src = YahooFinanceSource()
    close = src.fetch_ohlcv(asset, start=start, interval="1d").sort_index()["close"]
    market = src.fetch_ohlcv(
        get_asset_by_symbol("BTC"), start=start, interval="1d"
    ).sort_index()["close"]

    asset_source = f"googlenews_{asset.symbol.lower()}"
    moves = attribute_moves(
        close, news, asset_source=asset_source, market_close=market,
        z_threshold=args.z, window_days=2, top_k=3,
    )
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=args.days)
    moves = [m for m in moves if m.date >= cutoff][: args.max]

    print(f"\n=== Movimenti anomali di {asset.symbol} (|z|>={args.z}, ultimi {args.days}g) ===\n")
    if not moves:
        print("Nessun movimento anomalo nel periodo.")
        return
    for m in moves:
        print(f"📅 {m.date.date()}  {m.return_pct:+.1f}%  (z={m.zscore:+.1f})  [{m.classification}]")
        if m.candidate_events:
            for e in m.candidate_events:
                print(f"    • [rel {e['relevance']}] {e['source']}: {str(e['title'])[:72]}")
        else:
            print("    • nessuna news associata (possibile evento di leva/liquidazioni)")
        print()
    print(
        "Nota: eventi CANDIDATI ordinati per plausibilità (vicinanza + sentiment "
        "coerente). Associazione, non causazione."
    )


if __name__ == "__main__":
    main()
