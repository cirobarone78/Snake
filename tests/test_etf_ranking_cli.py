"""Offline tests for the weekly runner's non-network parts (WP4).

Yahoo is unreachable from the sandbox, so the fetch is exercised through a stub
source (the fixture-first convention of the plan §4). What is checked here is
the wiring the cron depends on: partial bars dropped, dead feeds reported,
panel rebuilt from the fetched bars, and the fail-safe that decides whether the
run is allowed to trade at all.
"""

from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from src.assets.asset import Asset, AssetClass, get_asset_by_symbol
from src.assets.sectors import SECTOR_ETFS
from src.execution.etf_rotation import SCENARIO_ID, decide_from_panel, ensure_scenario
from src.execution.scenarios import ScenarioStore
from src.ingestion.tier1.etf_ranking_cli import (
    MAX_VALIDATION_AGE_DAYS,
    build_panel,
    fetch_history,
    scenario_snapshot,
    validation_status,
)
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

NOW = pd.Timestamp("2026-08-24T12:00:00Z")


def _ohlcv(n: int, last: str = "2026-08-21", drift: float = 0.0005) -> pd.DataFrame:
    idx = pd.date_range(end=pd.Timestamp(last, tz="UTC"), periods=n, freq="D")
    close = 100.0 * np.cumprod(1.0 + drift * np.ones(n))
    return pd.DataFrame(
        {"open": close, "high": close * 1.01, "low": close * 0.99, "close": close,
         "volume": np.full(n, 1_000_000.0)},
        index=idx,
    )


class StubSource(YahooFinanceSource):
    """Yahoo stand-in: canned frames per symbol, optional failures."""

    def __init__(self, frames: dict[str, pd.DataFrame], failing: set[str] | None = None) -> None:
        self.frames = frames
        self.failing = failing or set()

    def fetch_ohlcv(
        self,
        asset: Asset,
        start: datetime | str,
        end: datetime | str | None = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        if asset.symbol in self.failing:
            raise RuntimeError(f"boom for {asset.symbol}")
        return self.frames.get(asset.symbol, pd.DataFrame())


def _asset(symbol: str) -> Asset:
    return Asset(
        symbol=symbol,
        name=symbol,
        asset_class=AssetClass.ETF,
        yahoo_symbol=symbol,
        tier=3,
    )


# --- fetch ------------------------------------------------------------------


def test_fetch_drops_todays_partial_bar() -> None:
    frame = _ohlcv(10, last="2026-08-24")  # includes "today"
    history, checks = fetch_history(StubSource({"A": frame}), [_asset("A")], "2026-01-01", now=NOW)
    assert len(history["A"]) == 9
    assert history["A"].index.max() < NOW.normalize()
    assert checks[0].is_fresh is True


def test_fetch_reports_a_failing_symbol_as_not_fresh() -> None:
    history, checks = fetch_history(
        StubSource({}, failing={"A"}), [_asset("A")], "2026-01-01", now=NOW
    )
    assert history == {}
    assert checks[0].is_fresh is False
    assert checks[0].last_timestamp is None


def test_fetch_flags_a_frozen_feed() -> None:
    """ADR-026: a feed that keeps returning old bars is worse than a missing one."""
    stale = _ohlcv(10, last="2026-07-01")
    _, checks = fetch_history(StubSource({"A": stale}), [_asset("A")], "2026-01-01", now=NOW)
    assert checks[0].is_fresh is False
    assert "STALE" in checks[0].message()


def test_fetch_reports_an_empty_frame_as_not_fresh() -> None:
    history, checks = fetch_history(StubSource({}), [_asset("A")], "2026-01-01", now=NOW)
    assert history == {}
    assert checks[0].is_fresh is False


# --- panel ------------------------------------------------------------------


def test_panel_is_rebuilt_from_the_fetched_bars() -> None:
    history = {"A": _ohlcv(300, drift=0.001), "B": _ohlcv(300, drift=0.0002)}
    benchmark = _ohlcv(300, drift=0.0005)
    panel, version = build_panel(history, benchmark)
    assert not panel.empty
    assert set(panel["symbol"]) == {"A", "B"}
    assert {"rel_ret_60", "vol_60", "regime", "close"} <= set(panel.columns)
    assert len(version) == 16  # schema hash, so a changed feature set is visible


def test_panel_supports_a_decision_and_the_strongest_name_wins() -> None:
    history = {"A": _ohlcv(300, drift=0.002), "B": _ohlcv(300, drift=-0.001)}
    panel, version = build_panel(history, _ohlcv(300, drift=0.0005))
    decision = decide_from_panel(panel, dataset_version=version)
    assert decision.ranked[0].symbol == "A"
    assert decision.predictive is False
    assert decision.dataset_version == version


# --- fail-safe: the validation report ---------------------------------------


def _write_validation(path, generated_at: str) -> None:
    path.write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "train_weeks": 156,
                "test_weeks": 52,
                "ic_bar": 0.03,
                "verdicts": [{"horizon": 20, "adoption_bar_passed": False}],
            }
        ),
        encoding="utf-8",
    )


