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
from src.features.events_export import build_events_payload, days_since_last_major
from src.features.move_attribution import attribute_moves, market_pulse
from src.features.news_volume import annotate_moves_with_coverage, daily_news_volume
from src.features.report_json import write_report_json
from src.ingestion.news.feeds import WORLD_SOURCE_NAMES
from src.ingestion.news.history import DEFAULT_HISTORY_DIR, read_news_history
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

NEWS_DIR = DEFAULT_HISTORY_DIR
JSON_PATH = Path("public/data/events.json")
CRYPTO_NEWSWIRES = {"cointelegraph", "coindesk"}

LOOKBACK_DAYS = 90
Z_THRESHOLD = 2.5
# Lower-confidence tier: |z| in [NOTABLE_Z, Z_THRESHOLD) shows as "notable" so
# the dashboard degrades gracefully in calm stretches instead of going silent.
NOTABLE_Z = 1.5
# Regime-robust absolute floors (a z-only trigger self-blinds when the rolling
# vol is inflated by a turbulent regime — e.g. bear-market BTC needs ±7%/day to
# reach |z|=2.5). Any day at/above the floor is an event regardless of z.
RETURN_FLOOR_PCT_CRYPTO = 4.0
RETURN_FLOOR_PCT_EQUITY = 2.5
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
    floor = RETURN_FLOOR_PCT_CRYPTO if is_crypto else RETURN_FLOOR_PCT_EQUITY
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
        # World/macro sources are always in the candidate pool; the attribution
        # weighting only promotes them on market-wide days.
        relevant = (
            {asset_source}
            | (CRYPTO_NEWSWIRES if is_crypto else set())
            | set(WORLD_SOURCE_NAMES)
        )
        news = news_all[news_all["source"].isin(relevant)] if not news_all.empty else news_all
        moves = attribute_moves(
            close, news, asset_source=asset_source, market_close=market,
            z_threshold=Z_THRESHOLD, window_days=2, top_k=3, market_threshold_pct=threshold,
            return_floor_pct=floor, notable_z=NOTABLE_Z,
            market_sources=set(WORLD_SOURCE_NAMES),
        )
        moves = [m for m in moves if m.date >= cutoff][:MAX_MOVES]
        # D2: annotate each move with the asset feed's same-day coverage — a
        # price move plus a headline-count spike is a stronger event marker.
        counts = daily_news_volume(news_all, asset_source)
        if not counts.empty:
            moves = annotate_moves_with_coverage(moves, counts)
        if skip_empty and not moves:
            continue
        out.append({"symbol": asset.symbol, "name": asset.name, "universe": universe, "moves": moves})
    return out


def main() -> None:
    # ADR-033: the history is a set of monthly partitions; the reader hides that.
    news_all = read_news_history(NEWS_DIR)
    if news_all.empty:
        raise SystemExit(f"News history not found (or empty) under {NEWS_DIR}.")

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
    pulse: dict[str, Any] = {}
    if btc is not None and not btc.empty:
        pulse["crypto"] = {
            **market_pulse(btc),
            "benchmark": "BTC",
            "days_since_last_major": days_since_last_major(crypto, now),
        }
    if spx is not None and not spx.empty:
        pulse["equity"] = {
            **market_pulse(spx),
            "benchmark": "SPX",
            "days_since_last_major": days_since_last_major(equity, now),
        }

    write_report_json(
        build_events_payload(crypto + equity, generated_at=now, market_pulse=pulse or None),
        JSON_PATH,
    )
    total = sum(len(a["moves"]) for a in crypto + equity)
    logger.info(
        "Wrote %s (%d crypto, %d equity assets, %d moves)",
        JSON_PATH, len(crypto), len(equity), total,
    )


if __name__ == "__main__":
    main()
