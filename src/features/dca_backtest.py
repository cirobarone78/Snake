"""Does the DCA sleeve rule actually beat the naive alternatives? (validation)

``dca_advisor`` proposes a rule for spending a small monthly slice on one of
several satellite assets. A rule that is never measured is a superstition, so
this module replays the **actual cash flows** — a fixed budget, once a month,
from a start date — and compares the rule against the honest alternatives:

- ``split``     — equal thirds every month (the do-nothing benchmark)
- ``rotate``    — round-robin, one asset per month in fixed order
- ``momentum``  — always buy the strongest performer (the naive intuition, and
                  the one the conditional-outcome study already argued against)
- ``discount``  — always buy the cheapest inside its own trailing range
- ``underweight`` — pure rebalancing toward the target weights
- ``advisor``   — the blend implemented in ``dca_advisor.advise``
- ``<SYMBOL>``  — always the same asset (one baseline per sleeve member)
- ``random``    — seeded random pick, the "was it luck?" control

Why the sleeve alone: the core legs (BTC, ETH) are identical under every rule,
so including them would dilute the comparison with a large common term. The
sleeve is where the decision lives, so the sleeve is what gets measured.

Metrics, and why these:

- ``multiple`` — what the money became. Intuitive, and the first thing anyone
  looks at, but on a few dozen monthly purchases it is dominated by *which asset
  happened to run*, not by the rule. Reported, never trusted alone.
- ``vs_split`` — the same number divided by the equal-split benchmark's. The
  equal split is the only alternative that requires no choice at all, so it is
  the honest bar: a rule that cannot clear ``1.0`` is not earning its complexity.
- ``max_drawdown_pct`` — worst peak-to-trough fall of the sleeve's value.
- ``weight_drift_pp`` — total absolute distance of the final weights from the
  target, in percentage points. A rebalancing rule's actual promise is *this*,
  not return: keeping the sleeve from silently turning into one asset.

Single-asset baselines are printed for context, but they are hindsight: nobody
could pick the winner in advance, which is the whole reason the sleeve exists.
``random_control`` makes the luck comparison explicit by re-running the random
rule over many seeds and locating a rule inside that distribution.

Honesty guards (CLAUDE.md):
- Monthly contributions over a few years means **tens of purchases**, not
  thousands. ``n_purchases`` is reported so the sample is never hidden.
- ``split_halves`` re-runs the comparison on the first and second half of the
  period: a ranking that flips between halves is noise, and the caller is meant
  to say so out loud.
- Purchases execute at the close **of the decision date** using only prior data;
  no look-ahead. Fees are a caller-supplied percentage, not assumed away.

Pure functions over pandas; unit-testable offline, no network.
"""

from __future__ import annotations

import random
from typing import Any, cast

import numpy as np
import pandas as pd

from src.features.dca_advisor import (
    DEFAULT_GAP_WEIGHT,
    DEFAULT_LOOKBACK,
    advise,
    align_timestamp,
    relative_discount,
)

# Rules that need no per-asset baseline registration.
BASE_RULES: tuple[str, ...] = (
    "advisor", "underweight", "discount", "momentum", "split", "rotate", "random",
)

# Trailing window for the momentum baseline: the horizon at which the rotation
# study found chasing strength was actively unhelpful, so it is the fair test.
MOMENTUM_LOOKBACK: int = 63

_RESULT_COLS = [
    "rule", "invested_eur", "final_value_eur", "multiple", "vs_split",
    "max_drawdown_pct", "weight_drift_pp", "n_purchases", "units_json",
]


def month_ends(index: pd.DatetimeIndex, day_of_month: int = 1) -> list[pd.Timestamp]:
    """Trading dates on which a monthly contribution lands.

    For each calendar month present in ``index``, the first available date on or
    after ``day_of_month``; if the month has none (a short tail), the month is
    skipped rather than shifted into the next one.
    """
    if day_of_month < 1 or day_of_month > 28:
        raise ValueError("day_of_month must be in [1, 28]")
    dates: list[pd.Timestamp] = []
    seen: set[tuple[int, int]] = set()
    for raw in index:
        ts = cast("pd.Timestamp", pd.Timestamp(cast("Any", raw)))
        key = (int(ts.year), int(ts.month))
        if key in seen or int(ts.day) < day_of_month:
            continue
        seen.add(key)
        dates.append(ts)
    return dates


