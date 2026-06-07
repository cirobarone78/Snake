"""Build the data-health JSON: cross-source price check for the Tier-1 majors.

For each Tier-1 crypto, compares the latest Yahoo close with the latest CoinGecko
price and flags large divergences (a frozen/wrong feed). Writes
``public/data/data_health.json`` for the dashboard. Honest hardening, not a signal.

Run:  uv run python -m src.ingestion.tier1.build_data_health
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import pandas as pd

from src.assets.asset import TIER1_ASSETS
from src.features.report_json import write_report_json
from src.ingestion.tier1.coingecko import CoinGeckoSource
from src.quality.cross_source import cross_source_check

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

JSON_PATH = Path("public/data/data_health.json")


def _round(value: float | None, ndigits: int = 6) -> float | None:
    return None if value is None else round(value, ndigits)


def _last_price(frame: pd.DataFrame, column: str) -> float | None:
    s = frame[column].dropna() if not frame.empty and column in frame else pd.Series(dtype="float64")
    return float(s.iloc[-1]) if len(s) else None


def main() -> None:
    from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

    yahoo = YahooFinanceSource()
    cg = CoinGeckoSource()
    start = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=10)).date().isoformat()

    assets: list[dict[str, Any]] = []
    for asset in TIER1_ASSETS:
        yahoo_price: float | None = None
        try:
            yahoo_price = _last_price(yahoo.fetch_ohlcv(asset, start=start, interval="1d"), "close")
        except Exception:
            logger.exception("Yahoo fetch failed for %s", asset.symbol)
        cg_price: float | None = None
        if asset.coingecko_id:
            try:
                cg_price = _last_price(cg.fetch_market_chart(asset.coingecko_id, days=2), "price")
            except Exception:
                logger.exception("CoinGecko fetch failed for %s", asset.symbol)
            time.sleep(2.0)  # pace the free CoinGecko tier
        result = cross_source_check(yahoo_price, cg_price)
        assets.append(
            {
                "symbol": asset.symbol,
                "name": asset.name,
                "yahoo": _round(yahoo_price),
                "coingecko": _round(cg_price),
                "divergence_pct": result.divergence_pct,
                "status": result.status,
                "reason": result.reason,
            }
        )

    now = pd.Timestamp.now(tz="UTC").floor("min")
    payload = {
        "generated_at": now.isoformat(),
        "title": "Salute delle fonti dati",
        "disclaimer": "Controllo incrociato Yahoo vs CoinGecko sui prezzi Tier-1. Non è consulenza finanziaria.",
        "assets": assets,
    }
    write_report_json(payload, JSON_PATH)
    mismatches = sum(1 for a in assets if a["status"] == "mismatch")
    logger.info("Wrote %s (%d assets, %d mismatch)", JSON_PATH, len(assets), mismatches)


if __name__ == "__main__":
    main()
