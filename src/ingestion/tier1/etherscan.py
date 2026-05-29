# pyright: strict
"""Etherscan on-chain source (Tier 1, ADR-017).

Etherscan adds the **on-chain** dimension to the Tier 1 ingestion. It
covers Ethereum mainnet natively and, through the v2 multi-chain
endpoint, also Polygon (chainid=137) and others — useful for our
Tier 1 assets that live on EVM chains: ETH, LINK, POL.

Free tier limits (no Pro):
- 5 calls/sec, 100k calls/day — generous for our snapshot needs
- **Historical daily aggregates are PRO-only** (e.g. dailytx,
  dailyavgnetdiff). For free we focus on **current-state snapshots**:
  ETH supply, gas oracle, ERC-20 token supply, ETH price. Each snapshot
  is one row that the script overwrites on every run (Q24 caveat
  applies; appending to a history is deferred).

API key required via env ``ETHERSCAN_API_KEY``. Init raises
``ValueError`` without it.

Like CoinGecko and FRED, this source does NOT implement
``OHLCVDataSource``: Etherscan returns single-value snapshots and
state queries, not OHLC bars. We inherit ``DataSource`` and expose
specialised methods.

Reference: https://docs.etherscan.io/etherscan-v2
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Final

import pandas as pd
import requests

from src.ingestion.base import DataSource

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL: Final[str] = "https://api.etherscan.io/v2/api"
DEFAULT_SLEEP_BETWEEN_CALLS: Final[float] = 0.25  # 5/sec cap = 0.2s min
DEFAULT_MAX_RETRIES: Final[int] = 3
DEFAULT_BACKOFF_BASE: Final[float] = 5.0

# Chain IDs used in the v2 multi-chain API
CHAIN_ETHEREUM: Final[int] = 1
CHAIN_POLYGON: Final[int] = 137

# 1 ETH = 10^18 wei; 1 gwei = 10^9 wei
WEI_PER_ETH: Final[int] = 10**18

# Tier 1 ERC-20 contract addresses on Ethereum mainnet. Kept here for now;
# can move to the Asset model when we have more ERC-20 assets and the
# duplication becomes a real cost. POL was migrated from MATIC on
# 2024-09; the post-rebrand contract is the one we fetch.
TIER1_ERC20_ETHEREUM: Final[dict[str, str]] = {
    "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
    "POL": "0x455e53CBB86018Ac2B8092FdCd39d8444aFFC3F6",
    # Legacy MATIC contract retained for historical sanity, not fetched
    # by default: 0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0
}


class EtherscanSource(DataSource):
    """Etherscan v2 multi-chain REST client."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        session: requests.Session | None = None,
        request_timeout: float = 15.0,
        sleep_between_calls: float = DEFAULT_SLEEP_BETWEEN_CALLS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
    ) -> None:
        resolved_key = api_key or os.environ.get("ETHERSCAN_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Etherscan API key not provided. Pass api_key= or set "
                "ETHERSCAN_API_KEY in env (e.g. via .env)."
            )
        self._api_key = resolved_key
        self._base_url = base_url
        self._session = session or requests.Session()
        self._timeout = request_timeout
        self._sleep = sleep_between_calls
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    @property
    def name(self) -> str:
        return "etherscan"

    # --- snapshot endpoints ---------------------------------------------

    def fetch_eth_supply(self) -> pd.DataFrame:
        """Total ETH supply (wei + derived ETH). Single-row snapshot.

        ``eth_supply_wei`` is stored as a decimal **string** because the
        true value (~10^26) overflows int64. The float ``eth_supply`` (in
        whole ETH) is the convenient column for analysis; the string
        preserves exactness for provenance.
        """
        logger.info("Fetching ETH supply from Etherscan")
        raw = self._get(
            chainid=CHAIN_ETHEREUM, module="stats", action="ethsupply",
        )
        wei = int(raw)
        row = {
            "eth_supply_wei": str(wei),
            "eth_supply": wei / WEI_PER_ETH,
        }
        return _single_row(row)

    def fetch_eth_supply_components(self) -> pd.DataFrame:
        """Detailed ETH supply: Eth2 staking, beacon issuance, burnt fees.

        Endpoint ``ethsupply2`` returns the components separately, which
        gives us the deflationary signal post-merge (burnt vs issued).
        Wei values are stored as strings (overflow int64); ETH-denominated
        values are float for analysis.
        """
        logger.info("Fetching ETH supply components (ethsupply2) from Etherscan")
        raw = self._get(
            chainid=CHAIN_ETHEREUM, module="stats", action="ethsupply2",
        )
        if not isinstance(raw, dict):
            raise RuntimeError(f"Unexpected ethsupply2 shape: {raw!r}")
        wei_supply = int(raw.get("EthSupply", 0))
        wei_staking = int(raw.get("Eth2Staking", 0))
        wei_burnt = int(raw.get("BurntFees", 0))
        wei_withdrawn = int(raw.get("WithdrawnTotal", 0))
        row = {
            "eth_supply_wei": str(wei_supply),
            "eth2_staking_wei": str(wei_staking),
            "burnt_fees_wei": str(wei_burnt),
            "withdrawn_wei": str(wei_withdrawn),
            "eth_supply": wei_supply / WEI_PER_ETH,
            "eth2_staking": wei_staking / WEI_PER_ETH,
            "burnt_fees": wei_burnt / WEI_PER_ETH,
            "withdrawn": wei_withdrawn / WEI_PER_ETH,
        }
        return _single_row(row)

    def fetch_gas_oracle(self) -> pd.DataFrame:
        """Current gas prices (in gwei): safe / propose / fast + base fee."""
        logger.info("Fetching gas oracle from Etherscan")
        raw = self._get(
            chainid=CHAIN_ETHEREUM, module="gastracker", action="gasoracle",
        )
        if not isinstance(raw, dict):
            raise RuntimeError(f"Unexpected gasoracle shape: {raw!r}")
        row = {
            "last_block": int(raw.get("LastBlock", 0)),
            "safe_gas_price": float(raw.get("SafeGasPrice", 0)),
            "propose_gas_price": float(raw.get("ProposeGasPrice", 0)),
            "fast_gas_price": float(raw.get("FastGasPrice", 0)),
            "suggest_base_fee": float(raw.get("suggestBaseFee", 0)),
            "gas_used_ratio": str(raw.get("gasUsedRatio", "")),
        }
        return _single_row(row)

    def fetch_eth_price(self) -> pd.DataFrame:
        """ETH price in USD and in BTC, per Etherscan's aggregate feed."""
        logger.info("Fetching ETH price from Etherscan")
        raw = self._get(
            chainid=CHAIN_ETHEREUM, module="stats", action="ethprice",
        )
        if not isinstance(raw, dict):
            raise RuntimeError(f"Unexpected ethprice shape: {raw!r}")
        row = {
            "eth_btc": float(raw.get("ethbtc", 0)),
            "eth_usd": float(raw.get("ethusd", 0)),
            "eth_btc_timestamp": int(raw.get("ethbtc_timestamp", 0)),
            "eth_usd_timestamp": int(raw.get("ethusd_timestamp", 0)),
        }
        return _single_row(row)

    def fetch_token_supply(
        self,
        contract_address: str,
        chainid: int = CHAIN_ETHEREUM,
        decimals: int = 18,
    ) -> pd.DataFrame:
        """Total supply of an ERC-20 token.

        ``raw_supply`` is in the token's smallest unit (typically
        10^decimals fraction of one whole token) and is stored as a
        **string** because the value (e.g. 10^27 for LINK) overflows
        int64. ``supply`` is the convenient float in whole tokens.
        """
        logger.info(
            "Fetching token supply for %s on chain %d", contract_address, chainid,
        )
        raw = self._get(
            chainid=chainid, module="stats", action="tokensupply",
            contractaddress=contract_address,
        )
        raw_int = int(raw)
        row = {
            "contract_address": contract_address,
            "chainid": chainid,
            "decimals": decimals,
            "raw_supply": str(raw_int),
            "supply": raw_int / (10**decimals),
        }
        return _single_row(row)

    # --- internal -------------------------------------------------------

    def _get(self, **params: Any) -> Any:
        """Send a request and unwrap Etherscan's status/message/result envelope.

        Etherscan responds with HTTP 200 even on logical errors and signals
        them via ``status="0"`` + ``message="NOTOK"`` + ``result="<reason>"``.
        We surface those as ``RuntimeError`` so callers get a real exception.
        """
        request_params = {**params, "apikey": self._api_key}

        attempt = 0
        while True:
            resp = self._session.get(
                self._base_url, params=request_params, timeout=self._timeout,
            )
            if resp.status_code == 429:
                attempt += 1
                if attempt > self._max_retries:
                    raise RuntimeError(
                        f"Etherscan rate limit (HTTP 429) after "
                        f"{self._max_retries} retries."
                    )
                wait = self._backoff_base * (2 ** (attempt - 1))
                logger.warning(
                    "Etherscan 429: retry %d/%d in %.0fs",
                    attempt, self._max_retries, wait,
                )
                time.sleep(wait)
                continue
            resp.raise_for_status()
            time.sleep(self._sleep)
            data = resp.json()
            if not isinstance(data, dict):
                raise RuntimeError(f"Unexpected Etherscan response shape: {data!r}")
            status = str(data.get("status", ""))
            if status != "1":
                raise RuntimeError(
                    f"Etherscan rejected the request: "
                    f"message={data.get('message')!r} result={data.get('result')!r}"
                )
            return data.get("result")


def _single_row(row: dict[str, Any]) -> pd.DataFrame:
    """Wrap a snapshot dict into a one-row DataFrame indexed by snapshot time."""
    snapshot_at = pd.Timestamp.now(tz="UTC").floor("min")
    df = pd.DataFrame([row], index=pd.DatetimeIndex([snapshot_at], name="snapshot_at"))
    return df
