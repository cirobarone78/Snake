"""Offline tests for cross-source price validation. No network."""

from __future__ import annotations

from src.quality.cross_source import MATCH, MISMATCH, SINGLE, cross_source_check


def test_match_within_tolerance() -> None:
    r = cross_source_check(60000.0, 60500.0)  # ~0.8%
    assert r.status == MATCH
    assert r.divergence_pct is not None and r.divergence_pct < 3.0


def test_mismatch_catches_frozen_feed() -> None:
    # the real POL case: Yahoo frozen 0.22 vs CoinGecko 0.084
    r = cross_source_check(0.22, 0.084)
    assert r.status == MISMATCH
    assert r.divergence_pct is not None and r.divergence_pct > 50
    assert "divergenza" in r.reason


def test_single_source_when_missing() -> None:
    assert cross_source_check(100.0, None).status == SINGLE
    assert cross_source_check(None, 100.0).status == SINGLE
    assert cross_source_check(100.0, 0.0).status == SINGLE


def test_boundary_at_tolerance() -> None:
    # exactly at the 3% threshold counts as a match
    r = cross_source_check(100.0, 103.045)  # ~3.0%
    assert r.status == MATCH
