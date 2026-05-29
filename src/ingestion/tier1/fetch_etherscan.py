# pyright: strict
"""Etherscan batch ingestion: on-chain snapshots for ETH + ERC-20 Tier 1.

Run with:
  ``uv run python -m src.ingestion.tier1.fetch_etherscan``

Fetches:
- ETH supply (basic + with components: staking, burnt, withdrawn)
- Gas oracle (current safe/propose/fast + base fee)
- ETH price per Etherscan aggregate feed (cross-check vs Yahoo/Binance)
- ERC-20 total supply for the Tier 1 tokens that live on Ethereum
  (LINK, POL). BTC and SOL are out of scope (different chains).

Storage (ADR-022: ``_latest`` overwrites, ``_history`` appends):
- data/raw/etherscan/{label}_latest.parquet — current state
- data/raw/etherscan/{label}_history.parquet — accumulated snapshots
- data/raw/etherscan/token_supply/{SYMBOL}_{latest,history}.parquet
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

from src.ingestion.snapshot import write_snapshot
from src.ingestion.tier1.etherscan import TIER1_ERC20_ETHEREUM, EtherscanSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path("data/raw/etherscan")


def main() -> None:
    load_dotenv()
    src = EtherscanSource()
    data_dir = DEFAULT_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    token_dir = data_dir / "token_supply"
    token_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting Etherscan batch ingestion (Phase 1)")
    results: dict[str, str] = {}

    snapshots: list[tuple[str, str, callable]] = [  # type: ignore[type-arg]
        ("eth_supply", "eth_supply", src.fetch_eth_supply),
        ("eth_supply_components", "eth_supply_components", src.fetch_eth_supply_components),
        ("gas_oracle", "gas_oracle", src.fetch_gas_oracle),
        ("eth_price", "eth_price", src.fetch_eth_price),
    ]

    for label, basename, method in snapshots:
        try:
            df = method()
            write_snapshot(
                df,
                latest_path=data_dir / f"{basename}_latest.parquet",
                history_path=data_dir / f"{basename}_history.parquet",
            )
            results[label] = "OK"
        except Exception as exc:
            logger.exception("Failed %s: %s", label, exc)
            results[label] = "ERROR"

    for symbol, contract in TIER1_ERC20_ETHEREUM.items():
        try:
            df = src.fetch_token_supply(contract_address=contract)
            write_snapshot(
                df,
                latest_path=token_dir / f"{symbol}_latest.parquet",
                history_path=token_dir / f"{symbol}_history.parquet",
            )
            results[f"token:{symbol}"] = "OK"
        except Exception as exc:
            logger.exception("Failed token supply %s: %s", symbol, exc)
            results[f"token:{symbol}"] = "ERROR"

    logger.info("Done. Per-snapshot result:")
    for label, status in results.items():
        logger.info("  %-30s [%s]", label, status)


if __name__ == "__main__":
    main()
