"""Offline tests for the fundamental profile. No network."""

from __future__ import annotations

import pandas as pd

from src.assets.token_economics import Emission, ValueAccrual, get_economics
from src.features.fundamentals import (
    accrual_score,
    dev_status,
    dilution_score,
    profile_frame,
    profile_token,
    track_record_score,
)

AS_OF = pd.Timestamp("2026-08-24", tz="UTC")


def _row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "symbol": "ETH", "name": "Ethereum", "coingecko_id": "ethereum",
        "market_cap": 3e11, "fully_diluted_valuation": 3e11,
        "circulating_supply": 120e6, "total_supply": 120e6,
        "commits_4w": 41, "pr_contributors": 906, "stars": 44422,
        "genesis_date": "2015-07-30", "categories": "Layer 1 (L1)", "as_of": AS_OF,
    }
    base.update(overrides)
    return base


def test_dev_status_separates_no_data_from_no_activity() -> None:
    # No repo mapped at all: unknown, not dead.
    assert dev_status(0, 0, 0) == "no_repo_data"
    # Established codebase gone quiet: could be a calm month or a stale mapping.
    assert dev_status(0, 320, 8309) == "quiet_or_stale"
    # Mapped repo, few contributors, nothing happening: genuinely thin.
    assert dev_status(0, 3, 40) == "thin"
    assert dev_status(41, 906, 44422) == "active"
    assert dev_status(8, 100, 500) == "moderate"
    assert dev_status(2, 100, 500) == "low"


def test_quiet_repo_scores_unknown_rather_than_zero() -> None:
    # Monero reports zero commits and is plainly alive; scoring that as zero
    # would be the same class of error as ranking Dogecoin second.
    quiet = profile_token(_row(symbol="XMR", coingecko_id="monero", commits_4w=0,
                               pr_contributors=320, stars=8309))
    assert quiet["dev_status"] == "quiet_or_stale"
    assert quiet["development_score"] is None
    assert quiet["confidence"] < 1.0


def test_dilution_score_falls_as_supply_overhang_grows() -> None:
    assert dilution_score(1.0, Emission.CAPPED) == 1.0
    assert dilution_score(2.0, Emission.CAPPED) == 0.5
    assert dilution_score(4.0, Emission.CAPPED) == 0.25
    assert dilution_score(None, Emission.CAPPED) is None


def test_perpetual_issuance_caps_the_dilution_score() -> None:
    # Dogecoin's float is "100% of total" and it still mints ~10bn a year, so the
    # ratio alone would score it perfectly.
    assert dilution_score(1.0, Emission.CAPPED) == 1.0
    assert dilution_score(1.0, Emission.HIGH_INFLATION) <= 0.35
    assert dilution_score(1.0, Emission.UNLOCK_OVERHANG) <= 0.50


def test_monetary_thesis_is_exempt_from_the_accrual_axis() -> None:
    # Not scored badly on value capture — not scored on it at all.
    assert accrual_score(ValueAccrual.MONETARY) is None
    assert accrual_score(ValueAccrual.UNKNOWN) is None
    assert accrual_score(ValueAccrual.NONE) == 0.0
    assert accrual_score(ValueAccrual.FEE_BURN) == 1.0


def test_bitcoin_is_not_penalised_for_capturing_no_fees() -> None:
    btc = profile_token(_row(symbol="BTC", coingecko_id="bitcoin",
                             genesis_date="2009-01-03", commits_4w=108,
                             pr_contributors=846, stars=73168))
    assert btc["verdict"] == "monetary_thesis"
    assert btc["accrual_score"] is None
    assert btc["score"] == 1.0  # scored on the axes that apply to it
    assert btc["confidence"] < 1.0  # and honest that one axis was skipped


def test_track_record_score_needs_an_age() -> None:
    assert track_record_score(None) is None
    assert track_record_score(0.5) == 0.2
    assert track_record_score(3.0) == 0.6
    assert track_record_score(9.0) == 1.0


