"""Crypto cycle features: Bitcoin halving clock (Fase 5).

VISION lists "cicli specifici crypto (halving)" as a factor to test. The
halving — when Bitcoin's block subsidy halves (~every 210k blocks, ~4 years) —
is the most-cited crypto cycle anchor. Whether it still carries predictive
information in 2026+ or is "priced in" is an open research question
(OPEN_QUESTIONS); this module only builds the *feature*, honestly and causally,
so a model can be asked the question.

Halving dates are **fixed historical facts** (past) plus the protocol-scheduled
next one — hardcoded as explicit constants (asset-class-agnostic: a feature is
just a date table, ADR-014). The features at day ``t`` use only ``t`` and known
past/future *scheduled* dates, never realised future prices, so there is no
look-ahead on market data.
"""

from __future__ import annotations

from typing import Final, cast

import pandas as pd

# Bitcoin halving dates (UTC). Past ones are realised facts; 2028 is the
# protocol-scheduled estimate (block-height based, ~±weeks). Used only as a
# calendar anchor for cycle-phase features, not as a price prediction.
_HALVING_ISO: Final[list[str]] = [
    "2012-11-28",
    "2016-07-09",
    "2020-05-11",
    "2024-04-20",
    "2028-04-17",  # scheduled estimate
]
HALVING_DATES: Final[pd.DatetimeIndex] = pd.DatetimeIndex(pd.to_datetime(_HALVING_ISO, utc=True))

# Nominal cycle length between halvings (~4 years). Used to normalise the
# cycle phase into [0, 1].
_CYCLE_DAYS: Final[float] = 4 * 365.25


def days_since_last_halving(index: pd.DatetimeIndex) -> pd.Series:
    """Days elapsed since the most recent halving on/before each timestamp.

    For dates before the first known halving the value is ``NaN`` (no anchor
    yet — never guessed). Pure calendar arithmetic, no market data.
    """
    idx = pd.DatetimeIndex(index)
    halvings = HALVING_DATES.sort_values()
    # for each timestamp, find the last halving <= t (searchsorted, right side)
    pos = halvings.searchsorted(idx, side="right") - 1
    out = pd.Series(index=idx, dtype="float64", name="days_since_halving")
    valid = pos >= 0
    last_halving = halvings[pos.clip(min=0)]
    deltas = (idx - last_halving).days.astype("float64")
    out[valid] = deltas[valid]
    return out


def days_to_next_halving(index: pd.DatetimeIndex) -> pd.Series:
    """Days until the next scheduled halving after each timestamp.

    ``NaN`` after the last known scheduled halving (no further anchor). Pure
    calendar arithmetic.
    """
    idx = pd.DatetimeIndex(index)
    halvings = HALVING_DATES.sort_values()
    pos = halvings.searchsorted(idx, side="right")  # first halving strictly after t
    out = pd.Series(index=idx, dtype="float64", name="days_to_halving")
    valid = pos < len(halvings)
    next_halving = halvings[pos.clip(max=len(halvings) - 1)]
    deltas = (next_halving - idx).days.astype("float64")
    out[valid] = deltas[valid]
    return out


def halving_cycle_phase(index: pd.DatetimeIndex) -> pd.Series:
    """Position within the current ~4-year halving cycle, in ``[0, 1)``.

    ``0`` just after a halving, approaching ``1`` as the next nears. Computed as
    ``days_since_last_halving / nominal_cycle_length`` (clipped to ``[0, 1)``),
    so it is a smooth cyclical feature a model can use without hardcoding which
    halving we are in. ``NaN`` before the first halving.
    """
    since = days_since_last_halving(index)
    phase = (since / _CYCLE_DAYS).clip(upper=0.999)
    return cast("pd.Series", phase).rename("halving_phase")


def halving_features(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Assemble the causal halving-cycle features on a given index.

    Columns: ``days_since_halving``, ``days_to_halving``, ``halving_phase``.
    All are pure calendar features (no market data), safe to lag/join into a
    design matrix like any other causal feature.
    """
    out = pd.DataFrame(index=pd.DatetimeIndex(index))
    out.index.name = index.name or "date"
    out["days_since_halving"] = days_since_last_halving(index)
    out["days_to_halving"] = days_to_next_halving(index)
    out["halving_phase"] = halving_cycle_phase(index)
    return out
