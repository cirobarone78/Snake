"""Sanity tests for the Asset model and Tier 1 lookups."""

from src.assets.asset import (
    CONTEXT_ASSETS,
    TIER1_ASSETS,
    AssetClass,
    TradingCalendar,
    get_asset_by_symbol,
)


def test_tier1_count_and_symbols():
    """ADR-005: Tier 1 has BTC, ETH, SOL, LINK, POL."""
    symbols = {a.symbol for a in TIER1_ASSETS}
    assert symbols == {"BTC", "ETH", "SOL", "LINK", "POL"}


def test_tier1_all_crypto():
    """Tier 1 is crypto-only in the project's current scope."""
    assert all(a.asset_class == AssetClass.CRYPTO for a in TIER1_ASSETS)
    assert all(a.trading_calendar == TradingCalendar.CRYPTO_24_7 for a in TIER1_ASSETS)


def test_tier1_have_yahoo_symbols():
    """Phase 1 ingestion via Yahoo requires every Tier 1 asset to map."""
    assert all(a.yahoo_symbol is not None for a in TIER1_ASSETS)


def test_context_assets_are_not_crypto():
    """ADR-005: context assets are macro indices and gold, not crypto."""
    assert all(a.asset_class != AssetClass.CRYPTO for a in CONTEXT_ASSETS)


def test_lookup_by_symbol():
    assert get_asset_by_symbol("BTC") is not None
    assert get_asset_by_symbol("BTC").name == "Bitcoin"
    assert get_asset_by_symbol("NONEXISTENT") is None
