"""Build the dashboard events JSON: recent abnormal moves + candidate causes.

Runs move attribution against the collected news history for two universes:
  * **Crypto majors** (Tier-1): market reference = BTC, crypto news sources.
  * **Equity sectors/themes** (ETFs): market reference = the S&P 500, per-sector
    news sources, with the equity-sized "big market day" threshold.

Writes ``public/data/events.json`` — the data behind the dashboard "Eventi"
section. Honest by design: candidate catalysts, not proven causes; a move with no
news in its window is flagged as such (equity news history is still young, so many
ETF moves show classification only for now).

Run:  uv run python -m src.ingestion.tier1.build_events
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.assets.asset import TIER1_ASSETS, Asset, get_asset_by_symbol
from src.assets.sectors import SECTOR_ETFS
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


def _attribute_universe(
    assets: list[Asset],
    src: YahooFinanceSource,
    news_all: pd.DataFrame,
    market: pd.Series | None,
    start: str,
    cutoff: pd.Timestamp,
    *,
    is_crypto: bool,
    universe: str,
    skip_empty: bool,
) -> list[dict[str, Any]]:
    """Attribute recent abnormal moves for one universe of assets."""
    threshold = 3.0 if is_crypto else 1.0
    out: list[dict[str, Any]] = []
    for asset in assets:
        try:
            close = src.fetch_ohlcv(asset, start=start, interval="1d").sort_index()["close"]
        except Exception:
            logger.exception("Failed to fetch %s", asset.symbol)
            continue
        if close.empty:
            continue
        asset_source = f"googlenews_{asset.symbol.lower()}"
        relevant = {asset_source} | (CRYPTO_NEWSWIRES if is_crypto else set())
        news = news_all[news_all["source"].isin(relevant)] if not news_all.empty else news_all
        moves = attribute_moves(
            close, news, asset_source=asset_source, market_close=market,
            z_threshold=Z_THRESHOLD, window_days=2, top_k=3, market_threshold_pct=threshold,
        )
        moves = [m for m in moves if m.date >= cutoff][:MAX_MOVES]
        if skip_empty and not moves:
            continue
        out.append({"symbol": asset.symbol, "name": asset.name, "universe": universe, "moves": moves})
    return out


def main() -> None:
    if not NEWS_PATH.exists():
        raise SystemExit(f"News history not found at {NEWS_PATH}.")
    news_all = pd.read_parquet(NEWS_PATH)

    start = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=LOOKBACK_DAYS + 40)).date().isoformat()
    src = YahooFinanceSource()
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=LOOKBACK_DAYS)

    def _close(symbol: str) -> pd.Series | None:
        asset = get_asset_by_symbol(symbol)
        if asset is None:
            return None
        return src.fetch_ohlcv(asset, start=start, interval="1d").sort_index()["close"]

    btc = _close("BTC")
    spx = _close("SPX")

    crypto = _attribute_universe(
        TIER1_ASSETS, src, news_all, btc, start, cutoff,
        is_crypto=True, universe="crypto", skip_empty=False,
    )
    equity = _attribute_universe(
        SECTOR_ETFS, src, news_all, spx, start, cutoff,
        is_crypto=False, universe="equity", skip_empty=True,
    )

    now = pd.Timestamp.now(tz="UTC").floor("min")
    write_report_json(build_events_payload(crypto + equity, generated_at=now), JSON_PATH)
    total = sum(len(a["moves"]) for a in crypto + equity)
    logger.info(
        "Wrote %s (%d crypto, %d equity assets, %d moves)",
        JSON_PATH, len(crypto), len(equity), total,
    )


if __name__ == "__main__":
    main()
