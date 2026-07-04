"""Replay engine (Fase 6): the strategy's history through the paper broker.

The live-shadow cron builds the paper track record one day at a time, forward,
out of sample. **Replay** answers a different question: *what would this exact
strategy have done over the past year, run through the very same broker* —
same cost model, same "decide at T, fill at T+1" discipline, same code path
(``run_daily``, driving a single dedicated scenario).

Two honest caveats, front and centre (mirrored in ``REPLAY_DISCLAIMER``):

- It is **backward-looking and in-sample**. The project's own research
  (Fasi 2-5) already found no directional edge in daily momentum; a replay
  curve illustrates *behaviour*, it is not evidence of an edge, and it is not
  the forward track record. That distinction is the whole point of the
  live-shadow run existing separately.
- Because replay reuses ``run_daily`` bar by bar, it is also a **consistency
  check**: the forward runner and the historical replay share one
  implementation, so they cannot silently disagree.

Pure over the price history; writes ``public/data/paper_replay.json`` for the
dashboard. No state is persisted in the repo (a throwaway store in a temp dir),
so ``data/paper/`` stays reserved for the live scenarios.
"""

from __future__ import annotations

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

import pandas as pd

from src.execution.live_shadow import DEFAULT_LOOKBACK, fetch_tier1_history, run_daily
from src.execution.report import _scenario_payload
from src.execution.scenarios import ScenarioStore

logger = logging.getLogger(__name__)

REPLAY_PATH = "public/data/paper_replay.json"
REPLAY_SCENARIO_ID = "replay"
REPLAY_INITIAL_CASH = 10_000.0

REPLAY_DISCLAIMER = (
    "Esecuzione STORICA (replay) della stessa strategia difensiva di momentum "
    "attraverso lo stesso broker del paper trading (stessi costi, fill a t+1). "
    "È backward-looking e IN-SAMPLE: illustra il comportamento passato e verifica "
    "la coerenza del motore, NON è il track record forward (quello è il "
    "live-shadow). Non è consulenza finanziaria."
)


def _decision_bars(history: dict[str, pd.DataFrame], lookback: int) -> pd.DatetimeIndex:
    """The common daily bars at which the strategy can first act, in order.

    Uses the intersection of the per-symbol indices so every decision sees a
    close for every symbol; drops the leading ``lookback + 1`` bars, where the
    momentum signal has no history yet (the strategy would only ever hold cash).
    """
    common: pd.Index | None = None
    for df in history.values():
        idx = df.sort_index().index
        common = idx if common is None else common.intersection(idx)
    if common is None or len(common) == 0:
        return pd.DatetimeIndex([])
    ordered = pd.DatetimeIndex(common.sort_values())
    return ordered[lookback + 1 :]


def replay_into(
    store: ScenarioStore,
    history: dict[str, pd.DataFrame],
    initial_cash: float = REPLAY_INITIAL_CASH,
    lookback: int = DEFAULT_LOOKBACK,
    scenario_id: str = REPLAY_SCENARIO_ID,
) -> None:
    """Step ``scenario_id`` through the whole history, one bar per ``run_daily``.

    Creates the scenario, then advances it bar by bar exactly as the cron would
    have, so the resulting equity curve/order trail is what the live-shadow
    would have produced over this window.
    """
    if not history:
        raise ValueError("empty history")
    store.create(scenario_id, initial_cash)
    for t in _decision_bars(history, lookback):
        window = {s: cast("Any", df).loc[:t] for s, df in history.items()}
        window = {s: df for s, df in window.items() if not df.empty}
        if not window:
            continue
        run_daily(store, window, lookback=lookback, scenario_ids=[scenario_id])


def build_replay_report(
    history: dict[str, pd.DataFrame],
    initial_cash: float = REPLAY_INITIAL_CASH,
    lookback: int = DEFAULT_LOOKBACK,
    generated_at: pd.Timestamp | None = None,
) -> dict[str, Any]:
    """Assemble the dashboard payload for the historical replay."""
    stamp = generated_at if generated_at is not None else pd.Timestamp.now(tz="UTC")
    with TemporaryDirectory() as tmp:
        store = ScenarioStore(root=Path(tmp) / "paper")
        replay_into(store, history, initial_cash=initial_cash, lookback=lookback)
        marks = {
            s: float(cast("float", df.sort_index()["close"].iloc[-1])) for s, df in history.items()
        }
        scenario = _scenario_payload(store, REPLAY_SCENARIO_ID, marks)
    return {
        "generated_at": stamp.isoformat(),
        "title": "Replay storico",
        "disclaimer": REPLAY_DISCLAIMER,
        "lookback": lookback,
        "symbols": sorted(history),
        "scenario": scenario,
    }


def main() -> None:
    """Fetch ~1 year of Tier 1 bars and write the replay report (cron entry)."""
    from src.features.report_json import write_report_json

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    start = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=400)).date().isoformat()
    history = fetch_tier1_history(start)
    if not history:
        raise SystemExit("no price history available, aborting replay")
    report = build_replay_report(history)
    write_report_json(report, Path(REPLAY_PATH))
    logger.info(
        "wrote replay report -> %s (return %.2f%%, %d bars)",
        REPLAY_PATH,
        report["scenario"]["return_pct"],
        len(report["scenario"]["curve"]),
    )


if __name__ == "__main__":
    main()