def _momentum_pick(panel: pd.DataFrame, as_of: pd.Timestamp, lookback: int) -> str:
    window = cast("pd.DataFrame", panel.loc[panel.index <= as_of].tail(lookback + 1)).ffill()
    if len(window) < 2:
        return str(panel.columns[0])
    ret = window.iloc[-1] / window.iloc[0] - 1.0
    ret = ret.dropna()
    if ret.empty:
        return str(panel.columns[0])
    # Ties broken by symbol so a run is reproducible.
    return str(ret.sort_values(ascending=False, kind="stable").index[0])


def _allocate(
    rule: str,
    panel: pd.DataFrame,
    as_of: pd.Timestamp,
    units: dict[str, float],
    targets: dict[str, float],
    budget: float,
    step: int,
    rng: random.Random,
    lookback: int,
    gap_weight: float,
) -> dict[str, float]:
    """Euro to spend per symbol on this date, under ``rule``."""
    symbols = [str(c) for c in panel.columns]
    if rule == "split":
        return {s: budget / len(symbols) for s in symbols}
    if rule == "rotate":
        return {symbols[step % len(symbols)]: budget}
    if rule == "random":
        return {rng.choice(symbols): budget}
    if rule == "momentum":
        return {_momentum_pick(panel, as_of, MOMENTUM_LOOKBACK): budget}
    if rule == "discount":
        pos = relative_discount(panel, lookback=lookback, as_of=as_of).dropna()
        if pos.empty:
            return {symbols[0]: budget}
        return {str(pos.sort_values(kind="stable").index[0]): budget}
    if rule in {"advisor", "underweight"}:
        ranked = advise(
            panel,
            target_weights=targets,
            holdings_units=units,
            lookback=lookback,
            gap_weight=1.0 if rule == "underweight" else gap_weight,
            as_of=as_of,
        )
        if ranked.empty:
            return {symbols[0]: budget}
        return {str(ranked.iloc[0]["symbol"]): budget}
    if rule in symbols:
        return {rule: budget}
    raise ValueError(f"unknown rule: {rule!r}")


