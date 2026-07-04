"""Scenario manager: N independent paper portfolios (Fase 6, ADR-011).

Each scenario (``small_1k``, ``mid_10k``, ``large_100k``, or custom) owns its
portfolio, its order audit trail and its equity curve. Two lifecycle
operations, both audit-preserving:

- **reset**: the scenario restarts from its initial capital; the previous
  run's files move to an archive folder. *Nothing is ever deleted* (ADR-011:
  the archive is value for a-posteriori analysis).
- **fork**: clone a scenario's current state under a new id, to try an
  alternative strategy from the same starting point.

Storage layout (small JSON for state, parquet for time series)::

    data/paper/
      scenarios.json                  registry of scenario ids + config
      <id>/state.json                 portfolio + last processed timestamp
      <id>/orders.parquet             full order audit trail (append)
      <id>/equity.parquet             equity curve (append, one row per bar)
      _archive/<id>__<reset-ts>/...   previous runs, moved on reset

The directory is meant to be *committed* (same rationale as the news history,
ADR-025): the live-shadow cron runs on ephemeral containers, and the paper
track record must survive them — it IS the deliverable of Fase 6.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pandas as pd

from src.execution.orders import Order, OrderStatus
from src.execution.portfolio import Portfolio

DEFAULT_ROOT = Path("data/paper")
# ADR-011 proposed defaults (EUR).
DEFAULT_SCENARIOS: dict[str, float] = {
    "small_1k": 1_000.0,
    "mid_10k": 10_000.0,
    "large_100k": 100_000.0,
}


@dataclass
class ScenarioState:
    """A scenario's persistent state between runs."""

    scenario_id: str
    initial_cash: float
    portfolio: Portfolio
    last_processed: pd.Timestamp | None = None
    # Target weights decided on the last run: the strategy trades on signal
    # CHANGES, not on daily drift (rebalance drag = pure fee churn).
    last_targets: dict[str, float] = field(default_factory=dict)


