"""Fetch FRED macro series, snapshot the current climate, accumulate history.

Pulls the standard macro series, extracts the current level and ~30-day change
per series, persists a compact one-row snapshot to a committed history (ADR-022),
and writes a readable ``REPORT_MACRO.md``. A scheduled workflow runs this daily.

Needs a FRED API key (free). Locally it reads ``FRED_API_KEY`` from ``.env``; in
CI it must be provided as the ``FRED_API_KEY`` repository **secret** (the cron
exposes it as an env var). If the key is absent the script logs and exits
cleanly rather than failing the workflow.

Run:  uv run python -m src.ingestion.tier1.fetch_macro
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.features.macro_report import MACRO_LABELS, format_macro_report_md
from src.ingestion.snapshot import write_snapshot
from src.ingestion.tier1.fred import FredSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SERIES = list(MACRO_LABELS.keys())
DATA_DIR = Path("data/macro_history")
REPORT_PATH = Path("REPORT_MACRO.md")
FETCH_START = "2024-01-01"  # enough lookback for a 30-day change on any series


def _latest_and_change(series: pd.Series, days: int = 30) -> tuple[float, float]:
    """Most recent value + change over ~``days`` (NaN-safe)."""
    s = series.dropna()
    last = float(s.iloc[-1])
    cutoff = s.index[-1] - pd.Timedelta(days=days)
    prior = s[s.index <= cutoff]
    change = last - float(prior.iloc[-1]) if len(prior) else float("nan")
    return last, change


def main() -> None:
    load_dotenv()
    if not os.environ.get("FRED_API_KEY"):
        logger.warning("FRED_API_KEY not set (env/.env/secret). Skipping macro fetch.")
        return

    src = FredSource()
    latest: dict[str, float] = {}
    change_30d: dict[str, float] = {}
    for sid in SERIES:
        try:
            df = src.fetch_series(sid, observation_start=FETCH_START)
        except Exception:
            logger.exception("Failed to fetch FRED series %s", sid)
            continue
        if df.empty or df["value"].dropna().empty:
            logger.warning("Empty FRED series %s", sid)
            continue
        last, chg = _latest_and_change(df["value"])
        latest[sid] = last
        change_30d[sid] = chg

    if not latest:
        logger.warning("No macro series fetched; nothing to persist.")
        return

    # One-row snapshot: current level per series (the climate at this date).
    now = pd.Timestamp.now(tz="UTC").floor("min")
    snapshot = pd.DataFrame([latest], index=pd.DatetimeIndex([now], name="snapshot_at"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    write_snapshot(
        snapshot,
        latest_path=DATA_DIR / "macro_latest.parquet",
        history_path=DATA_DIR / "macro_history.parquet",
    )

    REPORT_PATH.write_text(
        format_macro_report_md(latest, change_30d, snapshot_at=now), encoding="utf-8"
    )
    logger.info("Persisted macro snapshot (%d series) + wrote %s", len(latest), REPORT_PATH)


if __name__ == "__main__":
    main()