def test_fresh_validation_report_raises_no_warning(tmp_path) -> None:
    path = tmp_path / "ranking_backtest.json"
    _write_validation(path, "2026-08-20T00:00:00+00:00")
    summary, warning = validation_status(path, now=NOW)
    assert warning is None
    assert summary is not None
    assert summary["verdict_20d"]["adoption_bar_passed"] is False
    assert summary["age_days"] == pytest.approx(4.5, abs=0.1)


def test_old_validation_report_is_reported_as_stale(tmp_path) -> None:
    path = tmp_path / "ranking_backtest.json"
    old = (NOW - pd.Timedelta(days=MAX_VALIDATION_AGE_DAYS + 10)).isoformat()
    _write_validation(path, old)
    summary, warning = validation_status(path, now=NOW)
    assert summary is not None
    assert warning is not None
    assert "STALE" in warning


def test_missing_validation_report_is_named_not_guessed(tmp_path) -> None:
    summary, warning = validation_status(tmp_path / "nope.json", now=NOW)
    assert summary is None
    assert warning is not None
    assert "missing" in warning


def test_the_committed_validation_report_is_the_failed_one() -> None:
    """Guards the premise of this whole work package, not just the code."""
    from src.ingestion.tier1.etf_ranking_cli import VALIDATION_PATH

    if not VALIDATION_PATH.exists():  # pragma: no cover - present in the repo
        pytest.skip("validation report not in the checkout")
    payload = json.loads(VALIDATION_PATH.read_text(encoding="utf-8"))
    primary = next(v for v in payload["verdicts"] if v["horizon"] == 20)
    assert primary["adoption_bar_passed"] is False


# --- scenario snapshot -------------------------------------------------------


