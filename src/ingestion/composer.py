# pyright: strict
"""Multi-source OHLCV composition (ADR-021).

Some assets need data from more than one provider to cover their full
useful history. POL is the canonical example: Yahoo (via MATIC-USD)
serves 2019-04 → 2025-03, Binance.us (POLUSDT) serves 2025-01 → present.

This module joins such fragments into a single canonical series, with
provenance tracked per-row, so feature engineering downstream can
operate on one DataFrame without re-implementing the merge each time.

Why a separate module: the data layout under ``data/raw/`` is provider-
indexed (one parquet per source per asset). The "canonical" series live
under ``data/processed/``. The composer is the bridge between the two.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

OHLCV_COLUMNS = ("open", "high", "low", "close", "volume")


def compose_ohlcv(sources: list[tuple[pd.DataFrame, str]]) -> pd.DataFrame:
    """Concatenate OHLCV frames into a single canonical series.

    Each input is a ``(frame, source_name)`` tuple. Frames must follow the
    project's standard OHLCV schema: ``open, high, low, close, volume``
    columns with a tz-aware UTC ``DatetimeIndex`` named ``timestamp``.

    Concatenation policy
    --------------------
    All frames are concatenated and sorted by timestamp. On overlap (same
    timestamp in two or more sources), the **later-listed** source wins:
    list sources in increasing priority (least-trusted first, most-trusted
    last). This matches the natural semantic of "newer sources extend or
    correct older ones".

    Output schema
    -------------
    Same OHLCV columns plus a ``source`` column with the provenance label
    for each row. Index is the same UTC DatetimeIndex.
    """
    if not sources:
        raise ValueError("compose_ohlcv requires at least one source")

    labeled: list[pd.DataFrame] = []
    for df, name in sources:
        if df.empty:
            continue
        missing = set(OHLCV_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"Source {name!r} is missing columns: {sorted(missing)}")
        labeled.append(df.assign(source=name))

    if not labeled:
        return _empty_composed_frame()

    combined = pd.concat(labeled, axis=0)
    combined = combined.sort_index(kind="stable")
    # ``keep="last"`` honours the priority order: when two rows share an
    # index, the one from the later-listed source survives.
    combined = combined[~combined.index.duplicated(keep="last")]

    logger.info(
        "Composed %d rows from %d sources: %s",
        len(combined),
        len(labeled),
        combined["source"].value_counts().to_dict(),
    )

    return combined[[*OHLCV_COLUMNS, "source"]]


def _empty_composed_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[*OHLCV_COLUMNS, "source"],
        index=pd.DatetimeIndex([], name="timestamp", tz="UTC"),
    )
