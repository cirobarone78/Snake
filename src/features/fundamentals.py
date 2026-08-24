"""Fundamental profile of a token: what it does, who captures the value, what dilutes it.

The candidate screen in ``dca_candidates`` ranks on size, liquidity and age. Those
are real properties, but they are properties of the *ticker*, not of the thing
behind it — which is why a screen built on them surfaces a meme coin with a large
market cap and eleven years of history. This module adds the axes that describe
the project:

1. **Value accrual** — does anything the network does reach the token holder?
   Curated in ``src/assets/token_economics.py``, because no free API answers it.
2. **Dilution** — fully-diluted valuation over market cap, i.e. how much supply
   is still to come, corrected by the emission schedule. A token can look
   fully-circulating and still print forever (Dogecoin: ~10bn new coins a year).
3. **Development** — is anyone still building it.
4. **Track record** — age from the genesis date, when the source has one.

Three design rules, all of them consequences of getting this wrong once:

- **Unknown is not zero.** Every axis can be unknown, unknown axes are excluded
  from the score rather than imputed, and the row carries a ``confidence`` equal
  to the weight of what was actually known. A project this module has not
  researched must not look like a project that failed the test.
- **The monetary thesis is exempt from the accrual axis, not penalised by it.**
  Bitcoin captures no protocol revenue and is the most successful asset in the
  category. A scorer that ranked it last on "value capture" would be broken in a
  new direction rather than fixed.
- **Zero recent commits is a question, not a verdict.** The upstream developer
  data is derived from whichever repository the data provider happened to map,
  and it goes stale: Monero and Aave both report zero commits in four weeks and
  are both plainly alive. So a silent repo with a long contributor history is
  reported as *quiet or stale* and scored as **unknown**, never as dead.

None of this is backtested, and it is not backtestable with the data at hand:
fee/valuation history for protocols is a few years long and riddled with
survivors. This module describes projects; it does not predict returns, and
nothing here should be read as evidence that these axes beat a coin flip.

Pure functions over pandas; unit-testable offline, no network.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pandas as pd

from src.assets.token_economics import Emission, TokenEconomics, ValueAccrual, get_economics

# Axis weights. Accrual dominates because it is the question the other three
# cannot answer; they modify how much the answer is worth.
WEIGHT_ACCRUAL: float = 0.40
WEIGHT_DILUTION: float = 0.25
WEIGHT_DEVELOPMENT: float = 0.20
WEIGHT_TRACK_RECORD: float = 0.15

# Commits in the provider's trailing 4-week window.
_ACTIVE_COMMITS: int = 20
_MODERATE_COMMITS: int = 5

# A repo with at least this many historical PR contributors is an established
# codebase, so a silent month reads as stale data rather than abandonment.
_ESTABLISHED_CONTRIBUTORS: int = 50

# Ceilings applied to the dilution score by emission schedule: supply that keeps
# arriving is dilution even when today's float is already 100% of "total".
_EMISSION_CEILING: dict[Emission, float] = {
    Emission.HIGH_INFLATION: 0.35,
    Emission.UNLOCK_OVERHANG: 0.50,
}

# How each accrual mechanism scores on "is there a link between network activity
# and the holder". Deliberately NOT a league table of which mechanism is best.
# MONETARY is absent on purpose — see the module docstring.
_ACCRUAL_SCORE: dict[ValueAccrual, float] = {
    ValueAccrual.FEE_BURN: 1.0,
    ValueAccrual.STAKING_YIELD: 1.0,
    ValueAccrual.BUYBACK: 1.0,
    ValueAccrual.WORK_TOKEN: 1.0,
    ValueAccrual.GAS_ONLY: 0.5,
    ValueAccrual.GOVERNANCE_ONLY: 0.15,
    ValueAccrual.NONE: 0.0,
}

_OUT_COLS = [
    "symbol", "name", "coingecko_id", "what_it_does", "accrual", "accrual_note",
    "emission", "fdv_ratio", "circulating_pct", "commits_4w", "pr_contributors",
    "dev_status", "age_years", "age_source", "categories", "accrual_score", "dilution_score",
    "development_score", "track_record_score", "score", "confidence", "verdict",
]


def _num(value: object) -> float | None:
    """Plain float, or ``None`` for missing/NaN (never invent a value)."""
    if value is None:
        return None
    try:
        f = float(cast("float", value))
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(f) else f


def dev_status(commits_4w: float | None, pr_contributors: float | None, stars: float | None) -> str:
    """Label the development signal, keeping "we don't know" distinct from "nobody".

    ``no_repo_data`` — the provider mapped no repository at all (zero stars *and*
    zero contributors), so there is nothing to read.
    ``quiet_or_stale`` — an established codebase reporting no recent commits.
    Could be a calm month on a mature protocol, could be a stale mapping; both
    make the signal unusable, so it scores as unknown either way.
    """
    contributors = pr_contributors or 0.0
    if (stars or 0.0) <= 0 and contributors <= 0:
        return "no_repo_data"
    if commits_4w is None:
        return "no_repo_data"
    if commits_4w >= _ACTIVE_COMMITS:
        return "active"
    if commits_4w >= _MODERATE_COMMITS:
        return "moderate"
    if commits_4w > 0:
        return "low"
    if contributors >= _ESTABLISHED_CONTRIBUTORS:
        return "quiet_or_stale"
    return "thin"


_DEV_SCORE: dict[str, float | None] = {
    "active": 1.0,
    "moderate": 0.6,
    "low": 0.3,
    "thin": 0.1,
    "quiet_or_stale": None,  # unknown, not zero
    "no_repo_data": None,
}


def dilution_score(fdv_ratio: float | None, emission: Emission) -> float | None:
    """Score supply overhang in ``[0, 1]``; ``None`` when the ratio is unknown.

    The base is ``1 / fdv_ratio`` — a token whose fully-diluted valuation is
    twice its market cap has half its supply still to arrive, and scores 0.5. The
    emission schedule then caps it, because the ratio is blind to perpetual
    issuance: Dogecoin's float is already "100% of total" and it still mints
    about ten billion new coins every year, forever.
    """
    if fdv_ratio is None or fdv_ratio <= 0:
        return None
    base = min(1.0, 1.0 / fdv_ratio)
    ceiling = _EMISSION_CEILING.get(emission)
    return round(min(base, ceiling) if ceiling is not None else base, 4)


def track_record_score(age_years: float | None) -> float | None:
    """Score a demonstrable track record; ``None`` when the age is unknown."""
    if age_years is None:
        return None
    if age_years >= 5.0:
        return 1.0
    if age_years >= 2.0:
        return 0.6
    return 0.2


def accrual_score(accrual: ValueAccrual) -> float | None:
    """Score value capture; ``None`` for unknown **and for the monetary thesis**.

    Monetary assets are not scored on this axis rather than scored badly on it:
    "captures no protocol fees" is the thesis, not a defect.
    """
    return _ACCRUAL_SCORE.get(accrual)


def _verdict(accrual: ValueAccrual, dev: str) -> str:
    """Coarse label; the report renders these in Italian."""
    if accrual is ValueAccrual.UNKNOWN:
        return "unresearched"
    if accrual is ValueAccrual.NONE:
        return "no_value_capture"
    if accrual is ValueAccrual.GOVERNANCE_ONLY:
        return "governance_only"
    if accrual is ValueAccrual.MONETARY:
        return "monetary_thesis"
    if dev == "thin":
        return "capture_but_thin_dev"
    return "capture_present"


def _weighted(pairs: list[tuple[float | None, float]]) -> tuple[float | None, float]:
    """Weighted mean over the known axes, plus the weight that was known.

    Renormalising over known weights is what keeps an unresearched token from
    scoring like a failed one; ``confidence`` reports how much of the picture the
    number is actually based on.
    """
    known = [(v, w) for v, w in pairs if v is not None]
    total_weight = sum(w for _, w in known)
    if total_weight <= 0:
        return None, 0.0
    value = sum(v * w for v, w in known) / total_weight
    return round(value, 4), round(total_weight, 4)


def profile_token(row: dict[str, Any]) -> dict[str, Any]:
    """Fundamental profile for one coin-detail row.

    ``row`` carries the provider fields (``symbol``, ``name``, ``coingecko_id``,
    ``market_cap``, ``fully_diluted_valuation``, ``circulating_supply``,
    ``total_supply``, ``commits_4w``, ``pr_contributors``, ``stars``,
    ``genesis_date``, ``categories``); the curated half is looked up here.
    """
    symbol = str(row.get("symbol") or "").upper()
    coingecko_id = str(row.get("coingecko_id") or "")
    econ: TokenEconomics | None = get_economics(symbol=symbol, coingecko_id=coingecko_id)
    accrual = econ.accrual if econ else ValueAccrual.UNKNOWN
    emission = econ.emission if econ else Emission.UNKNOWN

    mcap = _num(row.get("market_cap"))
    fdv = _num(row.get("fully_diluted_valuation"))
    fdv_ratio = round(fdv / mcap, 4) if (fdv and mcap and mcap > 0) else None
    circ = _num(row.get("circulating_supply"))
    total = _num(row.get("total_supply"))
    circulating_pct = round(circ / total * 100.0, 2) if (circ and total and total > 0) else None

    commits = _num(row.get("commits_4w"))
    contributors = _num(row.get("pr_contributors"))
    status = dev_status(commits, contributors, _num(row.get("stars")))

    # Genesis is the real birthday; the all-time-low date is only a lower bound
    # (a 2016 coin that printed a new low last year looks two years old). Prefer
    # genesis, fall back, and record which one the number came from.
    age = _age_from_genesis(row.get("genesis_date"), row.get("as_of"))
    age_source = "genesis" if age is not None else None
    if age is None:
        age = _num(row.get("min_age_years"))
        age_source = "atl_lower_bound" if age is not None else None

    a_score = accrual_score(accrual)
    d_score = dilution_score(fdv_ratio, emission)
    dev_score = _DEV_SCORE.get(status)
    t_score = track_record_score(age)
    score, confidence = _weighted(
        [
            (a_score, WEIGHT_ACCRUAL),
            (d_score, WEIGHT_DILUTION),
            (dev_score, WEIGHT_DEVELOPMENT),
            (t_score, WEIGHT_TRACK_RECORD),
        ]
    )

    categories = row.get("categories")
    return {
        "symbol": symbol,
        "name": str(row.get("name") or ""),
        "coingecko_id": coingecko_id,
        "what_it_does": econ.what_it_does if econ else None,
        "accrual": str(accrual),
        "accrual_note": econ.accrual_note if econ else None,
        "emission": str(emission),
        "fdv_ratio": fdv_ratio,
        "circulating_pct": circulating_pct,
        "commits_4w": None if commits is None else int(commits),
        "pr_contributors": None if contributors is None else int(contributors),
        "dev_status": status,
        "age_years": None if age is None else round(age, 2),
        "age_source": age_source,
        "categories": categories if isinstance(categories, str) else None,
        "accrual_score": a_score,
        "dilution_score": d_score,
        "development_score": dev_score,
        "track_record_score": t_score,
        "score": score,
        "confidence": confidence,
        "verdict": _verdict(accrual, status),
    }


def _age_from_genesis(genesis: object, as_of: object) -> float | None:
    """Years since the genesis date, or ``None`` when the source has none."""
    if not isinstance(genesis, str) or not genesis:
        return None
    try:
        start = cast("pd.Timestamp", pd.Timestamp(genesis))
    except (ValueError, TypeError):
        return None
    now = cast(
        "pd.Timestamp",
        pd.Timestamp(cast("Any", as_of)) if as_of is not None else pd.Timestamp.now(tz="UTC"),
    )
    if start.tzinfo is None:
        start = cast("pd.Timestamp", start.tz_localize("UTC"))
    if now.tzinfo is None:
        now = cast("pd.Timestamp", now.tz_localize("UTC"))
    return max(0.0, float((now - start).days) / 365.25)


# A score standing on one axis out of four is not a score. Bitcoin Cash scored a
# perfect 1.0 on dilution alone and sorted fifth overall in an early run, ahead of
# Solana — the number was arithmetically right and completely meaningless. Rows
# below this much known weight are dropped from a ranked shortlist by default.
DEFAULT_MIN_CONFIDENCE: float = 0.5


def profile_frame(
    details: pd.DataFrame, min_confidence: float = DEFAULT_MIN_CONFIDENCE
) -> pd.DataFrame:
    """Fundamental profiles for a frame of coin details, best score first.

    ``min_confidence`` drops rows whose score rests on too little known data.
    Pass ``0.0`` to keep everything — appropriate when the caller wants the full
    picture including the unresearched, as the per-asset dossier does, and wrong
    when the output is a ranked shortlist.

    **The score is not a quality ranking.** Every token with any accrual
    mechanism scores 1.0 on that axis, because without protocol revenue data
    there is no way to tell a large fee burn from a token one. Use it to order
    within a verdict group, never as a verdict itself.
    """
    if details.empty:
        return pd.DataFrame(columns=_OUT_COLS)
    rows = [profile_token(cast("dict[str, Any]", r)) for r in details.to_dict("records")]
    out = pd.DataFrame(rows, columns=_OUT_COLS)
    if min_confidence > 0:
        out = cast("pd.DataFrame", out.loc[out["confidence"] >= min_confidence])
    out = cast(
        "pd.DataFrame",
        out.sort_values(
            ["score", "confidence", "symbol"],
            ascending=[False, False, True],
            na_position="last",
            kind="stable",
        ),
    )
    out.index = pd.RangeIndex(start=1, stop=len(out) + 1, name="rank")
    return out
