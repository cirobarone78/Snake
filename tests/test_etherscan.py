"""Tests for EtherscanSource — envelope parsing, snapshot shapes, errors."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.ingestion.tier1.etherscan import (
    CHAIN_ETHEREUM,
    WEI_PER_ETH,
    EtherscanSource,
)


def _resp(payload: Any, status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    r.raise_for_status = MagicMock()
    if status >= 400 and status != 429:
        r.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return r


def _ok(result: Any) -> dict[str, Any]:
    return {"status": "1", "message": "OK", "result": result}


def _err(message: str = "NOTOK", result: str = "Invalid API Key") -> dict[str, Any]:
    return {"status": "0", "message": message, "result": result}


def test_init_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ETHERSCAN_API_KEY", raising=False)
    with pytest.raises(ValueError, match="Etherscan API key"):
        EtherscanSource()


def test_init_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ETHERSCAN_API_KEY", "envkey")
    src = EtherscanSource()
    assert src._api_key == "envkey"


def test_init_explicit_api_key_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ETHERSCAN_API_KEY", "envkey")
    src = EtherscanSource(api_key="explicit")
    assert src._api_key == "explicit"


def test_fetch_eth_supply_parses_wei_and_eth() -> None:
    session = MagicMock()
    # 122 million ETH in wei
    session.get.return_value = _resp(_ok("122000000000000000000000000"))
    src = EtherscanSource(api_key="k", session=session, sleep_between_calls=0)
    df = src.fetch_eth_supply()

    assert len(df) == 1
    # wei is stored as a string (overflows int64)
    assert df.iloc[0]["eth_supply_wei"] == str(122_000_000 * WEI_PER_ETH)
    assert df.iloc[0]["eth_supply"] == 122_000_000
    assert df.index.name == "snapshot_at"
    assert str(df.index.tz) == "UTC"


def test_fetch_eth_supply_components_parses_dict_payload() -> None:
    payload = {
        "EthSupply": "122000000000000000000000000",
        "Eth2Staking": "1000000000000000000000",
        "BurntFees": "5000000000000000000000",
        "WithdrawnTotal": "200000000000000000000",
    }
    session = MagicMock()
    session.get.return_value = _resp(_ok(payload))
    src = EtherscanSource(api_key="k", session=session, sleep_between_calls=0)
    df = src.fetch_eth_supply_components()

    assert len(df) == 1
    assert df.iloc[0]["eth_supply"] == 122_000_000
    assert df.iloc[0]["eth2_staking"] == 1_000
    assert df.iloc[0]["burnt_fees"] == 5_000
    assert df.iloc[0]["withdrawn"] == 200
    # Sanity-check the string wei mirrors
    assert df.iloc[0]["eth_supply_wei"] == "122000000000000000000000000"


def test_fetch_gas_oracle_parses_prices() -> None:
    payload = {
        "LastBlock": "21000000",
        "SafeGasPrice": "12",
        "ProposeGasPrice": "15",
        "FastGasPrice": "20",
        "suggestBaseFee": "11.5",
        "gasUsedRatio": "0.5,0.6,0.7",
    }
    session = MagicMock()
    session.get.return_value = _resp(_ok(payload))
    src = EtherscanSource(api_key="k", session=session, sleep_between_calls=0)
    df = src.fetch_gas_oracle()

    assert df.iloc[0]["last_block"] == 21_000_000
    assert df.iloc[0]["safe_gas_price"] == 12.0
    assert df.iloc[0]["fast_gas_price"] == 20.0
    assert df.iloc[0]["suggest_base_fee"] == 11.5


def test_fetch_eth_price_parses_dict_payload() -> None:
    payload = {
        "ethbtc": "0.025",
        "ethusd": "2000",
        "ethbtc_timestamp": "1716000000",
        "ethusd_timestamp": "1716000000",
    }
    session = MagicMock()
    session.get.return_value = _resp(_ok(payload))
    src = EtherscanSource(api_key="k", session=session, sleep_between_calls=0)
    df = src.fetch_eth_price()
    assert df.iloc[0]["eth_usd"] == 2000.0
    assert df.iloc[0]["eth_btc"] == 0.025


def test_fetch_token_supply_parses_int_result() -> None:
    session = MagicMock()
    session.get.return_value = _resp(_ok("1000000000000000000000000000"))  # 1B with 18 decimals
    src = EtherscanSource(api_key="k", session=session, sleep_between_calls=0)
    df = src.fetch_token_supply(contract_address="0xABC")
    # raw_supply is stored as string (overflows int64)
    assert df.iloc[0]["raw_supply"] == str(1_000_000_000 * WEI_PER_ETH)
    assert df.iloc[0]["supply"] == 1_000_000_000
    assert df.iloc[0]["contract_address"] == "0xABC"
    assert df.iloc[0]["chainid"] == CHAIN_ETHEREUM
    assert df.iloc[0]["decimals"] == 18


def test_logical_error_surfaces_as_runtime_error() -> None:
    session = MagicMock()
    session.get.return_value = _resp(_err(message="NOTOK", result="Invalid API Key"))
    src = EtherscanSource(api_key="bad", session=session, sleep_between_calls=0)
    with pytest.raises(RuntimeError, match="Invalid API Key"):
        src.fetch_eth_supply()


def test_rate_limit_recovers_after_one_429() -> None:
    session = MagicMock()
    session.get.side_effect = [
        _resp({}, status=429),
        _resp(_ok("122000000000000000000000000")),
    ]
    src = EtherscanSource(
        api_key="k", session=session, sleep_between_calls=0,
        max_retries=3, backoff_base=0,
    )
    df = src.fetch_eth_supply()
    assert df.iloc[0]["eth_supply"] == 122_000_000
    assert session.get.call_count == 2


def test_rate_limit_exhausted_raises() -> None:
    session = MagicMock()
    session.get.return_value = _resp({}, status=429)
    src = EtherscanSource(
        api_key="k", session=session, sleep_between_calls=0,
        max_retries=2, backoff_base=0,
    )
    with pytest.raises(RuntimeError, match="rate limit"):
        src.fetch_eth_supply()
    assert session.get.call_count == 3  # 1 initial + 2 retries


def test_request_includes_apikey_param() -> None:
    session = MagicMock()
    session.get.return_value = _resp(_ok("0"))
    src = EtherscanSource(api_key="k", session=session, sleep_between_calls=0)
    src.fetch_eth_supply()
    _, kwargs = session.get.call_args
    assert kwargs["params"]["apikey"] == "k"
    assert kwargs["params"]["chainid"] == CHAIN_ETHEREUM
    assert kwargs["params"]["module"] == "stats"
    assert kwargs["params"]["action"] == "ethsupply"


# Reserve pandas usage to silence unused-import warnings
_ = pd.Timestamp("2020-01-01", tz="UTC")
