"""CLI: explain an asset's recent abrupt moves with candidate events (Fase 3/8).

Fetches an asset's prices + (for crypto) the collected news history and prints the
recent abnormal moves, each labelled market-wide / asset-specific and — for crypto
— annotated with the most plausible triggering news (recency + sentiment aligned
with the move).

Works on two universes:
  * **Crypto** (BTC/ETH/SOL/LINK/POL): market reference = BTC, news = the crypto
    news history we collect, asset-named source up-weighted.
  * **Equity sector/theme ETFs** (e.g. SEMIS, ENERGY, URANIUM): market reference =
    S&P 500, with a lower market threshold (an equity market day is "big" at ~1%,
    not 3%). News attribution is intentionally OFF here: our news history is
    crypto-only, so attaching it to an ETF would be misleading (VISION #1). For
    ETFs the deliverable is the honest market-wide / sector-specific split until an
    equity news source is wired in.

Honest by design (VISION #1): it lists *candidate* catalysts ranked by
plausibility — association, not proven causation. A move with no news attached is
flagged as such (leverage/liquidations with no headline, or no news source yet).

Run:
  uv run python -m src.ingestion.tier1.attribution_cli BTC
  uv run python -m src.ingestion.tier1.attribution_cli SOL --z 3 --days 60
  uv run python -m src.ingestion.tier1.attribution_cli SEMIS        # equity ETF
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.assets.asset import Asset, AssetClass, get_asset_by_symbol
from src.assets.sectors import get_sector_by_symbol
from src.features.move_attribution import attribute_moves
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

NEWS_PATH = Path("data/news_history/news.parquet")


def _resolve_asset(symbol: str) -> Asset | None:
    """Find an asset across the crypto/context universe and the sector ETFs."""
    return get_asset_by_symbol(symbol) or get_sector_by_symbol(symbol)


def main() -> None:
    parser = argparse.ArgumentParser(description="Explain abrupt price moves with events.")
    parser.add_argument(
        "symbol", help="Asset symbol: crypto (BTC, ETH, SOL, LINK, POL) or sector ETF (SEMIS, ENERGY, ...)."
    )
    parser.add_argument("--z", type=float, default=2.5, help="Abnormality z-threshold.")
    parser.add_argument("--days", type=int, default=90, help="Lookback window in days.")
    parser.add_argument("--max", type=int, default=8, help="Max moves to show.")
    args = parser.parse_args()

    asset = _resolve_asset(args.symbol.upper())
    if asset is None:
        raise SystemExit(f"Unknown symbol: {args.symbol}")

    is_crypto = asset.asset_class == AssetClass.CRYPTO
    # Market reference + "big market day" threshold differ by asset class: BTC at
    # ~3% for crypto, the S&P 500 at ~1% for equities.
    market_symbol = "BTC" if is_crypto else "SPX"
    market_asset = get_asset_by_symbol(market_symbol)
    market_threshold_pct = 3.0 if is_crypto else 1.0

    # News attribution only for crypto (our news history is crypto-only).
    if is_crypto:
        if not NEWS_PATH.exists():
            raise SystemExit(f"News history not found at {NEWS_PATH}.")
        news = pd.read_parquet(NEWS_PATH)
        asset_source: str | None = f"googlenews_{asset.symbol.lower()}"
    else:
        news = pd.DataFrame()
        asset_source = None

    start = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=args.days + 40)).date().isoformat()
    src = YahooFinanceSource()
    close = src.fetch_ohlcv(asset, start=start, interval="1d").sort_index()["close"]
    market = None
    if market_asset is not None:
        market = src.fetch_ohlcv(market_asset, start=start, interval="1d").sort_index()["close"]

    moves = attribute_moves(
        close, news, asset_source=asset_source, market_close=market,
        z_threshold=args.z, window_days=2, top_k=3,
        market_threshold_pct=market_threshold_pct,
    )
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=args.days)
    moves = [m for m in moves if m.date >= cutoff][: args.max]

    ref_label = "BTC" if is_crypto else "S&P 500"
    print(
        f"\n=== Movimenti anomali di {asset.symbol} ({asset.name}) "
        f"| |z|>={args.z}, ultimi {args.days}g, rif. mercato {ref_label} ===\n"
    )
    if not moves:
        print("Nessun movimento anomalo nel periodo.")
        return
    for m in moves:
        mkt = f", mercato {m.market_return_pct:+.1f}%" if m.market_return_pct is not None else ""
        print(
            f"📅 {m.date.date()}  {m.return_pct:+.1f}%  (z={m.zscore:+.1f})  "
            f"[{m.classification}{mkt}]"
        )
        if m.candidate_events:
            for e in m.candidate_events:
                print(f"    • [rel {e['relevance']}] {e['source']}: {str(e['title'])[:72]}")
        elif is_crypto:
            print("    • nessuna news associata (possibile evento di leva/liquidazioni)")
        else:
            print("    • news azionarie non ancora collegate (solo classificazione)")
        print()
    if is_crypto:
        print(
            "Nota: eventi CANDIDATI ordinati per plausibilità (vicinanza + sentiment "
            "coerente). Associazione, non causazione."
        )
    else:
        print(
            "Nota: per gli ETF azionari mostriamo solo market-wide vs settore-specifico "
            "(rif. S&P 500). La fonte news azionaria non è ancora collegata."
        )


if __name__ == "__main__":
    main()