class ScenarioStore:
    """Filesystem persistence for scenarios. All writes are atomic-enough for
    a single sequential cron writer (the only writer we have)."""

    def __init__(self, root: Path = DEFAULT_ROOT) -> None:
        self.root = root

    # -- registry ----------------------------------------------------------

    def _registry_path(self) -> Path:
        return self.root / "scenarios.json"

    def registry(self) -> dict[str, dict[str, object]]:
        path = self._registry_path()
        if not path.exists():
            return {}
        loaded = json.loads(path.read_text())
        if not isinstance(loaded, dict):
            raise ValueError("corrupt scenarios.json")
        return {str(k): dict(v) for k, v in loaded.items()}

    def _write_registry(self, reg: dict[str, dict[str, object]]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._registry_path().write_text(json.dumps(reg, indent=2, default=str))

    # -- lifecycle ---------------------------------------------------------

    def create(self, scenario_id: str, initial_cash: float) -> ScenarioState:
        if initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        reg = self.registry()
        if scenario_id in reg:
            raise ValueError(f"scenario {scenario_id!r} already exists")
        state = ScenarioState(
            scenario_id=scenario_id,
            initial_cash=initial_cash,
            portfolio=Portfolio(cash=initial_cash),
        )
        reg[scenario_id] = {"initial_cash": initial_cash}
        self._write_registry(reg)
        self.save(state)
        return state

    def load(self, scenario_id: str) -> ScenarioState:
        reg = self.registry()
        if scenario_id not in reg:
            raise KeyError(f"unknown scenario {scenario_id!r}")
        raw = json.loads((self.root / scenario_id / "state.json").read_text())
        last = raw.get("last_processed")
        last_ts: pd.Timestamp | None = None
        if last:
            parsed = pd.Timestamp(last)
            if parsed is pd.NaT:
                raise ValueError(f"corrupt last_processed in scenario {scenario_id!r}")
            last_ts = cast("pd.Timestamp", parsed)
        raw_targets = raw.get("last_targets") or {}
        return ScenarioState(
            scenario_id=scenario_id,
            initial_cash=float(raw["initial_cash"]),
            portfolio=Portfolio.from_record(raw["portfolio"]),
            last_processed=last_ts,
            last_targets={str(k): float(v) for k, v in raw_targets.items()},
        )

    def save(self, state: ScenarioState) -> None:
        d = self.root / state.scenario_id
        d.mkdir(parents=True, exist_ok=True)
        payload = {
            "initial_cash": state.initial_cash,
            "portfolio": state.portfolio.to_record(),
            "last_processed": str(state.last_processed) if state.last_processed is not None else None,
            "last_targets": state.last_targets,
        }
        (d / "state.json").write_text(json.dumps(payload, indent=2))

    def reset(self, scenario_id: str) -> ScenarioState:
        """Archive the current run and restart from the initial capital."""
        state = self.load(scenario_id)  # validates existence
        src = self.root / scenario_id
        stamp = pd.Timestamp.now(tz="UTC").strftime("%Y%m%dT%H%M%S")
        dst = self.root / "_archive" / f"{scenario_id}__{stamp}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        fresh = ScenarioState(
            scenario_id=scenario_id,
            initial_cash=state.initial_cash,
            portfolio=Portfolio(cash=state.initial_cash),
        )
        self.save(fresh)
        return fresh

    def fork(self, scenario_id: str, new_id: str) -> ScenarioState:
        """Clone a scenario's current state (and files) under ``new_id``."""
        reg = self.registry()
        if new_id in reg:
            raise ValueError(f"scenario {new_id!r} already exists")
        state = self.load(scenario_id)
        src = self.root / scenario_id
        dst = self.root / new_id
        shutil.copytree(src, dst)
        reg[new_id] = {"initial_cash": state.initial_cash, "forked_from": scenario_id}
        self._write_registry(reg)
        forked = self.load(new_id)
        return forked

    # -- time series appends -------------------------------------------------

    def append_orders(self, scenario_id: str, orders: list[Order]) -> None:
        """Upsert by ``order_id``: a re-saved order (e.g. pending -> filled on a
        later run) replaces its previous record instead of duplicating it."""
        if not orders:
            return
        path = self.root / scenario_id / "orders.parquet"
        new = pd.DataFrame([o.to_record() for o in orders])
        if path.exists():
            prev = pd.read_parquet(path)
            prev = prev[~prev["order_id"].isin(list(new["order_id"]))]
            new = pd.concat([prev, new], ignore_index=True)
        new.to_parquet(path, index=False)

    def orders(self, scenario_id: str) -> pd.DataFrame:
        path = self.root / scenario_id / "orders.parquet"
        return pd.read_parquet(path) if path.exists() else pd.DataFrame()

    def load_pending(self, scenario_id: str) -> list[Order]:
        """Rebuild the still-working orders (cross-run continuity of t+1 fills)."""
        df = self.orders(scenario_id)
        if df.empty:
            return []
        pending = df[df["status"] == OrderStatus.PENDING.value]
        return [Order.from_record(dict(r)) for _, r in pending.iterrows()]

    def append_equity(self, scenario_id: str, ts: pd.Timestamp, equity: float, cash: float) -> None:
        path = self.root / scenario_id / "equity.parquet"
        new = pd.DataFrame([{"ts": ts, "equity": equity, "cash": cash}])
        if path.exists():
            prev = pd.read_parquet(path)
            # idempotenza: un rerun sullo stesso bar sovrascrive, non duplica
            prev = prev[prev["ts"] != ts]
            new = pd.concat([prev, new], ignore_index=True)
        # sort_values overloads are unresolvable without pandas stubs
        cast("Any", new).sort_values("ts").to_parquet(path, index=False)

    def equity_curve(self, scenario_id: str) -> pd.Series:
        path = self.root / scenario_id / "equity.parquet"
        if not path.exists():
            return pd.Series(dtype=float, name="equity")
        df = pd.read_parquet(path).sort_values("ts")
        return pd.Series(df["equity"].to_numpy(), index=pd.DatetimeIndex(df["ts"]), name="equity")


def ensure_default_scenarios(store: ScenarioStore) -> list[str]:
    """Create the ADR-011 default scenarios if missing; returns all ids."""
    reg = store.registry()
    for sid, cash in DEFAULT_SCENARIOS.items():
        if sid not in reg:
            store.create(sid, cash)
    return sorted(store.registry())
