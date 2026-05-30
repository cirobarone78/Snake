# pyright: strict
"""FRED (Federal Reserve Economic Data) source (Tier 1, ADR-017).

FRED is the canonical free source for US macro time series. ADR-005
lists context assets at the index level (DXY, SPX, NDX, GOLD via Yahoo);
FRED adds the **macro fundamentals** that drive those indices:
- Policy rates (DFF, DGS2, DGS10) — curve slope is a recession proxy
- Inflation (CPIAUCSL, monthly)
- Money supply (M2SL, monthly)
- Labour market (UNRATE, monthly)
- An alternative broad dollar index (DTWEXBGS) to cross-check Yahoo DXY

API key required (free, register at https://fred.stlouisfed.org/docs/api/).
We expect the key in env ``FRED_API_KEY``. Rate limit is generous
(120 req/min), so default throttle is light.

Like ``CoinGeckoSource``, FRED returns time series of single values
(not OHLCV), so we don't implement ``OHLCVDataSource``. We inherit only
the minimal ``DataSource`` interface and expose specialised methods.
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

DEFAULT_BASE_URL: Final[str] = "https://api.stlouisfed.org/fred"
DEFAULT_SLEEP_BETWEEN_CALLS: Final[float] = 0.5  # 120/min cap, very loose
DEFAULT_MAX_RETRIES: Final[int] = 3
DEFAULT_BACKOFF_BASE: Final[float] = 5.0

# Sentinel FRED uses for missing observations
FRED_MISSING_VALUE: Final[str] = "."


class FredSource(DataSource):
    """REST client for the public FRED API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        session: requests.Session | None = None,
        request_timeout: float = 20.0,
        sleep_between_calls: float = DEFAULT_SLEEP_BETWEEN_CALLS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
    ) -> None:
        resolved_key = api_key or os.environ.get("FRED_API_KEY")
        if not resolved_key:
            raise ValueError(
                "FRED API key not provided. Pass api_key= or set FRED_API_KEY "
                "in env (e.g. via a .env file)."
            )
        self._api_key = resolved_key
        self._base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._timeout = request_timeout
        self._sleep = sleep_between_calls
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    @property
    def name(self) -> str:
        return "fred"

    def fetch_series(
        self,
        series_id: str,
        observation_start: str | None = None,
        observation_end: str | None = None,
    ) -> pd.DataFrame:
        """Return the full observation series for ``series_id``.

        Output: ``DataFrame`` with a tz-aware UTC ``DatetimeIndex`` named
        ``timestamp`` and a single column ``value``. Missing observations
        (FRED's ``"."`` sentinel) are converted to ``NaN`` and **kept** —
        downstream code decides whether to fill or drop. The behaviour
        matches what Yahoo / Binance sources do for ``close``.
        """
        params: dict[str, str] = {"series_id": series_id}
        if observation_start is not None:
            params["observation_start"] = observation_start
        if observation_end is not None:
            params["observation_end"] = observation_end

        logger.info(
            "Fetching FRED series %s (start=%s, end=%s)",
            series_id, observation_start, observation_end,
        )
        payload = self._get("/series/observations", params=params)
        return _observations_to_frame(payload.get("observations") or [])

    def fetch_series_info(self, series_id: str) -> dict[str, Any]:
        """Metadata for a series: title, units, frequency, observation range.

        Returns the raw FRED record (one dict per series). Useful to log
        provenance and to know the natural frequency (D/W/M/Q/A) before
        deciding storage paths.
        """
        logger.info("Fetching FRED metadata for %s", series_id)
        payload = self._get("/series", params={"series_id": series_id})
        rows = payload.get("seriess") or []
        if not rows:
            raise RuntimeError(f"FRED returned no metadata for series_id={series_id!r}")
        return rows[0]

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        request_params = {
            **params,
            "api_key": self._api_key,
            "file_type": "json",
        }

        attempt = 0
        while True:
            resp = self._session.get(url, params=request_params, timeout=self._timeout)
            if resp.status_code == 429:
                attempt += 1
                if attempt > self._max_retries:
                    raise RuntimeError(
                        f"FRED rate limit (HTTP 429) after {self._max_retries} retries."
                    )
                wait = self._backoff_base * (2 ** (attempt - 1))
                logger.warning(
                    "FRED 429: retry %d/%d in %.0fs",
                    attempt, self._max_retries, wait,
                )
                time.sleep(wait)
                continue
            if resp.status_code == 400:
                # FRED's auth/argument errors arrive as 400 with a JSON body
                body = resp.json() if resp.content else {}
                raise RuntimeError(
                    f"FRED rejected the request (HTTP 400): {body.get('error_message', body)}"
                )
            resp.raise_for_status()
            time.sleep(self._sleep)
            data = resp.json()
            if not isinstance(data, dict):
                raise RuntimeError(f"Unexpected FRED response shape: {data!r}")
            return data


def _observations_to_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Normalise a FRED ``observations`` payload into a single-column DataFrame.

    Each row has ``{"date": "YYYY-MM-DD", "value": "<float>" or "."}``.
    We turn ``"."`` into ``NaN`` and parse the rest. The date is taken at
    UTC midnight (FRED dates are calendar dates, not timestamps).
    """
    if not rows:
        return _empty_frame()
    dates = pd.to_datetime([r["date"] for r in rows], utc=True)
    raw_values = [r["value"] for r in rows]
    values = pd.to_numeric(
        [pd.NA if v == FRED_MISSING_VALUE else v for v in raw_values],
        errors="coerce",
    )
    df = pd.DataFrame({"value": values}, index=dates)
    df.index.name = "timestamp"
    df = df.sort_index()
    return df


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["value"],
        index=pd.DatetimeIndex([], name="timestamp", tz="UTC"),
    )
