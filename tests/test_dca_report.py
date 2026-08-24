"""Offline tests for the accumulation-plan report and its JSON twin. No network."""

from __future__ import annotations

import pandas as pd

from src.features.dca_advisor import advise
from src.features.dca_candidates import screen_candidates
from src.features.dca_report import (
    CAVEATS,
    EVIDENCE,
    dca_report_dict,
    format_report,
    write_markdown,
)
from tests.test_dca_backtest import _panel


def _ranked() -> pd.DataFrame:
    return advise(_panel(), holdings_units={"A": 10.0, "B": 1.0, "C": 1.0})


def _candidates() -> tuple[pd.DataFrame, pd.DataFrame]:
    from tests.test_dca_candidates import AS_OF, _markets

    return screen_candidates(_markets(), held_symbols=["BTC"], min_market_cap=1e9, as_of=AS_OF)


def test_report_names_the_pick_and_every_sleeve_asset() -> None:
    ranked = _ranked()
    text = format_report(ranked)
    assert f"**{ranked.iloc[0]['symbol']}**" in text
    for symbol in ranked["symbol"]:
        assert symbol in text


def test_report_always_carries_the_refutation_next_to_the_pick() -> None:
    # The whole point: the recommendation must never appear without the
    # backtest result that says it earns no return edge.
    text = format_report(_ranked())
    assert "nessun vantaggio" in text
    assert str(EVIDENCE["random_percentile"]) in text
    for caveat in CAVEATS:
        assert caveat in text


def test_report_warns_when_the_position_is_only_estimated() -> None:
    assert "stimati" not in format_report(_ranked(), holdings_estimated=False)
    assert "stimati" in format_report(_ranked(), holdings_estimated=True)


def test_report_lists_candidates_and_their_rejection_counts() -> None:
    shortlist, rejected = _candidates()
    text = format_report(_ranked(), shortlist, rejected)
    assert "Candidate per un accumulo" in text
    assert "XMR" in text
    assert "già in portafoglio" in text


def test_report_handles_an_empty_ranking() -> None:
    text = format_report(pd.DataFrame())
    assert "Nessun dato" in text


def test_payload_mirrors_the_markdown_fields() -> None:
    shortlist, rejected = _candidates()
    ranked = _ranked()
    payload = dca_report_dict(ranked, shortlist, rejected, sleeve_eur=10.0)
    assert payload["pick"] == ranked.iloc[0]["symbol"]
    assert len(payload["items"]) == len(ranked)
    assert len(payload["candidates"]) == len(shortlist)
    assert payload["evidence"]["random_percentile"] == EVIDENCE["random_percentile"]
    assert payload["caveats"] == list(CAVEATS)
    assert payload["rejected_summary"]["already_held"] == 1


def test_payload_reports_missing_weights_as_null_not_zero() -> None:
    payload = dca_report_dict(advise(_panel(), holdings_units=None))
    assert all(item["weight_now"] is None for item in payload["items"])
    assert all(item["gap_pp"] is None for item in payload["items"])


def test_payload_carries_the_estimated_flag_and_its_note() -> None:
    exact = dca_report_dict(_ranked(), holdings_estimated=False)
    estimated = dca_report_dict(_ranked(), holdings_estimated=True)
    assert exact["holdings_note"] is None
    assert estimated["holdings_estimated"] is True
    assert estimated["holdings_note"]


def test_payload_timestamp_is_iso_utc() -> None:
    payload = dca_report_dict(_ranked(), generated_at="2026-01-02 03:04:05")
    assert payload["generated_at"].startswith("2026-01-02T03:04:05")


def test_write_markdown_creates_parents_and_ends_with_a_newline(tmp_path) -> None:
    target = tmp_path / "nested" / "REPORT_DCA.md"
    write_markdown("# titolo", target)
    assert target.read_text(encoding="utf-8") == "# titolo\n"
