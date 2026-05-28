# pyright: strict
"""Abstract data source interfaces.

Concrete sources (Yahoo Finance, Binance, FRED, etc.) implement these
interfaces. The pipeline depends on the abstractions, not the concretions —
swapping sources should not require changes upstream.

This is intentionally minimal in Phase 1. We add capabilities as we add
source types (news, on-chain, macro). Premature abstraction would hurt.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd

from src.assets.asset import Asset


class DataSource(ABC):
    """Base for any external data source."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier for the source. Used in storage paths and logs."""


class OHLCVDataSource(DataSource):
    """A source that can return OHLCV bars for an asset."""

    @abstractmethod
    def fetch_ohlcv(
        self,
        asset: Asset,
        start: datetime | str,
        end: datetime | str | None = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Return OHLCV bars for the asset between ``start`` and ``end``.

        The returned DataFrame is normalized to columns:
        ``open, high, low, close, volume`` with a tz-aware UTC ``DatetimeIndex``.
        Missing data is dropped, not filled — feature engineering decides
        the policy.

        Implementations must respect the source's rate limits and surface
        partial failures (return what was fetched, log what was missed)
        rather than swallowing errors.
        """
