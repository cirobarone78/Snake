"""Equity sector/theme universe + snapshot (Fase 8, screener equity).

The user's original example was equity, not crypto: "AI is booming → memory and
energy stocks run; war hurts others". This is **sector/theme rotation** on the
classic market — the equity analogue of the crypto category screener. Here we
pin a compact universe of liquid, free-to-fetch **sector/thematic ETFs** (the
clean way to track a theme without picking single stocks), and turn a Yahoo
multi-day fetch into a current-strength snapshot.

ETFs are the right granularity: an ETF *is* the sector basket, so its return is
the sector's move — no survivorship/selection bias from hand-picking tickers.
Asset-class-agnostic (ADR-014): each theme is just an ``Asset`` with a Yahoo
symbol; adding a theme is one line.

Free data only (Yahoo). No look-ahead concern here — this is a present-snapshot
screener, like the crypto one; the historical/probabilistic layer is separate.
"""

from __future__ import annotations

from src.assets.asset import Asset, AssetClass, TradingCalendar

# Liquid US sector & thematic ETFs. Symbol = our label; yahoo_symbol = ticker.
# Mix of GICS sectors (SPDR "XL*") and themes the user cares about (AI/semis,
# nuclear/uranium, energy, defense, ...). All large, liquid, free on Yahoo.
SECTOR_ETFS: list[Asset] = [
    # --- broad GICS sectors (SPDR Select Sector) ---
    Asset(
        symbol="TECH",
        asset_class=AssetClass.ETF,
        name="Technology (XLK)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="XLK",
    ),
    Asset(
        symbol="ENERGY",
        asset_class=AssetClass.ETF,
        name="Energy (XLE)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="XLE",
    ),
    Asset(
        symbol="FINANCE",
        asset_class=AssetClass.ETF,
        name="Financials (XLF)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="XLF",
    ),
    Asset(
        symbol="HEALTH",
        asset_class=AssetClass.ETF,
        name="Health Care (XLV)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="XLV",
    ),
    Asset(
        symbol="INDUSTRIAL",
        asset_class=AssetClass.ETF,
        name="Industrials (XLI)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="XLI",
    ),
    Asset(
        symbol="UTILITIES",
        asset_class=AssetClass.ETF,
        name="Utilities (XLU)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="XLU",
    ),
    Asset(
        symbol="STAPLES",
        asset_class=AssetClass.ETF,
        name="Consumer Staples (XLP)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="XLP",
    ),
    Asset(
        symbol="DISCRETIONARY",
        asset_class=AssetClass.ETF,
        name="Consumer Discretionary (XLY)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="XLY",
    ),
    Asset(
        symbol="MATERIALS",
        asset_class=AssetClass.ETF,
        name="Materials (XLB)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="XLB",
    ),
    Asset(
        symbol="REALESTATE",
        asset_class=AssetClass.ETF,
        name="Real Estate (XLRE)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="XLRE",
    ),
    Asset(
        symbol="COMMSERV",
        asset_class=AssetClass.ETF,
        name="Communication Svcs (XLC)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="XLC",
    ),
    # --- themes the user named (AI/semis, nuclear/energy, defense) ---
    Asset(
        symbol="SEMIS",
        asset_class=AssetClass.ETF,
        name="Semiconductors (SMH)",
        trading_calendar=TradingCalendar.NASDAQ,
        yahoo_symbol="SMH",
    ),
    Asset(
        symbol="URANIUM",
        asset_class=AssetClass.ETF,
        name="Uranium/Nuclear (URA)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="URA",
    ),
    Asset(
        symbol="CLEANENERGY",
        asset_class=AssetClass.ETF,
        name="Clean Energy (ICLN)",
        trading_calendar=TradingCalendar.NASDAQ,
        yahoo_symbol="ICLN",
    ),
    Asset(
        symbol="OILGAS",
        asset_class=AssetClass.ETF,
        name="Oil & Gas E&P (XOP)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="XOP",
    ),
    Asset(
        symbol="DEFENSE",
        asset_class=AssetClass.ETF,
        name="Aerospace & Defense (ITA)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="ITA",
    ),
    Asset(
        symbol="ROBOTICS",
        asset_class=AssetClass.ETF,
        name="Robotics & AI (BOTZ)",
        trading_calendar=TradingCalendar.NASDAQ,
        yahoo_symbol="BOTZ",
    ),
    Asset(
        symbol="CYBER",
        asset_class=AssetClass.ETF,
        name="Cybersecurity (CIBR)",
        trading_calendar=TradingCalendar.NASDAQ,
        yahoo_symbol="CIBR",
    ),
    Asset(
        symbol="BIOTECH",
        asset_class=AssetClass.ETF,
        name="Biotech (XBI)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="XBI",
    ),
    Asset(
        symbol="GOLD_MINERS",
        asset_class=AssetClass.ETF,
        name="Gold Miners (GDX)",
        trading_calendar=TradingCalendar.NYSE,
        yahoo_symbol="GDX",
    ),
]
