"""Offline tests for the long-horizon candidate screen. No network."""

from __future__ import annotations

import pandas as pd

from src.features.dca_candidates import (
    coin_categories,
    context_flags,
    is_derivative,
    is_pegged,
    screen_candidates,
)

AS_OF = pd.Timestamp("2026-01-01", tz="UTC")


def _markets() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "coingecko_id": [
                "bitcoin", "tether", "wrapped-bitcoin", "cardano",
                "leo-token", "shiny", "monero",
            ],
            "symbol": ["BTC", "USDT", "WBTC", "ADA", "LEO", "SHINY", "XMR"],
            "name": [
                "Bitcoin", "Tether", "Wrapped Bitcoin", "Cardano",
                "LEO Token", "Shiny", "Monero",
            ],
            "market_cap": [1e12, 1e11, 2e10, 1e10, 8e9, 5e8, 7e9],
            "market_cap_rank": [1, 3, 12, 17, 16, 90, 18],
            "current_price": [100000.0, 1.0, 100000.0, 0.5, 9.0, 0.01, 300.0],
            "total_volume": [3e10, 6e10, 5e8, 6e8, 3e5, 4e7, 8e7],
            "price_change_24h_pct": [1.4, 0.01, 1.3, -2.0, 0.4, 12.0, 0.9],
            "ath_change_pct": [-38.0, -24.0, -38.0, -92.0, -11.0, -60.0, -47.0],
            "atl_date": [
                "2013-07-05T16:00:00.000Z", "2015-03-01T16:00:00.000Z",
                "2019-04-01T00:00:00.000Z", "2020-03-12T18:22:55.000Z",
                "2019-12-24T07:14:35.000Z", "2025-06-01T00:00:00.000Z",
                "2015-01-13T16:00:00.000Z",
            ],
        }
    )


def _categories() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "category_id": ["l1", "privacy", "meme"],
            "name": ["Layer 1 (L1)", "Privacy Coins", "Meme"],
            "market_cap": [2e12, 8e9, 3e10],
            "volume_24h": [6e10, 1e8, 2e9],
            "change_24h_pct": [1.0, 0.5, 4.0],
            "top_coins": ["bitcoin,cardano", "monero", "shiny"],
        }
    )


def test_pegged_detection_covers_name_and_behaviour() -> None:
    assert is_pegged("Tether", "USDT", 1.0, 0.01)
    # No stable-ish name, but pinned to 1.00 and barely moving -> pegged anyway.
    assert is_pegged("Quiet Token", "QT", 1.001, 0.1)
    assert not is_pegged("Bitcoin", "BTC", 100000.0, 1.4)


def test_derivative_detection_matches_wrappers_not_lookalike_symbols() -> None:
    assert is_derivative("Wrapped Bitcoin")
    assert is_derivative("Lido Staked Ether")
    # Regression: a "starts with W" symbol rule threw these out wrongly.
    assert not is_derivative("Worldcoin")
    assert not is_derivative("World Liberty Financial")


def test_context_flags_do_not_confuse_decentralized_with_centralized_exchange() -> None:
    assert context_flags(["Decentralized Exchange (DEX)"]) == []
    assert context_flags(["Centralized Exchange (CEX) Token"]) == ["exchange_token"]
    assert context_flags(["Meme", "Dog-Themed"]) == ["meme"]


def test_coin_categories_inverts_the_snapshot() -> None:
    mapping = coin_categories(_categories())
    assert mapping["bitcoin"] == ["Layer 1 (L1)"]
    assert mapping["monero"] == ["Privacy Coins"]
    assert "unknown-coin" not in mapping


def test_screen_rejects_each_class_with_its_own_reason() -> None:
    _, rejected = screen_candidates(
        _markets(), held_symbols=["BTC"], min_market_cap=1e9, as_of=AS_OF
    )
    reasons = dict(zip(rejected["symbol"], rejected["reason"], strict=True))
    assert reasons["BTC"] == "already_held"
    assert reasons["USDT"] == "stablecoin_or_pegged"
    assert reasons["WBTC"] == "wrapped_or_derivative"
    assert reasons["LEO"] == "illiquid"  # $8B cap on $300k of volume
    assert reasons["SHINY"] == "market_cap_below_floor"


def test_screen_keeps_the_coins_that_clear_every_filter() -> None:
    shortlist, _ = screen_candidates(
        _markets(), held_symbols=["BTC"], min_market_cap=1e9, as_of=AS_OF
    )
    assert set(shortlist["symbol"]) == {"ADA", "XMR"}
    assert list(shortlist["rank"]) == [1, 2]


def test_min_age_is_measured_from_the_all_time_low_date() -> None:
    shortlist, _ = screen_candidates(
        _markets(), held_symbols=["BTC"], min_market_cap=1e9, as_of=AS_OF
    )
    xmr = shortlist.loc[shortlist["symbol"] == "XMR"].iloc[0]
    assert 10.5 < float(xmr["min_age_years"]) < 11.5  # ATL Jan 2015


def test_diversifying_flags_only_categories_absent_from_the_holdings() -> None:
    shortlist, _ = screen_candidates(
        _markets(),
        held_symbols=["BTC"],
        categories=_categories(),
        min_market_cap=1e9,
        as_of=AS_OF,
    )
    flags = dict(zip(shortlist["symbol"], shortlist["diversifying"], strict=True))
    assert flags["XMR"] is True  # Privacy Coins: not covered by BTC
    assert flags["ADA"] is False  # shares Layer 1 (L1) with BTC


def test_turnover_ceiling_rejects_volume_anomalies() -> None:
    markets = _markets()
    markets.loc[markets["symbol"] == "ADA", "total_volume"] = 1e12  # 100x its cap
    _, rejected = screen_candidates(
        markets, held_symbols=["BTC"], min_market_cap=1e9, as_of=AS_OF
    )
    assert "turnover_anomaly" in set(rejected["reason"])


def test_screen_on_empty_snapshot_returns_empty_frames() -> None:
    shortlist, rejected = screen_candidates(pd.DataFrame())
    assert shortlist.empty and rejected.empty
