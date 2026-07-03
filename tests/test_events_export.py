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
    assert asset["universe"] == "crypto"
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


def test_universe_passthrough() -> None:
    payload = build_events_payload(
        [{"symbol": "SEMIS", "name": "Semiconductors", "universe": "equity",
          "moves": [_move(-4.0, "market-wide", False)]}]
    )
    assert payload["assets"][0]["universe"] == "equity"


def test_empty_assets() -> None:
    payload = build_events_payload([])
    assert payload["assets"] == []
    assert "generated_at" in payload


# --- severity + market pulse (regime-robust attribution v2) ---


def test_severity_defaults_to_major_and_passes_through() -> None:
    payload = build_events_payload(
        [{"symbol": "BTC", "name": "Bitcoin", "moves": [_move(-6.5, "market-wide", False)]}]
    )
    assert payload["assets"][0]["moves"][0]["severity"] == "major"

    notable = AbnormalMove(
        date=pd.Timestamp("2026-06-03", tz="UTC"),
        return_pct=-2.1,
        zscore=-1.8,
        market_return_pct=-1.5,
        classification="market-wide",
        severity="notable",
    )
    payload = build_events_payload([{"symbol": "BTC", "name": "Bitcoin", "moves": [notable]}])
    assert payload["assets"][0]["moves"][0]["severity"] == "notable"


def test_market_pulse_in_payload_when_provided() -> None:
    pulse = {"crypto": {"benchmark": "BTC", "return_pct": 1.6, "zscore": 0.9,
                        "max_abs_z_recent": 1.4, "days_since_last_major": 25}}
    payload = build_events_payload([], market_pulse=pulse)
    assert payload["market_pulse"] == pulse
    # and absent when not provided (older consumers unaffected)
    assert "market_pulse" not in build_events_payload([])


def test_days_since_last_major_counts_only_major() -> None:
    from src.features.events_export import days_since_last_major

    major = _move(-6.5, "market-wide", False)  # 2026-06-02, severity major
    notable = AbnormalMove(
        date=pd.Timestamp("2026-06-04", tz="UTC"),
        return_pct=-2.0,
        zscore=-1.7,
        market_return_pct=None,
        classification="unknown",
        severity="notable",
    )
    entries = [{"symbol": "BTC", "name": "Bitcoin", "moves": [major, notable]}]
    as_of = pd.Timestamp("2026-06-05", tz="UTC")
    # the more recent notable move must NOT reset the counter
    assert days_since_last_major(entries, as_of) == 3
    # no major anywhere -> None
    only_notable = [{"symbol": "BTC", "name": "Bitcoin", "moves": [notable]}]
    assert days_since_last_major(only_notable, as_of) is None
    assert days_since_last_major([], as_of) is None
