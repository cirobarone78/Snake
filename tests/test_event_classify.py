"""Offline tests for headline event-type classification."""

from __future__ import annotations

import pytest

from src.features.event_classify import classify_event


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Bitcoin, XRP Fall As Israel-Hezbollah War Threatens", "geopolitical"),
        ("SEC charges exchange over unregistered securities", "regulation"),
        ("US CPI comes in hotter than expected", "inflation"),
        ("Fed signals a rate cut at next FOMC", "fed"),
        ("Major DeFi protocol hacked, $50M drained", "hack"),
        ("Spot bitcoin ETFs extend outflow streak", "etf_flow"),
        ("Coinbase lists new token", "listing"),
        ("Ethereum mainnet upgrade goes live", "upgrade"),
        ("Company announces partnership with bank", "partnership"),
        ("Just another quiet day in markets", "other"),
    ],
)
def test_classify(title: str, expected: str) -> None:
    assert classify_event(title) == expected


def test_word_boundary_avoids_false_positive() -> None:
    # 'war' must not match inside 'forward'
    assert classify_event("Looking forward to the launch") != "geopolitical"


def test_empty_is_other() -> None:
    assert classify_event("") == "other"
    assert classify_event(None) == "other"
