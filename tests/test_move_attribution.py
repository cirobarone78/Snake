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


# --- regime-robust triggers (dual trigger + severity tiers) ---


def _high_vol_series(n: int = 60, shock_day: int = 50, shock: float = -0.05) -> pd.Series:
    """Deterministic ±3% alternating returns (3% daily vol), one shock day.

    In this regime a -5% day scores |z| ~= 1.7 — *below* the 2.5 threshold —
    which is exactly the self-blinding failure the absolute floor must fix.
    """
    ret = np.array([0.03 if i % 2 == 0 else -0.03 for i in range(n)])
    ret[shock_day] = shock
    idx = pd.date_range("2026-01-01", periods=n, freq="D", tz="UTC")
    price = 100 * np.cumprod(1 + ret)
    return pd.Series(price, index=idx)


def test_z_only_trigger_misses_big_move_in_high_vol_regime() -> None:
    # documents the failure mode: -5% day, 3% vol -> |z| < 2.5 -> not flagged
    close = _high_vol_series(shock=-0.05)
    flagged = detect_abnormal_moves(close, vol_window=20, z_threshold=2.5)
    assert close.index[50] not in flagged.index


def test_return_floor_flags_big_move_in_high_vol_regime() -> None:
    close = _high_vol_series(shock=-0.05)
    flagged = detect_abnormal_moves(
        close, vol_window=20, z_threshold=2.5, return_floor_pct=4.0
    )
    assert close.index[50] in flagged.index
    row = flagged.loc[close.index[50]]
    assert row["severity"] == "major"  # absolute floor -> full-confidence tier
    assert abs(row["zscore"]) < 2.5  # and indeed z alone would not have fired


def test_notable_tier_between_thresholds() -> None:
    # -6.5% on 3% vol -> |z| ~ 2.2: notable (>=1.5) but not major (<2.5)
    close = _high_vol_series(shock=-0.065)
    flagged = detect_abnormal_moves(
        close, vol_window=20, z_threshold=2.5, notable_z=1.5
    )
    assert close.index[50] in flagged.index
    assert flagged.loc[close.index[50], "severity"] == "notable"


def test_notable_z_must_be_below_threshold() -> None:
    close = _high_vol_series()
    try:
        detect_abnormal_moves(close, z_threshold=2.5, notable_z=2.5)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_severity_column_always_present() -> None:
    close = _calm_then_shock(shock_day=50, shock=-0.25)
    flagged = detect_abnormal_moves(close, vol_window=20, z_threshold=2.5)
    assert "severity" in flagged.columns
    assert (flagged["severity"] == "major").all()


# --- world/macro sources on market-wide moves ---


def _world_vs_generic_news(day: str) -> pd.DataFrame:
    idx = pd.DatetimeIndex([day, day], tz="UTC", name="published")
    return pd.DataFrame(
        {
            "source": ["googlenews_world", "cointelegraph"],
            "title": ["Geopolitical shock rattles markets", "Crypto daily roundup"],
            "url": ["w", "g"],
            "sentiment": [-0.5, -0.5],
        },
        index=idx,
    )


def test_world_sources_upweighted_on_market_wide_moves() -> None:
    move_date = pd.Timestamp("2026-02-20", tz="UTC")
    news = _world_vs_generic_news("2026-02-20")
    events = associate_events(
        move_date, -8.0, news, asset_source="googlenews_btc",
        market_sources={"googlenews_world"}, classification="market-wide",
    )
    by_source = {str(e["source"]): float(e["relevance"]) for e in events}
    # same recency and sentiment: the world source must outrank the generic one
    assert by_source["googlenews_world"] > by_source["cointelegraph"]


def test_world_sources_not_upweighted_on_asset_specific_moves() -> None:
    move_date = pd.Timestamp("2026-02-20", tz="UTC")
    news = _world_vs_generic_news("2026-02-20")
    events = associate_events(
        move_date, -8.0, news, asset_source="googlenews_btc",
        market_sources={"googlenews_world"}, classification="asset-specific",
    )
    by_source = {str(e["source"]): float(e["relevance"]) for e in events}
    # asset-specific day: a world headline is just another generic source
    assert by_source["googlenews_world"] == by_source["cointelegraph"]


def test_attribute_moves_carries_severity_and_floor() -> None:
    close = _high_vol_series(shock=-0.05)
    market = _high_vol_series(shock=-0.045)
    moves = attribute_moves(
        close, pd.DataFrame(), market_close=market, vol_window=20,
        return_floor_pct=4.0, notable_z=1.5,
    )
    shock = next(m for m in moves if m.date == close.index[50])
    assert shock.severity == "major"


# --- market pulse ---


def test_market_pulse_shape() -> None:
    from src.features.move_attribution import market_pulse

    close = _calm_then_shock(shock_day=50, shock=-0.25)
    pulse = market_pulse(close, vol_window=20, recent_days=10)
    assert set(pulse) == {"date", "return_pct", "zscore", "max_abs_z_recent", "recent_days"}
    assert pulse["recent_days"] == 10
    # the shock (day 50 of 60) is inside the 10-day window -> big recent max |z|
    assert float(pulse["max_abs_z_recent"]) > 2.5
    assert pulse["date"] == str(close.index[-1].date())
