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

Storage (overwrites on each run; Q24 caveat applies):
- data/raw/etherscan/eth_supply_latest.parquet
- data/raw/etherscan/eth_supply_components_latest.parquet
- data/raw/etherscan/gas_oracle_latest.parquet
- data/raw/etherscan/eth_price_latest.parquet
- data/raw/etherscan/token_supply/{SYMBOL}_latest.parquet
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

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
        ("eth_supply", "eth_supply_latest.parquet", src.fetch_eth_supply),
        (
            "eth_supply_components",
            "eth_supply_components_latest.parquet",
            src.fetch_eth_supply_components,
        ),
        ("gas_oracle", "gas_oracle_latest.parquet", src.fetch_gas_oracle),
        ("eth_price", "eth_price_latest.parquet", src.fetch_eth_price),
    ]

    for label, filename, method in snapshots:
        try:
            df = method()
            out = data_dir / filename
            df.to_parquet(out, engine="pyarrow", compression="snappy")
            logger.info("Saved %s snapshot (%d rows) to %s", label, len(df), out)
            results[label] = "OK"
        except Exception as exc:
            logger.exception("Failed %s: %s", label, exc)
            results[label] = "ERROR"

    for symbol, contract in TIER1_ERC20_ETHEREUM.items():
        try:
            df = src.fetch_token_supply(contract_address=contract)
            out = token_dir / f"{symbol}_latest.parquet"
            df.to_parquet(out, engine="pyarrow", compression="snappy")
            logger.info("Saved %s ERC-20 supply snapshot to %s", symbol, out)
            results[f"token:{symbol}"] = "OK"
        except Exception as exc:
            logger.exception("Failed token supply %s: %s", symbol, exc)
            results[f"token:{symbol}"] = "ERROR"

    logger.info("Done. Per-snapshot result:")
    for label, status in results.items():
        logger.info("  %-30s [%s]", label, status)


if __name__ == "__main__":
    main()
