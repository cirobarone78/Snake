# pyright: strict
"""Asset model: asset-class-agnostic representation (ADR-014).

The system handles crypto first but must not bake in crypto-only assumptions.
Equity, ETFs, forex are anticipated future asset classes. Hardcoding
`24/7 market`, `no dividends`, `USD only` would force a rewrite when we
extend to traditional markets.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AssetClass(StrEnum):
    """First-class asset taxonomy. Extendable as we add asset classes."""

    CRYPTO = "crypto"
    EQUITY = "equity"
    ETF = "etf"
    INDEX = "index"
    FOREX = "forex"
    COMMODITY = "commodity"


class TradingCalendar(StrEnum):
    """Trading calendar identifier. Crypto is 24/7, equity markets have
    sessions and holidays. ADR-014 requires explicit calendar handling."""

    CRYPTO_24_7 = "crypto_24_7"
    NYSE = "nyse"
    NASDAQ = "nasdaq"
    BORSA_ITALIANA = "borsa_italiana"
    LSE = "lse"


class Asset(BaseModel):
    """A tradeable or observable financial asset.

    Fields beyond `symbol` and `asset_class` may be None when irrelevant
    (e.g. on-chain metrics for non-crypto, exchange for an index)."""

    symbol: str = Field(..., description="Canonical project symbol, e.g. 'BTC', 'ETH', 'AAPL'")
    asset_class: AssetClass
    name: str = Field(..., description="Human-readable name")
    quote_currency: str = Field(default="USD", description="Currency the price is denominated in")
    trading_calendar: TradingCalendar = Field(default=TradingCalendar.CRYPTO_24_7)
    exchange: str | None = Field(default=None, description="Primary exchange for trading")
    tier: int = Field(default=2, description="1 = deep analysis (ADR-005), 2 = broad universe, 3 = context-only")
    yahoo_symbol: str | None = Field(default=None, description="Ticker on Yahoo Finance (e.g. 'BTC-USD')")
    binance_symbol: str | None = Field(default=None, description="Symbol on Binance (e.g. 'BTCUSDT')")
    coingecko_id: str | None = Field(default=None, description="ID on CoinGecko (e.g. 'bitcoin')")
    notes: str | None = None


TIER1_ASSETS: list[Asset] = [
    Asset(
        symbol="BTC",
        asset_class=AssetClass.CRYPTO,
        name="Bitcoin",
        quote_currency="USD",
        trading_calendar=TradingCalendar.CRYPTO_24_7,
        tier=1,
        yahoo_symbol="BTC-USD",
        binance_symbol="BTCUSDT",
        coingecko_id="bitcoin",
    ),
    Asset(
        symbol="ETH",
        asset_class=AssetClass.CRYPTO,
        name="Ethereum",
        quote_currency="USD",
        trading_calendar=TradingCalendar.CRYPTO_24_7,
        tier=1,
        yahoo_symbol="ETH-USD",
        binance_symbol="ETHUSDT",
        coingecko_id="ethereum",
    ),
    Asset(
        symbol="SOL",
        asset_class=AssetClass.CRYPTO,
        name="Solana",
        quote_currency="USD",
        trading_calendar=TradingCalendar.CRYPTO_24_7,
        tier=1,
        yahoo_symbol="SOL-USD",
        binance_symbol="SOLUSDT",
        coingecko_id="solana",
    ),
    Asset(
        symbol="LINK",
        asset_class=AssetClass.CRYPTO,
        name="Chainlink",
        quote_currency="USD",
        trading_calendar=TradingCalendar.CRYPTO_24_7,
        tier=1,
        yahoo_symbol="LINK-USD",
        binance_symbol="LINKUSDT",
        coingecko_id="chainlink",
    ),
    Asset(
        symbol="POL",
        asset_class=AssetClass.CRYPTO,
        name="Polygon",
        quote_currency="USD",
        trading_calendar=TradingCalendar.CRYPTO_24_7,
        tier=1,
        yahoo_symbol="POL28321-USD",
        binance_symbol="POLUSDT",
        coingecko_id="polygon-ecosystem-token",
        notes="Yahoo ticker history: POL-USD (truncated 2023-10-31), then MATIC-USD "
        "(froze/delisted ~2026-03), now POL28321-USD (the live POL feed, "
        "cross-validated 1:1 vs CoinGecko polygon-ecosystem-token). Internal "
        "canonical name remains POL after the Sep-2024 MATIC->POL rebrand. See ADR-019/026.",
    ),
]


CONTEXT_ASSETS: list[Asset] = [
    Asset(
        symbol="DXY",
        asset_class=AssetClass.INDEX,
        name="US Dollar Index",
        quote_currency="USD",
        trading_calendar=TradingCalendar.NYSE,
        tier=3,
        yahoo_symbol="DX-Y.NYB",
    ),
    Asset(
        symbol="SPX",
        asset_class=AssetClass.INDEX,
        name="S&P 500",
        quote_currency="USD",
        trading_calendar=TradingCalendar.NYSE,
        tier=3,
        yahoo_symbol="^GSPC",
    ),
    Asset(
        symbol="NDX",
        asset_class=AssetClass.INDEX,
        name="NASDAQ 100",
        quote_currency="USD",
        trading_calendar=TradingCalendar.NASDAQ,
        tier=3,
        yahoo_symbol="^NDX",
    ),
    Asset(
        symbol="GOLD",
        asset_class=AssetClass.COMMODITY,
        name="Gold (spot proxy via GLD ETF)",
        quote_currency="USD",
        trading_calendar=TradingCalendar.NYSE,
        tier=3,
        yahoo_symbol="GC=F",
    ),
    Asset(
        symbol="SPY",
        asset_class=AssetClass.ETF,
        name="SPDR S&P 500 ETF Trust",
        quote_currency="USD",
        trading_calendar=TradingCalendar.NYSE,
        tier=3,
        yahoo_symbol="SPY",
        notes="Benchmark of the probabilistic ETF ranking (decision D2, ADR-032). "
        "The tradeable twin of SPX (^GSPC): an index cannot be held, so excess "
        "returns are measured against the fund an investor could actually buy, "
        "dividends and tracking difference included.",
    ),
]


def get_asset_by_symbol(symbol: str) -> Asset | None:
    """Look up an asset by its canonical project symbol."""
    for asset in TIER1_ASSETS + CONTEXT_ASSETS:
        if asset.symbol == symbol:
            return asset
    return None
