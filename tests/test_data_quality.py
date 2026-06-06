"""Offline tests for the data confidence layer. No network."""

from __future__ import annotations

from src.quality.data_quality import (
    LOW,
    STALE,
    VALID,
    crypto_item_confidence,
    equity_item_confidence,
    freshness_score,
    liquidity_score,
)


def test_freshness_score_decay() -> None:
    assert freshness_score(0) == 1.0
    assert freshness_score(2) == 1.0
    assert freshness_score(7) == 0.0
    assert freshness_score(None) == 0.0
    mid = freshness_score(4.5)  # halfway between soft(2) and hard(7)
    assert 0.4 < mid < 0.6


def test_liquidity_tiers() -> None:
    assert liquidity_score(2e9) == 1.0
    assert liquidity_score(5e8) == 0.7
    assert liquidity_score(1e7) == 0.35
    assert liquidity_score(None) == 0.4


def test_crypto_confidence_large_vs_micro() -> None:
    big = crypto_item_confidence(2e9, has_change=True, has_leader=True)
    micro = crypto_item_confidence(1e7, has_change=True, has_leader=True)
    assert big.score > micro.score
    assert big.status == VALID
    assert "liquidità bassa" in micro.reason


def test_equity_confidence_fresh_vs_frozen() -> None:
    fresh = equity_item_confidence(1.0, has_5d=True, has_21d=True)
    frozen = equity_item_confidence(None, has_5d=True, has_21d=True)
    assert fresh.score == 1.0 and fresh.status == VALID
    assert frozen.status == STALE
    assert frozen.score < 0.55


def test_equity_incomplete_momentum_lowers_score() -> None:
    c = equity_item_confidence(1.0, has_5d=True, has_21d=False)
    assert c.score < 1.0
    assert "momentum incompleto" in c.reason


def test_low_status_band() -> None:
    c = crypto_item_confidence(1e7, has_change=False, has_leader=False, snapshot_age_days=6.0)
    assert c.status in {LOW, STALE}
