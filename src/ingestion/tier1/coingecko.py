# pyright: strict
"""CoinGecko data source (Tier 1, ADR-017).

CoinGecko complements Yahoo + Binance with three pieces they don't give:
- **Aggregated daily price + market cap + volume** time series per coin
  (volume is cross-exchange, not single-venue like Binance)
- **Global market dominance**: BTC/ETH share of total crypto market cap
- **Top-N dynamic universe** by market cap (feeds Tier 2 in ADR-005)

This source does **not** implement OHLCVDataSource: CoinGecko returns
single-price points per timestamp, not OHLC bars. We keep the abstract
interface minimal and let CoinGecko expose its specialised methods.
Forcing OHLC out of close-only data would be lossy and misleading.

Free tier limits (no API key):
- ~5-15 calls/min, variable by endpoint
- ``market_chart`` granularity is auto-selected: minutely for days=1,
  hourly for 2-90 days, daily for >90 days (we always pass days>=365)
- Last point of any time series is "now" (intraday tail). We floor to
  date and de-duplicate keeping the last entry per day.

Optional Demo API key via env var ``COINGECKO_API_KEY`` lifts the limit
to 30 calls/min.
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

DEFAULT_BASE_URL: Final[str] = "https://api.coingecko.com/api/v3"
DEFAULT_VS_CURRENCY: Final[str] = "usd"
DEFAULT_DAYS: Final[int] = 365
DEFAULT_TOP_N: Final[int] = 20
# Wider universe for the DCA candidate screen: the filters cut hard, so the pool
# has to start well past the handful of names everyone already holds.
DEFAULT_MARKETS_N: Final[int] = 100

# Free-tier polite throttle. With a Demo key this could be lower.
DEFAULT_SLEEP_BETWEEN_CALLS: Final[float] = 10.0

# Retry policy for transient 429s (free-tier quota shared by IP can spike).
DEFAULT_MAX_RETRIES: Final[int] = 5
DEFAULT_BACKOFF_BASE: Final[float] = 30.0


class CoinGeckoSource(DataSource):
    """Public + Demo CoinGecko REST API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        session: requests.Session | None = None,
        request_timeout: float = 20.0,
        sleep_between_calls: float = DEFAULT_SLEEP_BETWEEN_CALLS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key or os.environ.get("COINGECKO_API_KEY")
        self._session = session or requests.Session()
        self._timeout = request_timeout
        self._sleep = sleep_between_calls
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    @property
    def name(self) -> str:
        return "coingecko"

    def fetch_market_chart(
        self,
        coingecko_id: str,
        days: int = DEFAULT_DAYS,
        vs_currency: str = DEFAULT_VS_CURRENCY,
    ) -> pd.DataFrame:
        """Daily price, market cap, USD-volume for a single coin.

        Output columns: ``price, market_cap, volume`` with a tz-aware
        UTC ``DatetimeIndex`` named ``timestamp`` (floored to date).
        """
        logger.info(
            "Fetching market chart for %s (days=%d, vs=%s)",
            coingecko_id,
            days,
            vs_currency,
        )
        payload = self._get(
            f"/coins/{coingecko_id}/market_chart",
            params={"vs_currency": vs_currency, "days": days},
        )
        return _market_chart_to_frame(payload)

    def fetch_global(self) -> pd.DataFrame:
        """Snapshot of global market structure.

        Output is a single-row DataFrame indexed by an ISO ``snapshot_at``
        timestamp, with one column per dominance percentage
        (``btc_dom``, ``eth_dom``, ``usdt_dom``, ...) plus total market
        cap and 24h volume in USD.
        """
        logger.info("Fetching CoinGecko /global snapshot")
        payload = self._get("/global")["data"]
        snapshot_at = pd.Timestamp.now(tz="UTC").floor("min")
        row: dict[str, float] = {}
        for sym, pct in (payload.get("market_cap_percentage") or {}).items():
            row[f"{sym}_dom"] = float(pct)
        row["total_market_cap_usd"] = float(
            (payload.get("total_market_cap") or {}).get(DEFAULT_VS_CURRENCY, 0.0)
        )
        row["total_volume_24h_usd"] = float(
            (payload.get("total_volume") or {}).get(DEFAULT_VS_CURRENCY, 0.0)
        )
        row["active_cryptocurrencies"] = float(payload.get("active_cryptocurrencies") or 0)
        return pd.DataFrame([row], index=pd.DatetimeIndex([snapshot_at], name="snapshot_at"))

    def fetch_top_n(
        self,
        n: int = DEFAULT_TOP_N,
        vs_currency: str = DEFAULT_VS_CURRENCY,
    ) -> pd.DataFrame:
        """Top N coins by market cap. Snapshot, not time series.

        Output columns: ``symbol, name, market_cap, current_price,
        total_volume, price_change_24h_pct, market_cap_rank``.
        Index: integer rank (1-based).
        """
        logger.info("Fetching top %d coins by market cap (vs=%s)", n, vs_currency)
        payload = self._get(
            "/coins/markets",
            params={
                "vs_currency": vs_currency,
                "order": "market_cap_desc",
                "per_page": n,
                "page": 1,
            },
        )
        rows = [
            {
                "symbol": c["symbol"],
                "name": c["name"],
                "market_cap": c["market_cap"],
                "current_price": c["current_price"],
                "total_volume": c["total_volume"],
                "price_change_24h_pct": c.get("price_change_percentage_24h"),
                "market_cap_rank": c.get("market_cap_rank"),
            }
            for c in payload
        ]
        df = pd.DataFrame(rows)
        df.index = pd.RangeIndex(start=1, stop=len(df) + 1, name="rank")
        return df

    def fetch_markets(
        self,
        n: int = DEFAULT_MARKETS_N,
        vs_currency: str = DEFAULT_VS_CURRENCY,
    ) -> pd.DataFrame:
        """Top N coins with the extra fields a long-horizon screen needs.

        ``fetch_top_n`` deliberately stays a small, stable universe snapshot for
        Tier 2 (ADR-005). The DCA candidate screen needs three things it does not
        carry: ``atl_date`` (a lower bound on how long the coin has existed —
        there is no track record to judge without it), ``ath_change_percentage``
        (how far below its peak it trades) and ``coingecko_id`` (to join against
        the category map). Rather than widen ``fetch_top_n`` and its callers, this
        is a separate, richer read of the same endpoint.

        Output columns: ``coingecko_id, symbol, name, market_cap,
        market_cap_rank, current_price, total_volume, price_change_24h_pct,
        ath_change_pct, atl_date``. Index: integer rank (1-based).
        Snapshot, not time series.
        """
        logger.info("Fetching top %d coin markets (vs=%s)", n, vs_currency)
        rows: list[dict[str, Any]] = []
        # The endpoint caps per_page at 250, so a wider screen needs paging.
        per_page = min(250, max(1, n))
        page = 1
        while len(rows) < n:
            payload = self._get(
                "/coins/markets",
                params={
                    "vs_currency": vs_currency,
                    "order": "market_cap_desc",
                    "per_page": per_page,
                    "page": page,
                },
            )
            if not payload:
                break
            for c in payload:
                rows.append(
                    {
                        "coingecko_id": c.get("id"),
                        "symbol": str(c.get("symbol") or "").upper(),
                        "name": c.get("name"),
                        "market_cap": c.get("market_cap"),
                        "market_cap_rank": c.get("market_cap_rank"),
                        "current_price": c.get("current_price"),
                        "total_volume": c.get("total_volume"),
                        "price_change_24h_pct": c.get("price_change_percentage_24h"),
                        "ath_change_pct": c.get("ath_change_percentage"),
                        "atl_date": c.get("atl_date"),
                    }
                )
            if len(payload) < per_page:
                break
            page += 1
        df = pd.DataFrame(
            rows[:n],
            columns=[
                "coingecko_id",
                "symbol",
                "name",
                "market_cap",
                "market_cap_rank",
                "current_price",
                "total_volume",
                "price_change_24h_pct",
                "ath_change_pct",
                "atl_date",
            ],
        )
        df.index = pd.RangeIndex(start=1, stop=len(df) + 1, name="rank")
        return df

    def fetch_categories(self, min_market_cap: float = 0.0) -> pd.DataFrame:
        """Crypto categories (narratives) with market-cap-weighted 24h move.

        CoinGecko's ``/coins/categories`` returns ~700 categories (AI, RWA,
        gaming, L2, meme, ...) — the crypto analogue of equity sectors/themes.
        Each carries aggregate ``market_cap``, ``volume_24h`` and the
        market-cap-weighted ``market_cap_change_24h`` (%), plus the top-3 coins.

        ``min_market_cap`` filters out micro-cap categories whose huge % moves
        are pump noise, not rotation (e.g. a $5M "launchpad" category at +400%).
        A sensible screener floor is ~1e8 (100M USD). Default 0 keeps all.

        Output columns: ``category_id, name, market_cap, volume_24h,
        change_24h_pct, top_coins``. Index: integer rank by market cap (1-based).
        Snapshot, not time series — accumulate via ``write_snapshot``.
        """
        logger.info("Fetching CoinGecko /coins/categories (min_mcap=%.0f)", min_market_cap)
        payload = self._get("/coins/categories")
        rows = [
            {
                "category_id": c.get("id"),
                "name": c.get("name"),
                "market_cap": c.get("market_cap"),
                "volume_24h": c.get("volume_24h"),
                "change_24h_pct": c.get("market_cap_change_24h"),
                "top_coins": ",".join(str(s) for s in (c.get("top_3_coins_id") or []) if s),
            }
            for c in payload
            if (c.get("market_cap") or 0.0) >= min_market_cap
        ]
        df = pd.DataFrame(
            rows,
            columns=[
                "category_id",
                "name",
                "market_cap",
                "volume_24h",
                "change_24h_pct",
                "top_coins",
            ],
        )
        df = df.sort_values("market_cap", ascending=False, na_position="last")
        df.index = pd.RangeIndex(start=1, stop=len(df) + 1, name="rank")
        return df

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        headers = {"accept": "application/json"}
        if self._api_key:
            # Demo API key header (per CoinGecko docs)
            headers["x-cg-demo-api-key"] = self._api_key

        attempt = 0
        while True:
            resp = self._session.get(url, params=params, headers=headers, timeout=self._timeout)
            if resp.status_code == 429:
                attempt += 1
                if attempt > self._max_retries:
                    raise RuntimeError(
                        "CoinGecko rate limit hit (HTTP 429) after "
                        f"{self._max_retries} retries. Increase sleep_between_calls "
                        "or set COINGECKO_API_KEY (Demo)."
                    )
                wait = self._backoff_base * (2 ** (attempt - 1))
                logger.warning(
                    "CoinGecko 429: retry %d/%d in %.0fs",
                    attempt,
                    self._max_retries,
                    wait,
                )
                time.sleep(wait)
                continue
            resp.raise_for_status()
            time.sleep(self._sleep)
            return resp.json()


