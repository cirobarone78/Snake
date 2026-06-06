"""Build the market price-series JSON for the dashboard hero chart (Fase 7).

Fetches ~1 year of daily closes for a few headline assets (BTC, ETH, the S&P 500,
gold) and writes ``public/data/market_series.json`` — the data behind the
stock-style line chart on the dashboard. Free Yahoo data only; tolerant of a
flaky single feed.

Run:  uv run python -m src.ingestion.tier1.build_market_series
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.assets.asset import get_asset_by_symbol
from src.features.market_series import build_market_series
from src.features.report_json import write_report_json
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

JSON_PATH = Path("public/data/market_series.json")
# Display label per headline symbol.
HEADLINE: dict[str, str] = {"BTC": "Bitcoin", "ETH": "Ethereum", "SPX": "S&P 500", "GOLD": "Oro"}
FETCH_START = "2025-01-01"


def main() -> None:
    src = YahooFinanceSource()
    closes: dict[str, pd.Series] = {}
    for symbol in HEADLINE:
        asset = get_asset_by_symbol(symbol)
        if asset is None:
            continue
        try:
            ohlcv = src.fetch_ohlcv(asset, start=FETCH_START, interval="1d")
        except Exception:  # tolerate a flaky single feed
            logger.exception("Failed to fetch %s", symbol)
            continue
        if not ohlcv.empty:
            closes[symbol] = ohlcv["close"]

    if not closes:
        raise SystemExit("No market series fetched.")

    now = pd.Timestamp.now(tz="UTC").floor("min")
    payload = build_market_series(closes, names=HEADLINE, window=365, generated_at=now)
    write_report_json(payload, JSON_PATH)
    logger.info("Wrote %s (%d series)", JSON_PATH, len(payload["series"]))


if __name__ == "__main__":
    main()
