"""Tests for the Fase 6 paper broker: no-look-ahead, costs, long-only, scenarios."""

from __future__ import annotations

import pandas as pd
import pytest

from src.backtest.costs import FeeModel, SlippageModel, TransactionCostModel
from src.execution import (
    Bar,
    Order,
    OrderStatus,
    OrderType,
    PaperBroker,
    Portfolio,
    ScenarioStore,
    Side,
    ensure_default_scenarios,
)

T0 = pd.Timestamp("2026-01-01 00:00", tz="UTC")
T1 = pd.Timestamp("2026-01-02 00:00", tz="UTC")
T2 = pd.Timestamp("2026-01-03 00:00", tz="UTC")

FREE = TransactionCostModel(
    fee=FeeModel(maker_rate=0.0, taker_rate=0.0),
    slippage=SlippageModel(base_cost_bps=0.0),
)


def _bar(ts: pd.Timestamp, o: float, h: float, lo: float, c: float, symbol: str = "BTC") -> Bar:
    return Bar(symbol=symbol, ts=ts, open=o, high=h, low=lo, close=c)


def _mkt(side: Side, qty: float, ts: pd.Timestamp = T0, symbol: str = "BTC") -> Order:
    return Order(
        scenario_id="s", symbol=symbol, side=side, order_type=OrderType.MARKET,
        qty=qty, created_at=ts,
    )


def _limit(side: Side, qty: float, limit: float, ts: pd.Timestamp = T0) -> Order:
    return Order(
        scenario_id="s", symbol="BTC", side=side, order_type=OrderType.LIMIT,
        qty=qty, created_at=ts, limit_price=limit,
    )


# --- no look-ahead (ADR-010 #1) ---


def test_order_never_fills_on_its_own_bar() -> None:
    broker = PaperBroker(Portfolio(cash=10_000), cost_model=FREE)
    broker.submit(_mkt(Side.BUY, 1.0, ts=T1))
    # a bar AT the creation time must not fill (>= guard)
    assert broker.process_bar(_bar(T1, 100, 110, 90, 105)) == []
    # the NEXT bar fills, at its open
    filled = broker.process_bar(_bar(T2, 106, 112, 100, 108))
    assert len(filled) == 1
    assert filled[0].fill_price == pytest.approx(106.0)
    assert filled[0].filled_at == T2


def test_market_fills_at_next_open_not_signal_price() -> None:
    broker = PaperBroker(Portfolio(cash=10_000), cost_model=FREE)
    broker.submit(_mkt(Side.BUY, 1.0, ts=T0))
    filled = broker.process_bar(_bar(T1, 120, 125, 118, 124))
    # the decision was made when price was (say) 100; the fill is 120 — reality
    assert filled[0].fill_price == pytest.approx(120.0)


# --- limit semantics ---


def test_buy_limit_fills_at_limit_when_touched() -> None:
    broker = PaperBroker(Portfolio(cash=10_000), cost_model=FREE)
    broker.submit(_limit(Side.BUY, 1.0, limit=95.0))
    filled = broker.process_bar(_bar(T1, 100, 105, 94, 99))  # low touches 94 <= 95
    assert filled[0].fill_price == pytest.approx(95.0)


def test_buy_limit_fills_at_open_if_gapped_below() -> None:
    broker = PaperBroker(Portfolio(cash=10_000), cost_model=FREE)
    broker.submit(_limit(Side.BUY, 1.0, limit=95.0))
    filled = broker.process_bar(_bar(T1, 90, 96, 88, 92))  # opens below the limit
    assert filled[0].fill_price == pytest.approx(90.0)  # better price, honest fill


def test_buy_limit_stays_pending_if_never_reached() -> None:
    broker = PaperBroker(Portfolio(cash=10_000), cost_model=FREE)
    o = broker.submit(_limit(Side.BUY, 1.0, limit=95.0))
    assert broker.process_bar(_bar(T1, 100, 105, 97, 99)) == []
    assert o.status is OrderStatus.PENDING
    assert broker.pending == [o]


def test_sell_limit_symmetric() -> None:
    pf = Portfolio(cash=100.0)
    pf.apply_buy("BTC", 1.0, 100.0, 0.0)
    broker = PaperBroker(pf, cost_model=FREE)
    broker.submit(_limit(Side.SELL, 1.0, limit=110.0))
    filled = broker.process_bar(_bar(T1, 105, 111, 104, 108))  # high touches 111 >= 110
    assert filled[0].fill_price == pytest.approx(110.0)


# --- costs bite (ADR-012/013) ---


def test_fees_and_slippage_are_charged() -> None:
    model = TransactionCostModel(
        fee=FeeModel(maker_rate=0.001, taker_rate=0.001),
        slippage=SlippageModel(base_cost_bps=100.0),  # 1% slippage, visible
    )
    pf = Portfolio(cash=10_000)
    broker = PaperBroker(pf, cost_model=model)
    broker.submit(_mkt(Side.BUY, 1.0))
    filled = broker.process_bar(_bar(T1, 100, 105, 99, 104))
    o = filled[0]
    assert o.fill_price == pytest.approx(101.0)  # 100 * (1 + 1%)
    assert o.fee_paid == pytest.approx(101.0 * 0.001)
    assert pf.cash == pytest.approx(10_000 - 101.0 - 0.101)
    assert pf.fees_paid == pytest.approx(0.101)


# --- long-only enforcement ---


