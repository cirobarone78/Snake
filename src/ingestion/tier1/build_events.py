"""Build the dashboard events JSON: recent abnormal moves + candidate causes.

Runs move attribution for the Tier-1 crypto majors against the collected news
history and writes ``public/data/events.json`` — the data behind the dashboard
"Eventi" section. Honest by design: candidate catalysts, not proven causes; a move
with no news in its window is flagged as such.

Run:  uv run python -m src.ingestion.tier1.build_events
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.assets.asset import TIER1_ASSETS, get_asset_by_symbol
from src.features.events_export import build_events_payload
from src.features.move_attribution import attribute_moves
from src.features.report_json import write_report_json
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

NEWS_PATH = Path("data/news_history/news.parquet")
JSON_PATH = Path("public/data/events.json")
CRYPTO_NEWSWIRES = {"cointelegraph", "coindesk"}

LOOKBACK_DAYS = 90
Z_THRESHOLD = 2.5
MAX_MOVES = 6


def main() -> None:
    if not NEWS_PATH.exists():
        raise SystemExit(f"News history not found at {NEWS_PATH}.")
    news_all = pd.read_parquet(NEWS_PATH)

    start = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=LOOKBACK_DAYS + 40)).date().isoformat()
    src = YahooFinanceSource()
    btc = get_asset_by_symbol("BTC")
    market = (
        src.fetch_ohlcv(btc, start=start, interval="1d").sort_index()["close"]
        if btc is not None
        else None
    )
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=LOOKBACK_DAYS)

    asset_moves: list[dict[str, Any]] = []
    for asset in TIER1_ASSETS:
        try:
            close = src.fetch_ohlcv(asset, start=start, interval="1d").sort_index()["close"]
        except Exception:
            logger.exception("Failed to fetch %s", asset.symbol)
            continue
        if close.empty:
            continue
        asset_source = f"googlenews_{asset.symbol.lower()}"
        relevant = {asset_source} | CRYPTO_NEWSWIRES
        news = news_all[news_all["source"].isin(relevant)] if not news_all.empty else news_all
        moves = attribute_moves(
            close, news, asset_source=asset_source, market_close=market,
            z_threshold=Z_THRESHOLD, window_days=2, top_k=3, market_threshold_pct=3.0,
        )
        moves = [m for m in moves if m.date >= cutoff][:MAX_MOVES]
        asset_moves.append({"symbol": asset.symbol, "name": asset.name, "moves": moves})

    now = pd.Timestamp.now(tz="UTC").floor("min")
    write_report_json(build_events_payload(asset_moves, generated_at=now), JSON_PATH)
    total = sum(len(a["moves"]) for a in asset_moves)
    logger.info("Wrote %s (%d assets, %d moves)", JSON_PATH, len(asset_moves), total)


if __name__ == "__main__":
    main()
