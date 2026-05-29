# pyright: strict
"""CoinGecko batch ingestion: per-coin market chart + global + top-N snapshot.

Run with:
  ``uv run python -m src.ingestion.tier1.fetch_coingecko``

CoinGecko is the third Tier 1 source. It adds three pieces neither
Yahoo nor Binance gives us:
- Daily ``price + market_cap + cross-exchange volume`` per coin
- Global market dominance snapshot (BTC/ETH/USDT/... share %)
- Top-N dynamic universe (feeds ADR-005 Tier 2)

Free-tier rate limit ~5-15 calls/min so we deliberately pace the
batch via the source's ``sleep_between_calls``. With 5 Tier 1 + global
+ markets = 7 calls, total time is ~45s, well within budget.

Output layout (all under ``data/raw/coingecko/``):
- ``crypto/{SYMBOL}_market_chart.parquet`` — time series per asset
- ``global_latest.parquet`` / ``global_history.parquet`` — single-row
  snapshot of global dominance + history of all past snapshots (ADR-022)
- ``top_{N}_latest.parquet`` / ``top_{N}_history.parquet`` — N-row
  snapshot of top-N by market cap + history with ``snapshot_at`` column
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.assets.asset import TIER1_ASSETS
from src.ingestion.snapshot import write_snapshot
from src.ingestion.tier1.coingecko import CoinGeckoSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_DAYS = 365
DEFAULT_TOP_N = 20
DEFAULT_DATA_DIR = Path("data/raw/coingecko")


def main() -> None:
    logger.info("Starting CoinGecko batch ingestion (Phase 1)")
    src = CoinGeckoSource()
    data_dir = DEFAULT_DATA_DIR
    crypto_dir = data_dir / "crypto"
    crypto_dir.mkdir(parents=True, exist_ok=True)

    per_asset: dict[str, int] = {}
    for asset in TIER1_ASSETS:
        if asset.coingecko_id is None:
            logger.info("Skipping %s: no coingecko_id", asset.symbol)
            per_asset[asset.symbol] = -2
            continue
        try:
            df = src.fetch_market_chart(asset.coingecko_id, days=DEFAULT_DAYS)
            if df.empty:
                logger.warning("Empty market chart for %s", asset.symbol)
                per_asset[asset.symbol] = 0
                continue
            out = crypto_dir / f"{asset.symbol}_market_chart.parquet"
            df.to_parquet(out, engine="pyarrow", compression="snappy")
            logger.info("Saved %d rows to %s", len(df), out)
            per_asset[asset.symbol] = len(df)
        except Exception as exc:
            logger.exception("Failed to fetch %s: %s", asset.symbol, exc)
            per_asset[asset.symbol] = -1

    try:
        global_df = src.fetch_global()
        write_snapshot(
            global_df,
            latest_path=data_dir / "global_latest.parquet",
            history_path=data_dir / "global_history.parquet",
        )
    except Exception as exc:
        logger.exception("Failed to fetch /global: %s", exc)

    try:
        top_df = src.fetch_top_n(n=DEFAULT_TOP_N)
        write_snapshot(
            top_df,
            latest_path=data_dir / f"top_{DEFAULT_TOP_N}_latest.parquet",
            history_path=data_dir / f"top_{DEFAULT_TOP_N}_history.parquet",
            primary_key=["rank"],
        )
    except Exception as exc:
        logger.exception("Failed to fetch /coins/markets: %s", exc)

    logger.info("Done. Row counts per asset:")
    for symbol, count in per_asset.items():
        if count == -2:
            status = "SKIP"
        elif count == -1:
            status = "ERROR"
        elif count == 0:
            status = "EMPTY"
        else:
            status = "OK"
        logger.info("  %-6s %6s rows  [%s]", symbol, count, status)


if __name__ == "__main__":
    main()
