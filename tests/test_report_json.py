"""Offline tests for the dashboard JSON export. No network."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.features.report_json import (
    DISCLAIMER,
    crypto_report_dict,
    equity_report_dict,
    write_report_json,
)


def _categories() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "category_id": ["ai", "rwa", "meme"],
            "name": ["Artificial Intelligence", "Real World Assets", "Meme"],
            "market_cap": [5e9, 2e9, np.nan],  # one NaN -> must become null
            "volume_24h": [1e9, 5e8, 1e7],
            "change_24h_pct": [7.5, 1.2, -3.0],
            "top_coins": ["FET,RNDR,TAO", "ONDO,PENDLE", ""],
        }
    )


def _sectors() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": ["SEMIS", "ENERGY"],
            "name": ["Semiconductors (SMH)", "Energy (XLE)"],
            "ret_5d_pct": [4.6, -1.1],
            "ret_21d_pct": [11.7, 2.0],
        }
    )


# --- crypto ---


def test_crypto_payload_shape_and_disclaimer() -> None:
    payload = crypto_report_dict(_categories(), generated_at="2026-06-05T00:00:00Z")
    assert payload["title"] == "Crypto Narrative Rotation"
    assert payload["disclaimer"] == DISCLAIMER
    assert payload["generated_at"].startswith("2026-06-05")
    assert len(payload["items"]) >= 1
    top = payload["items"][0]
    assert top["rank"] == 1
    assert set(top) == {
        "rank", "name", "status", "strength", "change_24h", "market_cap", "leader", "note"
    }
    assert top["leader"] == "FET"  # first of the comma-joined leaders


def test_crypto_missing_market_cap_is_null_not_invented() -> None:
    payload = crypto_report_dict(_categories())
    meme = next((it for it in payload["items"] if it["name"] == "Meme"), None)
    # 'Meme' has NaN market cap and empty leaders -> null, never fabricated
    if meme is not None:
        assert meme["market_cap"] is None
        assert meme["leader"] is None


def test_crypto_empty_input_yields_empty_items() -> None:
    payload = crypto_report_dict(pd.DataFrame())
    assert payload["items"] == []
    assert payload["disclaimer"] == DISCLAIMER


# --- equity ---


def test_equity_payload_shape_and_ticker() -> None:
    payload = equity_report_dict(_sectors(), generated_at="2026-06-05T00:00:00Z")
    assert payload["title"] == "Equity Sector Rotation"
    semis = next(it for it in payload["items"] if it["name"].startswith("Semiconductors"))
    assert semis["ticker"] == "SMH"  # resolved from the sector universe
    assert set(semis) == {
        "rank", "name", "ticker", "status", "strength", "change_5d", "change_1m", "spark", "note"
    }
    assert semis["change_5d"] == 4.6


def test_equity_empty_input_yields_empty_items() -> None:
    payload = equity_report_dict(pd.DataFrame())
    assert payload["items"] == []


def test_equity_embeds_sparkline_when_provided() -> None:
    spark = {"SEMIS": [10.0, 11.0, 12.0], "ENERGY": [5.0, 4.0]}
    payload = equity_report_dict(_sectors(), spark=spark)
    semis = next(it for it in payload["items"] if it["name"].startswith("Semiconductors"))
    assert semis["spark"] == [10.0, 11.0, 12.0]
    # missing symbol -> null, not invented
    other = equity_report_dict(_sectors(), spark={})
    assert other["items"][0]["spark"] is None


# --- writer ---


def test_write_report_json_is_valid_and_roundtrips(tmp_path: Path) -> None:
    payload = crypto_report_dict(_categories())
    out = tmp_path / "data" / "crypto_report.json"
    write_report_json(payload, out)
    assert out.exists()  # parent dir created
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["title"] == payload["title"]
    assert loaded["items"][0]["rank"] == 1
