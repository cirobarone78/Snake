"""Offline tests for the equity sector rotation screener (Fase 8). No network."""

from __future__ import annotations

import pandas as pd

from src.features.sector_screener import build_sector_frame, screen_sectors


def _close(trend: float, n: int = 30, start: float = 100.0) -> pd.Series:
    # deterministic ramp: trend% total over n days
    idx = pd.date_range("2026-01-01", periods=n, freq="D", tz="UTC")
    factor = (1 + trend / 100.0) ** (1 / (n - 1))
    return pd.Series([start * factor**i for i in range(n)], index=idx)


def test_build_frame_computes_horizons() -> None:
    closes = {"SEMIS": _close(20.0), "UTILITIES": _close(-5.0)}
    frame = build_sector_frame(closes, names={"SEMIS": "Semiconductors"})
    assert set(frame.columns) == {"symbol", "name", "ret_5d_pct", "ret_21d_pct"}
    semis = frame[frame["symbol"] == "SEMIS"].iloc[0]
    assert semis["name"] == "Semiconductors"
    # rising series -> positive returns; falling -> negative
    assert semis["ret_21d_pct"] > 0
    assert frame[frame["symbol"] == "UTILITIES"].iloc[0]["ret_21d_pct"] < 0


def test_build_frame_skips_short_history() -> None:
    closes = {"OK": _close(10.0, n=30), "SHORT": _close(10.0, n=10)}
    frame = build_sector_frame(closes)
    assert "OK" in frame["symbol"].tolist()
    assert "SHORT" not in frame["symbol"].tolist()  # <22 bars dropped


def test_screen_ranks_strongest_first() -> None:
    closes = {
        "SEMIS": _close(25.0),
        "ENERGY": _close(8.0),
        "UTILITIES": _close(-6.0),
    }
    out = screen_sectors(build_sector_frame(closes), top_n=10)
    assert out.iloc[0]["symbol"] == "SEMIS"
    assert out.index[0] == 1
    assert "score" in out.columns and "signal" in out.columns
    # strongest is hot/warm, weakest is weak/neutral
    assert out.iloc[0]["signal"] in {"hot", "warm"}
    assert out[out["symbol"] == "UTILITIES"].iloc[0]["signal"] in {"weak", "neutral"}


def test_screen_empty() -> None:
    out = screen_sectors(build_sector_frame({}), top_n=5)
    assert out.empty
    assert "score" in out.columns


def test_screen_top_n_caps() -> None:
    closes = {f"S{i}": _close(float(i)) for i in range(1, 8)}
    out = screen_sectors(build_sector_frame(closes), top_n=3)
    assert len(out) == 3
