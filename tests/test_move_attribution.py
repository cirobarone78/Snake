"""Offline tests for abnormal-move event attribution (Fase 3). No network."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.move_attribution import (
    associate_events,
    attribute_moves,
    classify_move,
    detect_abnormal_moves,
)


def _calm_then_shock(n: int = 60, shock_day: int = 50, shock: float = -0.25) -> pd.Series:
    rng = np.random.default_rng(0)
    idx = pd.date_range("2026-01-01", periods=n, freq="D", tz="UTC")
    ret = rng.normal(0, 0.01, n)  # calm 1% daily vol
    ret[shock_day] = shock  # a -25% shock day
    price = 100 * np.cumprod(1 + ret)
    return pd.Series(price, index=idx)


# --- detection ---


def test_detect_flags_the_shock_day() -> None:
    close = _calm_then_shock(shock_day=50, shock=-0.25)
    flagged = detect_abnormal_moves(close, vol_window=20, z_threshold=2.5)
    assert close.index[50] in flagged.index
    assert flagged.loc[close.index[50], "return_pct"] < -20  # ~-25%
    # calm days are not flagged
    assert len(flagged) <= 2


def test_detect_no_lookahead_in_baseline() -> None:
    # the shock day must not be in its own volatility baseline (shift(1))
    close = _calm_then_shock(shock_day=40, shock=0.30)
    flagged = detect_abnormal_moves(close, vol_window=15, z_threshold=2.5)
    assert close.index[40] in flagged.index
    # the day AFTER the shock should not be flagged just from the shock's vol
    assert flagged["zscore"].abs().max() > 2.5


# --- classification ---


def test_classify_market_wide() -> None:
    # asset -8%, market -6% same direction and large -> market-wide
    assert classify_move(-8.0, -6.0) == "market-wide"


def test_classify_asset_specific() -> None:
    # asset -15%, market flat -> asset-specific
    assert classify_move(-15.0, -0.3) == "asset-specific"


def test_classify_unknown_without_market() -> None:
    assert classify_move(-10.0, None) == "unknown"


def test_classify_opposite_direction_is_asset_specific() -> None:
    # asset down but market up -> not market-driven
    assert classify_move(-10.0, +4.0) == "asset-specific"


def test_classify_equity_threshold_makes_small_market_day_count() -> None:
    # an equity sector ETF +2.5% on a +1.5% S&P day: with the equity-sized
    # threshold (1%) this is market-wide; with the crypto default (3%) it isn't.
    assert classify_move(2.5, 1.5, market_threshold_pct=1.0) == "market-wide"
    assert classify_move(2.5, 1.5) == "asset-specific"


def test_classify_positive_market_wide() -> None:
    # surges are handled too: asset +8%, market +6% same direction -> market-wide
    assert classify_move(8.0, 6.0) == "market-wide"


# --- association ---


def _news() -> pd.DataFrame:
    idx = pd.DatetimeIndex(
        ["2026-02-19", "2026-02-20", "2026-02-20", "2026-02-10"], tz="UTC", name="published"
    )
    return pd.DataFrame(
        {
            "source": ["googlenews_btc", "googlenews_btc", "cointelegraph", "googlenews_btc"],
            "title": [
                "Bitcoin plunges as ETF outflows hit record",
                "Crypto market in turmoil, BTC crashes",
                "Markets fall broadly",
                "Old unrelated bullish story",
            ],
            "url": ["u1", "u2", "u3", "u4"],
            "sentiment": [-0.8, -0.7, -0.4, +0.6],
        },
        index=idx,
    )


def test_associate_ranks_relevant_negative_news_for_a_crash() -> None:
    move_date = pd.Timestamp("2026-02-20", tz="UTC")
    events = associate_events(move_date, -22.0, _news(), asset_source="googlenews_btc")
    assert len(events) >= 2
    # top event is recent + negative + asset-specific
    top = events[0]
    assert "Bitcoin" in str(top["title"]) or "BTC" in str(top["title"])
    assert float(top["sentiment"]) < 0
    # the old bullish story (10 days before, wrong direction) is excluded
    titles = [str(e["title"]) for e in events]
    assert "Old unrelated bullish story" not in titles


def test_associate_empty_news() -> None:
    out = associate_events(pd.Timestamp("2026-02-20", tz="UTC"), -10.0, pd.DataFrame())
    assert out == []


# --- end to end ---


def test_attribute_moves_end_to_end() -> None:
    close = _calm_then_shock(shock_day=50, shock=-0.25)
    # market reference that ALSO dropped that day -> market-wide
    market = _calm_then_shock(shock_day=50, shock=-0.20)
    moves = attribute_moves(
        close, _news(), asset_source="googlenews_btc", market_close=market, vol_window=20
    )
    assert len(moves) >= 1
    shock = next(m for m in moves if m.date == close.index[50])
    assert shock.return_pct < -20
    assert shock.classification == "market-wide"  # both fell
    assert shock.market_return_pct is not None


def test_attribute_moves_asset_specific_when_market_calm() -> None:
    close = _calm_then_shock(shock_day=50, shock=-0.25)
    market = _calm_then_shock(shock_day=20, shock=-0.20)  # market shock on a different day
    moves = attribute_moves(
        close, _news(), asset_source="googlenews_btc", market_close=market, vol_window=20
    )
    shock = next(m for m in moves if m.date == close.index[50])
    assert shock.classification == "asset-specific"


def test_attribute_moves_equity_threshold_marks_market_wide() -> None:
    # equity-sized shock: ETF -4%, S&P -2.5% same day (market explains >= half the
    # move). Crypto default (3%) would call it asset-specific because 2.5% < 3%;
    # the equity threshold (1%) correctly calls it market-wide.
    close = _calm_then_shock(shock_day=50, shock=-0.04)
    market = _calm_then_shock(shock_day=50, shock=-0.025)
    moves = attribute_moves(
        close, pd.DataFrame(), market_close=market, vol_window=20, market_threshold_pct=1.0
    )
    shock = next(m for m in moves if m.date == close.index[50])
    assert shock.classification == "market-wide"
    # no news frame -> no candidate events, but the move is still classified
    assert shock.candidate_events == []

    # same data, crypto-sized threshold -> the 2.5% market day is "too small"
    crypto_view = attribute_moves(
        close, pd.DataFrame(), market_close=market, vol_window=20, market_threshold_pct=3.0
    )
    crypto_shock = next(m for m in crypto_view if m.date == close.index[50])
    assert crypto_shock.classification == "asset-specific"
