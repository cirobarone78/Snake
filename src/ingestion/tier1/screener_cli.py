"""CLI: print the crypto narrative screener briefing (Fase 6).

Reads the persisted category snapshot (``data/category_history/
categories_latest.parquet``) and prints the "opportunities / risks now" report.
With ``--live`` it fetches a fresh snapshot from CoinGecko instead.

Run:
  uv run python -m src.ingestion.tier1.screener_cli           # from saved snapshot
  uv run python -m src.ingestion.tier1.screener_cli --live    # fresh fetch
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.features.screener_report import format_report

DEFAULT_SNAPSHOT = Path("data/category_history/categories_latest.parquet")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crypto narrative screener briefing.")
    parser.add_argument(
        "--live", action="store_true", help="Fetch a fresh snapshot from CoinGecko."
    )
    parser.add_argument(
        "--snapshot", default=str(DEFAULT_SNAPSHOT), help="Path to a saved snapshot parquet."
    )
    parser.add_argument("--top", type=int, default=8, help="How many strong narratives to show.")
    args = parser.parse_args()

    if args.live:
        from src.ingestion.tier1.coingecko import CoinGeckoSource

        categories = CoinGeckoSource().fetch_categories(min_market_cap=1e8)
    else:
        path = Path(args.snapshot)
        if not path.exists():
            raise SystemExit(
                f"Snapshot non trovato: {path}\n"
                "Esegui prima `uv run python -m src.ingestion.tier1.fetch_categories` "
                "oppure usa --live."
            )
        categories = pd.read_parquet(path)

    print(format_report(categories, top_n=args.top))


if __name__ == "__main__":
    main()