def test_genesis_date_beats_the_all_time_low_fallback() -> None:
    from_genesis = profile_token(_row(min_age_years=1.0))
    assert from_genesis["age_source"] == "genesis"
    assert from_genesis["age_years"] > 10

    no_genesis = profile_token(_row(genesis_date=None, min_age_years=6.3))
    assert no_genesis["age_source"] == "atl_lower_bound"
    assert no_genesis["age_years"] == 6.3

    neither = profile_token(_row(genesis_date=None, min_age_years=None))
    assert neither["age_source"] is None
    assert neither["track_record_score"] is None


def test_unresearched_token_is_unknown_not_condemned() -> None:
    unknown = profile_token(_row(symbol="ZZZ", coingecko_id="nothing-here"))
    assert unknown["verdict"] == "unresearched"
    assert unknown["accrual_score"] is None
    assert unknown["what_it_does"] is None
    # It must not look like a token that failed the test.
    assert unknown["confidence"] < 1.0


def test_no_value_capture_verdict_for_a_token_with_no_mechanism() -> None:
    doge = profile_token(_row(symbol="DOGE", coingecko_id="dogecoin",
                              genesis_date="2013-12-08", commits_4w=0,
                              pr_contributors=161, stars=14334))
    assert doge["verdict"] == "no_value_capture"
    assert doge["accrual_score"] == 0.0
    assert doge["emission"] == str(Emission.HIGH_INFLATION)


def test_governance_only_is_its_own_verdict() -> None:
    uni = profile_token(_row(symbol="UNI", coingecko_id="uniswap",
                             genesis_date=None, min_age_years=5.9))
    assert uni["verdict"] == "governance_only"
    assert uni["accrual_score"] == 0.15


def test_confidence_reports_how_much_was_actually_known() -> None:
    complete = profile_token(_row(symbol="LINK", coingecko_id="chainlink"))
    assert complete["confidence"] == 1.0
    partial = profile_token(_row(symbol="LINK", coingecko_id="chainlink",
                                 genesis_date=None, min_age_years=None,
                                 commits_4w=0, pr_contributors=0, stars=0))
    assert partial["confidence"] < complete["confidence"]


def test_profile_frame_drops_rows_that_barely_know_anything() -> None:
    rows = pd.DataFrame([
        _row(),
        # Monetary thesis + no repo + no age: one axis known out of four.
        _row(symbol="BCH", coingecko_id="bitcoin-cash", genesis_date=None,
             min_age_years=None, commits_4w=0, pr_contributors=0, stars=0),
    ])
    kept = profile_frame(rows)
    assert "BCH" not in set(kept["symbol"])
    everything = profile_frame(rows, min_confidence=0.0)
    assert "BCH" in set(everything["symbol"])


def test_profile_frame_ranks_a_capturing_token_above_a_hollow_one() -> None:
    rows = pd.DataFrame([
        _row(symbol="DOGE", coingecko_id="dogecoin", genesis_date="2013-12-08",
             commits_4w=0, pr_contributors=161, stars=14334),
        _row(),
    ])
    ranked = profile_frame(rows, min_confidence=0.0)
    assert list(ranked["symbol"]) == ["ETH", "DOGE"]


def test_profile_frame_on_empty_input_returns_empty() -> None:
    assert profile_frame(pd.DataFrame()).empty


def test_registry_lookup_by_symbol_and_id_and_the_unknown_default() -> None:
    assert get_economics(symbol="eth") is not None
    assert get_economics(coingecko_id="ethereum") is not None
    assert get_economics(symbol="NOPE") is None


def test_curated_entries_carry_a_source_and_a_check_date() -> None:
    from src.assets.token_economics import TOKEN_ECONOMICS

    for entry in TOKEN_ECONOMICS:
        assert entry.what_it_does, entry.symbol
        assert entry.source.startswith("http"), entry.symbol
        assert entry.verified_on, entry.symbol
        # Curated prose is rendered into both Markdown and HTML, so it must not
        # carry format markers of its own (they showed up raw on the dashboard).
        assert "**" not in entry.accrual_note, entry.symbol
        assert "**" not in entry.what_it_does, entry.symbol