def simulate(
    panel_close: pd.DataFrame,
    rule: str,
    budget_eur: float = 10.0,
    target_weights: dict[str, float] | None = None,
    start: pd.Timestamp | str | None = None,
    end: pd.Timestamp | str | None = None,
    day_of_month: int = 1,
    fee_pct: float = 0.0,
    lookback: int = DEFAULT_LOOKBACK,
    gap_weight: float = DEFAULT_GAP_WEIGHT,
    seed: int = 0,
) -> dict[str, Any]:
    """Replay monthly contributions under one rule; return the outcome summary.

    ``fee_pct`` is a percentage taken off each purchase (0.5 = 0.5%), matching a
    retail exchange spread+fee. Every purchase fills at that date's close using
    only data up to and including it.

    The returned ``value`` series is the sleeve's mark-to-market worth on every
    date, which is what ``max_drawdown_pct`` is measured on — a rule that ends
    in the same place through a deeper hole is not the same rule.
    """
    panel = cast("pd.DataFrame", panel_close.sort_index()).astype("float64")
    if start is not None:
        panel = cast("pd.DataFrame", panel.loc[panel.index >= align_timestamp(panel.index, start)])
    if end is not None:
        panel = cast("pd.DataFrame", panel.loc[panel.index <= align_timestamp(panel.index, end)])
    symbols = [str(c) for c in panel.columns]
    units: dict[str, float] = dict.fromkeys(symbols, 0.0)
    if panel.empty or not symbols:
        return {
            "rule": rule, "invested_eur": 0.0, "final_value_eur": 0.0,
            "multiple": None, "max_drawdown_pct": None, "weight_drift_pp": None,
            "n_purchases": 0, "units": units, "spent": dict.fromkeys(symbols, 0.0),
            "value": pd.Series(dtype="float64"),
        }

    targets = target_weights or dict.fromkeys(symbols, 1.0 / len(symbols))
    rng = random.Random(seed)
    filled = panel.ffill()
    spent: dict[str, float] = dict.fromkeys(symbols, 0.0)
    invested = 0.0
    n_purchases = 0
    # Units held after each purchase date; reindexed+ffilled below into the
    # step function that turns prices into a daily portfolio value.
    units_log: dict[pd.Timestamp, dict[str, float]] = {}

    for step, date in enumerate(month_ends(cast("pd.DatetimeIndex", panel.index), day_of_month)):
        alloc = _allocate(
            rule, panel, date, units, targets, budget_eur, step, rng, lookback, gap_weight
        )
        prices = filled.loc[date]
        bought = False
        for sym, eur in alloc.items():
            price = float(prices.get(sym, np.nan))
            if not np.isfinite(price) or price <= 0 or eur <= 0:
                continue
            units[sym] += (eur * (1.0 - fee_pct / 100.0)) / price
            spent[sym] += eur
            invested += eur
            bought = True
        if bought:
            n_purchases += 1
        units_log[date] = dict(units)

    value = _value_curve(filled, units_log)
    final_value = float(value.iloc[-1]) if not value.empty else 0.0

    return {
        "rule": rule,
        "invested_eur": round(invested, 2),
        "final_value_eur": round(final_value, 2),
        "multiple": round(final_value / invested, 4) if invested > 0 else None,
        "max_drawdown_pct": _max_drawdown_pct(value),
        "weight_drift_pp": _weight_drift_pp(filled, units, targets),
        "n_purchases": n_purchases,
        "units": units,
        "spent": spent,
        "value": value,
    }


def _value_curve(
    filled: pd.DataFrame, units_log: dict[pd.Timestamp, dict[str, float]]
) -> pd.Series:
    """Daily mark-to-market value of the sleeve given the purchase history."""
    if not units_log:
        return pd.Series(0.0, index=filled.index, dtype="float64")
    held = pd.DataFrame.from_dict(units_log, orient="index").reindex(columns=filled.columns)
    held = cast("pd.DataFrame", held.sort_index().reindex(filled.index).ffill().fillna(0.0))
    return cast("pd.Series", (held * filled).sum(axis=1).astype("float64"))


def _max_drawdown_pct(value: pd.Series) -> float | None:
    """Worst peak-to-trough fall of the value curve, as a positive percentage.

    Only the stretch after the first euro is invested counts — the leading zeros
    of an empty portfolio are not a drawdown.
    """
    invested = cast("pd.Series", value[value > 0])
    if len(invested) < 2:
        return None
    peak = cast("pd.Series", invested.cummax())
    drawdown = invested / peak - 1.0
    worst = float(drawdown.min())
    return round(abs(worst) * 100.0, 2) if np.isfinite(worst) else None


def _weight_drift_pp(
    filled: pd.DataFrame, units: dict[str, float], targets: dict[str, float]
) -> float | None:
    """Total absolute gap between final weights and target, in percentage points.

    ``0`` = the sleeve ended exactly on plan; a large number means the sleeve
    quietly became a bet on whichever leg ran. This is what a rebalancing rule is
    actually for, so it is measured rather than asserted.
    """
    last = filled.iloc[-1]
    value = {s: units.get(s, 0.0) * float(last.get(s, np.nan)) for s in filled.columns}
    total = sum(v for v in value.values() if np.isfinite(v))
    if not np.isfinite(total) or total <= 0:
        return None
    target_total = sum(max(0.0, float(v)) for v in targets.values()) or 1.0
    drift = sum(
        abs(value[s] / total - max(0.0, float(targets.get(str(s), 0.0))) / target_total)
        for s in filled.columns
        if np.isfinite(value[s])
    )
    return round(drift * 100.0, 2)


