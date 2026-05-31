"""Offline tests for the screener report formatter (Fase 6). No network."""

from __future__ import annotations

import pandas as pd

from src.features.screener_report import format_report, format_report_md


def _categories() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "category_id": ["ai", "rwa", "gaming", "defi", "pump"],
            "name": ["AI", "RWA", "Gaming", "DeFi", "MicroPump"],
            "market_cap": [50e9, 20e9, 8e9, 30e9, 5e6],
            "volume_24h": [10e9, 1e9, 0.4e9, 3e9, 4e6],
            "change_24h_pct": [8.0, 3.0, -5.0, 1.0, 420.0],
            "top_coins": [
                "near,bittensor,fetch-ai",
                "ondo,chainlink",
                "imx,gala",
                "aave,uni",
                "scam",
            ],
        }
    )


def test_report_contains_sections() -> None:
    report = format_report(_categories())
    assert "NARRATIVE IN FORZA ORA" in report
    assert "IN CALO / RISCHIO ORA" in report
    # honest framing line present
    assert "non una previsione" in report.lower() or "non e' una previsione" in report.lower()


def test_report_shows_strong_and_excludes_pump() -> None:
    report = format_report(_categories())
    assert "AI" in report
    # micro-cap pump must not surface as a strong narrative
    assert "MicroPump" not in report


def test_report_shows_losers() -> None:
    report = format_report(_categories())
    # Gaming is the worst real mover (-5%) -> should appear in the risk section
    assert "Gaming" in report


def test_report_empty_snapshot() -> None:
    report = format_report(pd.DataFrame())
    assert "Nessun dato" in report


def test_report_lists_leading_coins() -> None:
    report = format_report(_categories())
    # leading coins of a strong narrative are shown
    assert "near" in report or "bittensor" in report


# --- Markdown variant ---


def test_report_md_has_markdown_tables_and_sections() -> None:
    md = format_report_md(_categories(), snapshot_at="2026-05-31 07:00")
    assert md.startswith("#")  # markdown heading
    assert "| # | Narrativa |" in md  # strong table header
    assert "Narrative in forza" in md
    assert "In calo / rischio" in md
    # freshness stamp surfaced
    assert "2026-05-31 07:00" in md
    # honest framing
    assert "non è una previsione" in md.lower()


def test_report_md_excludes_pump_and_shows_strong() -> None:
    md = format_report_md(_categories())
    assert "AI" in md
    assert "MicroPump" not in md


def test_report_md_empty() -> None:
    md = format_report_md(pd.DataFrame())
    assert md.startswith("#")
    assert "Nessun dato" in md
