"""Tier 1 data sources (ADR-017): the indispensable core.

Implemented in Phase 1. Other tiers are placeholders only until their
phase begins.
"""

from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

__all__ = ["YahooFinanceSource"]