def test_snapshot_of_an_untouched_scenario_is_all_cash(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    ensure_scenario(store)
    snap = scenario_snapshot(store, SCENARIO_ID, marks={})
    assert snap["cash"] == pytest.approx(10_000.0)
    assert snap["equity"] == pytest.approx(10_000.0)
    assert snap["return_pct"] == pytest.approx(0.0)
    assert snap["positions"] == []
    assert snap["started_at"] is None


# --- the universe the runner actually trades ---------------------------------


def test_benchmark_and_universe_are_the_pre_registered_ones() -> None:
    """D1/D2 are pre-registered: a silent universe change would invalidate WP3."""
    assert get_asset_by_symbol("SPY") is not None
    assert len(SECTOR_ETFS) == 20


# --- end to end, offline -----------------------------------------------------


def test_full_run_writes_ledger_scenario_and_payloads(tmp_path, monkeypatch) -> None:
    """The whole cron path with a stubbed feed: nothing here touches the network."""
    import json as _json

    from src.ingestion.tier1 import etf_ranking_cli as cli

    universe = [a.symbol for a in SECTOR_ETFS]
    frames = {s: _ohlcv(400, last="2026-08-21", drift=0.0004 + i * 0.00002)
              for i, s in enumerate(universe)}
    frames["SPY"] = _ohlcv(400, last="2026-08-21", drift=0.0005)

    monkeypatch.setattr(cli, "YahooFinanceSource", lambda: StubSource(frames))
    monkeypatch.setattr(cli, "REPORT_PATH", tmp_path / "ranking_report.json")
    monkeypatch.setattr(cli, "MODEL_PATH", tmp_path / "ranking_model.json")
    monkeypatch.setattr(cli, "VALIDATION_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(cli, "ScenarioStore", lambda: ScenarioStore(root=tmp_path / "paper"))
    monkeypatch.setattr(
        "sys.argv", ["etf_ranking_cli", "--ledger", str(tmp_path / "ledger.jsonl")]
    )
    # a missing validation report is a warning, not a reason to trade blind:
    # the fail-safe must fire, so give the runner a real (failed) verdict
    _write_validation(tmp_path / "validation.json", "2026-08-20T00:00:00+00:00")
    monkeypatch.setattr(cli, "VALIDATION_PATH", tmp_path / "validation.json")

    cli.main()

    ledger = tmp_path / "ledger.jsonl"
    rows = [_json.loads(line) for line in ledger.read_text().splitlines()]
    assert len(rows) == len(universe) * 2  # every symbol, both horizons
    assert all(r["outcome"] is None for r in rows), "nothing can be resolved on day one"
    assert all(r["probability_outperform"] is None for r in rows)
    assert sum(1 for r in rows if r["selected"] and r["horizon_days"] == 20) == 5

    report = _json.loads((tmp_path / "ranking_report.json").read_text())
    assert report["status"] == "ok"
    assert report["predictive"] is False
    assert len(report["items"]) == len(universe)

    model = _json.loads((tmp_path / "ranking_model.json").read_text())
    assert model["adoption_bar"]["passed"] is False
    assert model["scenario"]["cash"] == pytest.approx(10_000.0)

    store = ScenarioStore(root=tmp_path / "paper")
    pending = store.load_pending(SCENARIO_ID)
    assert len(pending) == 5, "five buys queued, none filled today"
    assert all(o.filled_at is None for o in pending)


def test_second_run_on_the_same_date_adds_nothing(tmp_path, monkeypatch) -> None:
    import json as _json

    from src.ingestion.tier1 import etf_ranking_cli as cli

    universe = [a.symbol for a in SECTOR_ETFS]
    frames = {s: _ohlcv(400, last="2026-08-21", drift=0.0004 + i * 0.00002)
              for i, s in enumerate(universe)}
    frames["SPY"] = _ohlcv(400, last="2026-08-21", drift=0.0005)
    _write_validation(tmp_path / "validation.json", "2026-08-20T00:00:00+00:00")

    monkeypatch.setattr(cli, "YahooFinanceSource", lambda: StubSource(frames))
    monkeypatch.setattr(cli, "REPORT_PATH", tmp_path / "ranking_report.json")
    monkeypatch.setattr(cli, "MODEL_PATH", tmp_path / "ranking_model.json")
    monkeypatch.setattr(cli, "VALIDATION_PATH", tmp_path / "validation.json")
    monkeypatch.setattr(cli, "ScenarioStore", lambda: ScenarioStore(root=tmp_path / "paper"))
    monkeypatch.setattr(
        "sys.argv", ["etf_ranking_cli", "--ledger", str(tmp_path / "ledger.jsonl")]
    )

    cli.main()
    ledger_after_first = (tmp_path / "ledger.jsonl").read_text()
    orders_after_first = len(ScenarioStore(root=tmp_path / "paper").orders(SCENARIO_ID))

    cli.main()

    # the second run stamps a new `emitted_at` but refers to the same decision
    # bar: neither the ledger nor the order book may grow
    assert (tmp_path / "ledger.jsonl").read_text() == ledger_after_first
    assert len(ScenarioStore(root=tmp_path / "paper").orders(SCENARIO_ID)) == orders_after_first
    rows = [_json.loads(line) for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert len({r["data_cutoff"] for r in rows}) == 1