def _market_chart_to_frame(payload: dict[str, list[list[float]]]) -> pd.DataFrame:
    """Normalise the three parallel arrays into one daily DataFrame.

    CoinGecko returns:
      ``prices``, ``market_caps``, ``total_volumes``: each a list of
      ``[unix_ms, value]`` pairs.
    """
    df_price = _series_from_payload(payload.get("prices") or [], "price")
    df_mcap = _series_from_payload(payload.get("market_caps") or [], "market_cap")
    df_vol = _series_from_payload(payload.get("total_volumes") or [], "volume")

    if df_price.empty:
        return _empty_market_chart_frame()

    combined = df_price.join(df_mcap, how="outer").join(df_vol, how="outer")
    # Floor timestamps to date and keep the latest record per day. This
    # collapses the intraday tail without dropping it silently.
    combined.index = combined.index.normalize()
    combined.index.name = "timestamp"
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    return combined


def _series_from_payload(rows: list[list[float]], col_name: str) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=[col_name], index=pd.DatetimeIndex([], tz="UTC"))
    ms = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    idx = pd.to_datetime(ms, unit="ms", utc=True)
    return pd.DataFrame({col_name: vals}, index=idx)


def _empty_market_chart_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["price", "market_cap", "volume"],
        index=pd.DatetimeIndex([], name="timestamp", tz="UTC"),
    )
