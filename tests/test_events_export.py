"""Offline tests for the dashboard events export. No network."""

from __future__ import annotations

import pandas as pd

from src.features.events_export import DISCLAIMER, build_events_payload
from src.features.move_attribution import AbnormalMove


def _move(ret: float, classification: str, with_event: bool) -> AbnormalMove:
    events = (
        [{"source": "googlenews_btc", "title": "Big news", "url": "u", "sentiment": -0.7, "relevance": 0.9}]
        if with_event
        else []
    )
    return AbnormalMove(
        date=pd.Timestamp("2026-06-02", tz="UTC"),
        return_pct=ret,
        zscore=-3.0,
        market_return_pct=-6.0,
        classification=classification,
        candidate_events=events,
    )


def test_payload_shape_and_disclaimer() -> None:
    payload = build_events_payload(
        [{"symbol": "BTC", "name": "Bitcoin", "moves": [_move(-6.5, "market-wide", True)]}],
        generated_at="2026-06-05T00:00:00Z",
    )
    assert payload["title"] == "Eventi e movimenti"
    assert payload["disclaimer"] == DISCLAIMER
    asset = payload["assets"][0]
    assert asset["symbol"] == "BTC"
    move = asset["moves"][0]
    assert move["date"] == "2026-06-02"
    assert move["return_pct"] == -6.5
    assert move["classification"] == "market-wide"
    assert move["events"][0]["title"] == "Big news"
    assert move["events"][0]["sentiment"] == -0.7
    assert move["events"][0]["event_type"] == "other"


def test_move_without_news_has_empty_events() -> None:
    payload = build_events_payload(
        [{"symbol": "SOL", "name": "Solana", "moves": [_move(-9.0, "asset-specific", False)]}]
    )
    assert payload["assets"][0]["moves"][0]["events"] == []


def test_empty_assets() -> None:
    payload = build_events_payload([])
    assert payload["assets"] == []
    assert "generated_at" in payload
