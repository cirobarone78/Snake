# pyright: strict
"""Snapshot persistence with parallel "latest" pointer and append history.

Resolves OPEN_QUESTIONS Q24. Pattern picked: option A (see ADR-022).

Use ``write_snapshot()`` from any source that produces snapshot data
(CoinGecko global / top-N, Etherscan supply / gas / token supply, etc.)
to persist both:

- ``{label}_latest.parquet`` — overwritten on each call, always carries
  the most recent state. Useful for "what's the current value?" queries
- ``{label}_history.parquet`` — appended to on each call. Useful for
  building time series from repeated snapshots

Two cases supported:

1. **Single-row snapshot** — DataFrame whose index is a UTC
   ``DatetimeIndex`` named ``snapshot_at``. History dedup is on the
   index, so running multiple times in the same minute is idempotent.

2. **Multi-row snapshot** — DataFrame with a non-time index (e.g.
   top-N indexed by rank, or per-asset supply table). Pass
   ``snapshot_at`` (or let it default to "now") + ``primary_key`` listing
   the columns that identify a row within a single snapshot. History
   dedup is on ``("snapshot_at", *primary_key)``.

For both, we always physically write the **history first** (so failure
modes don't lose the new snapshot) and the **latest after** (a stale
latest is recoverable from history; the inverse is not true).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def write_snapshot(
    snapshot_df: pd.DataFrame,
    latest_path: Path,
    history_path: Path,
    snapshot_at: pd.Timestamp | None = None,
    primary_key: list[str] | None = None,
) -> None:
    """Persist a snapshot to its history (append) and to its latest pointer."""
    if snapshot_df.empty:
        logger.warning(
            "write_snapshot called with an empty frame for %s; skipping",
            latest_path.name,
        )
        return

    latest_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.parent.mkdir(parents=True, exist_ok=True)

    single_row_mode = snapshot_df.index.name == "snapshot_at"

    if single_row_mode:
        hist_df = snapshot_df
    else:
        if snapshot_at is None:
            snapshot_at = pd.Timestamp.now(tz="UTC").floor("min")
        hist_df = snapshot_df.reset_index()
        hist_df["snapshot_at"] = snapshot_at

    if history_path.exists():
        existing = pd.read_parquet(history_path)
        combined = pd.concat([existing, hist_df], axis=0)
    else:
        combined = hist_df.copy()

    if single_row_mode:
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    else:
        dedup_keys = ["snapshot_at"] + (primary_key or [])
        combined = combined.drop_duplicates(subset=dedup_keys, keep="last")
        combined = combined.sort_values(by=dedup_keys).reset_index(drop=True)

    combined.to_parquet(history_path, engine="pyarrow", compression="snappy")
    snapshot_df.to_parquet(latest_path, engine="pyarrow", compression="snappy")

    logger.info(
        "Wrote snapshot: latest=%s (%d rows), history=%s (%d rows total)",
        latest_path.name, len(snapshot_df), history_path.name, len(combined),
    )