def test_sell_more_than_held_is_rejected_at_submit() -> None:
    broker = PaperBroker(Portfolio(cash=1_000), cost_model=FREE)
    o = broker.submit(_mkt(Side.SELL, 1.0))
    assert o.status is OrderStatus.REJECTED
    assert o.reject_reason is not None and "long-only" in o.reject_reason
    assert broker.pending == []


def test_buy_beyond_cash_is_rejected_at_fill() -> None:
    broker = PaperBroker(Portfolio(cash=50.0), cost_model=FREE)
    o = broker.submit(_mkt(Side.BUY, 1.0))  # 1 BTC a ~100 con 50 di cassa
    filled = broker.process_bar(_bar(T1, 100, 105, 99, 104))
    assert filled == []
    assert o.status is OrderStatus.REJECTED
    assert o.reject_reason is not None and "insufficient cash" in o.reject_reason


# --- portfolio accounting ---


def test_roundtrip_pnl_and_equity() -> None:
    pf = Portfolio(cash=1_000)
    broker = PaperBroker(pf, cost_model=FREE)
    broker.submit(_mkt(Side.BUY, 2.0, ts=T0))
    broker.process_bar(_bar(T1, 100, 110, 95, 105))  # buy 2 @ 100
    assert pf.equity({"BTC": 105.0}) == pytest.approx(1_000 - 200 + 2 * 105)
    assert pf.unrealized_pnl({"BTC": 105.0}) == pytest.approx(10.0)
    broker.submit(_mkt(Side.SELL, 2.0, ts=T1))
    broker.process_bar(_bar(T2, 120, 125, 118, 121))  # sell 2 @ 120
    assert pf.realized_pnl == pytest.approx(40.0)
    assert pf.positions == {}
    assert pf.equity({}) == pytest.approx(1_040.0)


def test_average_cost_basis() -> None:
    pf = Portfolio(cash=10_000)
    pf.apply_buy("BTC", 1.0, 100.0, 0.0)
    pf.apply_buy("BTC", 1.0, 200.0, 0.0)
    assert pf.positions["BTC"].avg_cost == pytest.approx(150.0)
    pnl = pf.apply_sell("BTC", 1.0, 180.0, 0.0)
    assert pnl == pytest.approx(30.0)  # vs avg cost 150, not FIFO


# --- sizing helper ---


def test_qty_for_cash_fraction_leaves_room_for_costs() -> None:
    model = TransactionCostModel(
        fee=FeeModel(maker_rate=0.001, taker_rate=0.001),
        slippage=SlippageModel(base_cost_bps=2.0),
    )
    pf = Portfolio(cash=1_000)
    broker = PaperBroker(pf, cost_model=model)
    qty = broker.qty_for_cash_fraction(1.0, price=100.0)
    broker.submit(_mkt(Side.BUY, qty))
    filled = broker.process_bar(_bar(T1, 100, 101, 99, 100))
    assert len(filled) == 1  # non rimbalza per mancanza di cassa
    assert pf.cash >= 0


# --- scenarios (ADR-011) ---


def test_scenario_create_save_load(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    state = store.create("mid_10k", 10_000.0)
    state.portfolio.apply_buy("BTC", 0.5, 100.0, 1.0)
    state.last_processed = T1
    store.save(state)
    loaded = store.load("mid_10k")
    assert loaded.portfolio.cash == pytest.approx(10_000 - 51.0)
    assert loaded.portfolio.positions["BTC"].qty == pytest.approx(0.5)
    assert loaded.last_processed == T1


def test_scenario_reset_archives_never_deletes(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    store.create("small_1k", 1_000.0)
    store.append_equity("small_1k", T1, equity=1_100.0, cash=500.0)
    fresh = store.reset("small_1k")
    assert fresh.portfolio.cash == pytest.approx(1_000.0)
    assert fresh.portfolio.positions == {}
    # the old run is archived, not deleted (ADR-011)
    archives = list((tmp_path / "paper" / "_archive").iterdir())
    assert len(archives) == 1 and archives[0].name.startswith("small_1k__")
    assert (archives[0] / "equity.parquet").exists()


def test_scenario_fork_clones_state(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    state = store.create("base", 5_000.0)
    state.portfolio.apply_buy("ETH", 2.0, 100.0, 0.0)
    store.save(state)
    forked = store.fork("base", "variant")
    assert forked.portfolio.positions["ETH"].qty == pytest.approx(2.0)
    assert store.registry()["variant"]["forked_from"] == "base"
    with pytest.raises(ValueError, match="already exists"):
        store.fork("base", "variant")


def test_equity_append_is_idempotent(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    store.create("s", 1_000.0)
    store.append_equity("s", T1, equity=1_010.0, cash=10.0)
    store.append_equity("s", T1, equity=1_020.0, cash=20.0)  # rerun same bar
    curve = store.equity_curve("s")
    assert len(curve) == 1
    assert curve.iloc[0] == pytest.approx(1_020.0)  # overwrite, no duplicate


def test_ensure_default_scenarios(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    ids = ensure_default_scenarios(store)
    assert ids == ["large_100k", "mid_10k", "small_1k"]
    # idempotent
    assert ensure_default_scenarios(store) == ids


def test_order_audit_trail_appends(tmp_path) -> None:
    store = ScenarioStore(root=tmp_path / "paper")
    store.create("s", 1_000.0)
    o1 = _mkt(Side.BUY, 1.0)
    store.append_orders("s", [o1])
    store.append_orders("s", [_mkt(Side.SELL, 1.0)])
    df = store.orders("s")
    assert len(df) == 2
    assert set(df["side"]) == {"buy", "sell"}
