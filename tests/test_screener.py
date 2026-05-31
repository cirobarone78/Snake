"""Offline tests for the category rotation screener (Fase 6). No network."""

from __future__ import annotations

import pandas as pd

from src.features.screener import screen_categories, screen_movers


def _categories() -> pd.DataFrame:
    # mix of real-size categories and one micro-cap pump
    return pd.DataFrame(
        {
            "category_id": ["ai", "rwa", "gaming", "defi", "pump"],
            "name": ["AI", "RWA", "Gaming", "DeFi", "MicroPump"],
            "market_cap": [50e9, 20e9, 8e9, 30e9, 5e6],
            "volume_24h": [10e9, 1e9, 0.4e9, 3e9, 4e6],
            "change_24h_pct": [8.0, 3.0, -2.0, 1.0, 420.0],
            "top_coins": ["near,tao,fet", "ondo,link", "imx,gala", "aave,uni", "scam"],
        }
    )


def test_screener_excludes_microcap_pump() -> None:
    out = screen_categories(_categories(), min_market_cap=1e8, top_n=10)
    # the $5M +420% pump must NOT appear (filtered as noise)
    assert "MicroPump" not in out["name"].tolist()
    assert len(out) == 4


def test_screener_ranks_strong_first() -> None:
    out = screen_categories(_categories(), min_market_cap=1e8, top_n=10)
    # AI: highest move (8%) AND highest turnover (10e9/50e9=0.2) -> should rank #1
    assert out.iloc[0]["name"] == "AI"
    assert out.index[0] == 1
    assert "score" in out.columns and "signal" in out.columns


def test_screener_signal_labels() -> None:
    out = screen_categories(_categories(), min_market_cap=1e8, top_n=10)
    # the top category should be labelled hot or warm, the worst neutral
    assert out.iloc[0]["signal"] in {"hot", "warm"}
    assert out.iloc[-1]["signal"] == "neutral"


def test_screener_top_n_caps_output() -> None:
    out = screen_categories(_categories(), min_market_cap=1e8, top_n=2)
    assert len(out) == 2


def test_screener_empty_input() -> None:
    out = screen_categories(pd.DataFrame(), top_n=5)
    assert out.empty
    assert "score" in out.columns


def test_screener_all_filtered_out() -> None:
    # everything below floor -> empty (not a crash)
    out = screen_categories(_categories(), min_market_cap=1e12, top_n=5)
    assert out.empty


def test_movers_gainers_and_losers() -> None:
    res = screen_movers(_categories(), min_market_cap=1e8, n=2)
    # gainers led by AI (+8), losers led by Gaming (-2); pump excluded
    assert res["gainers"].iloc[0]["name"] == "AI"
    assert res["losers"].iloc[0]["name"] == "Gaming"
    assert "MicroPump" not in res["gainers"]["name"].tolist()


def test_zscore_handles_constant_column() -> None:
    # all categories same move/turnover -> z-scores 0, no NaN/crash, still ranks
    df = pd.DataFrame(
        {
            "category_id": ["a", "b"],
            "name": ["A", "B"],
            "market_cap": [1e9, 1e9],
            "volume_24h": [1e8, 1e8],
            "change_24h_pct": [5.0, 5.0],
            "top_coins": ["x", "y"],
        }
    )
    out = screen_categories(df, min_market_cap=1e8, top_n=5)
    assert len(out) == 2
    assert out["score"].notna().all()