def compare(
    panel_close: pd.DataFrame,
    rules: list[str] | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Run every rule over the same period; one row per rule, best multiple first.

    Defaults to :data:`BASE_RULES` plus a single-asset baseline per sleeve member.
    ``units_json`` keeps the accumulated units for inspection.
    """
    symbols = [str(c) for c in panel_close.columns]
    to_run = rules if rules is not None else [*BASE_RULES, *symbols]
    rows: list[dict[str, Any]] = []
    for rule in to_run:
        res = simulate(panel_close, rule, **kwargs)
        rows.append(
            {
                "rule": res["rule"],
                "invested_eur": res["invested_eur"],
                "final_value_eur": res["final_value_eur"],
                "multiple": res["multiple"],
                "vs_split": None,
                "max_drawdown_pct": res["max_drawdown_pct"],
                "weight_drift_pp": res["weight_drift_pp"],
                "n_purchases": res["n_purchases"],
                "units_json": {k: round(v, 8) for k, v in res["units"].items()},
            }
        )
    out = pd.DataFrame(rows, columns=_RESULT_COLS)
    # vs_split needs every row, so it is filled once the whole table exists. If
    # the caller excluded "split" there is no benchmark and the column stays null
    # rather than silently falling back to some other rule.
    if "split" not in to_run:
        benchmark = None
    else:
        matched = out.loc[out["rule"] == "split", "multiple"]
        benchmark = None if matched.empty or pd.isna(matched.iloc[0]) else float(matched.iloc[0])
    if benchmark:
        out["vs_split"] = [
            None if m is None or pd.isna(m) else round(float(m) / benchmark, 4)
            for m in out["multiple"]
        ]
    return cast(
        "pd.DataFrame",
        out.sort_values("multiple", ascending=False, na_position="last", kind="stable"),
    )


def random_control(
    panel_close: pd.DataFrame,
    rule: str = "advisor",
    n_seeds: int = 200,
    **kwargs: Any,
) -> dict[str, Any]:
    """Where does ``rule`` land inside the distribution of random picking?

    With a few dozen purchases, beating the equal split once proves nothing —
    a coin-flipping rule beats it about half the time. This re-runs the random
    rule over ``n_seeds`` seeds and reports the rule's percentile in that
    distribution. Around 50 means the rule is indistinguishable from luck; only
    a high percentile that also survives ``split_halves`` is worth anything.
    """
    kwargs.pop("seed", None)
    multiples: list[float] = []
    for seed in range(n_seeds):
        res = simulate(panel_close, "random", seed=seed, **kwargs)
        if res["multiple"] is not None:
            multiples.append(float(res["multiple"]))
    target = simulate(panel_close, rule, **kwargs)["multiple"]
    if not multiples or target is None:
        return {"rule": rule, "multiple": target, "n_seeds": len(multiples),
                "percentile": None, "random_median": None}
    arr = np.array(multiples, dtype="float64")
    return {
        "rule": rule,
        "multiple": round(float(target), 4),
        "n_seeds": len(multiples),
        "percentile": round(float((arr < float(target)).mean() * 100.0), 1),
        "random_median": round(float(np.median(arr)), 4),
        "random_p10": round(float(np.percentile(arr, 10)), 4),
        "random_p90": round(float(np.percentile(arr, 90)), 4),
    }


def split_halves(
    panel_close: pd.DataFrame,
    rules: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, pd.DataFrame]:
    """Same comparison on the first and second half of the period (OOS check).

    A rule whose ranking survives both halves is at least *stable*; one that wins
    the first half and loses the second is noise, and the report must say so.
    """
    panel = cast("pd.DataFrame", panel_close.sort_index())
    if len(panel) < 4:
        return {"first": pd.DataFrame(columns=_RESULT_COLS),
                "second": pd.DataFrame(columns=_RESULT_COLS)}
    mid = panel.index[len(panel) // 2]
    first = cast("pd.DataFrame", panel.loc[panel.index <= mid])
    second = cast("pd.DataFrame", panel.loc[panel.index > mid])
    return {
        "first": compare(first, rules=rules, **kwargs),
        "second": compare(second, rules=rules, **kwargs),
    }
