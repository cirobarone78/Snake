"""Candidate screen for a long-horizon accumulation plan (which coins even qualify).

This module is a **pre-filter, not a ranker**. It answers:

    Of the coins large enough to see, which ones are even the right *kind* of
    thing to consider — and which are disqualified, and why?

It used to also score and rank the survivors, by market cap, liquidity and age.
That was wrong, and wrong in an instructive way: those are properties of the
ticker, not of the project behind it, so the ranking put Dogecoin second — big,
liquid, eleven years old, and with nothing underneath. Ranking now lives in
``src/features/fundamentals.py``, which asks what the thing does and who captures
its value. Here the survivors come out ordered by market cap and nothing else,
because market cap is a fact about size and this module claims nothing more.

The output is a **filtered universe with an explicit rejection log**. Every
filter is mechanical and checkable; none of them is a forecast.

The filters, and what each is actually for:

- **Already held** — a plan that re-buys what you own is not diversification.
- **Stablecoin / pegged** — a token engineered to stay at 1.00 cannot accumulate;
  it is cash with extra steps and extra counterparty risk.
- **Wrapped / staked / derivative** — a claim on another asset, not a separate
  bet. Owning wBTC alongside BTC is one position, not two.
- **Market cap floor** — the crude survivorship proxy. A large cap is no promise
  of survival, but the base rate for micro-caps over a decade is dismal.
- **Liquidity floor** — turnover (24h volume / market cap). A token with a huge
  nominal cap and almost no trading cannot be exited at the screen price; this
  is what removes locked-float exchange tokens and freshly minted RWA wrappers
  whose cap is an accounting figure rather than a market.
- **Turnover ceiling** — the opposite failure: volume far above cap is a
  pump or wash trading, not a market.

What these filters explicitly do *not* test is whether the project does anything.
A network with no users, no revenue and no development can clear every one of
them. That question is the whole subject of ``fundamentals.py``, and this module
is only the cheap first pass that narrows the universe before the expensive
per-coin calls that answer it.

**Survivorship bias — read this before using the output.** The screen sees
today's ranking, which is *by construction* the list of coins that survived. The
2018 top-100 is mostly gone; the names that vanished are not in the input, so
nothing here can measure how often a coin at this rank dies. The market-cap floor
is a proxy for durability, not a filter against failure, and the honest base rate
for individual altcoins over a decade is bad. Treat the shortlist as "these are
the ones worth researching", never as "these will work".

Age is reported as ``min_age_years``, derived from the all-time-low date, and it
is deliberately **one-sided**: an old ATL proves the coin is at least that old,
but a recent ATL proves nothing (a 2016 coin that made a new low last year looks
young, and POL — a 2024 rebrand of a 2019 token — looks months old). It is passed
through as a fallback for the real genesis date and never rejects anything.

Pure functions over pandas; the caller supplies the snapshot, so this is
unit-testable offline with no network.
"""

from __future__ import annotations

import re
from typing import cast

import numpy as np
import pandas as pd

# Survivorship proxy: below this the decade base rate gets materially worse.
DEFAULT_MIN_MARKET_CAP: float = 1e9

# 24h volume / market cap. Below the floor the "market cap" is an accounting
# figure (locked float, exchange token, tokenised RWA) rather than a market you
# could actually leave; above the ceiling it is a pump, not liquidity.
DEFAULT_MIN_TURNOVER: float = 0.01
DEFAULT_MAX_TURNOVER: float = 1.5

# Name patterns for tokens that are a claim on another asset rather than a
# separate bet. Matched on the human name, case-insensitive.
# Matched on the human name only. A symbol-shape rule ("starts with W") was
# tried and dropped: it threw out Worldcoin and World Liberty Financial, which
# are not wrappers of anything. Wrappers say so in their name.
_DERIVATIVE_PATTERNS: tuple[str, ...] = (
    r"\bwrapped\b", r"\bstaked\b", r"\bliquid stak", r"\brestaked\b",
    r"\bbridged\b", r"\bpegged\b", r"\bsynthetic\b", r"\btokenized\b",
    r"\btokenised\b",
)

# Descriptive context tags surfaced next to a candidate. These are *not* filters
# and carry no judgment: a meme coin can clear every mechanical test in this
# module, and the reader deserves to see that written on the row rather than
# discover it later. Regexes, not substrings — "centralized exchange" is a
# substring of "*de*centralized exchange", which tagged Uniswap as a CEX token.
_FLAG_RULES: tuple[tuple[str, str], ...] = (
    (r"\bmeme\b", "meme"),
    (r"exchange-based", "exchange_token"),
    (r"(?<!de)centralized exchange", "exchange_token"),
    (r"\bprivacy\b", "privacy"),
    (r"real world assets", "rwa"),
    (r"artificial intelligence", "ai"),
    (r"stablecoin", "stablecoin_adjacent"),
)

# Stablecoin naming, as a complement to the price test below (a depegged
# stablecoin is still a stablecoin, and the price test alone would miss it).
_STABLE_PATTERNS: tuple[str, ...] = (
    r"\busd\b", r"usd$", r"^usd", r"\bdollar\b", r"\beuro\b", r"\btether\b",
    r"\bdai\b", r"stablecoin", r"\bfrax\b", r"\bpyusd\b",
)

# A token trading this close to 1.00 and barely moving is pegged in practice,
# whatever it calls itself.
_PEG_TOLERANCE_PCT: float = 3.0
_PEG_MAX_DAILY_MOVE_PCT: float = 1.5

_OUT_COLS = [
    "symbol", "name", "coingecko_id", "market_cap", "market_cap_rank",
    "turnover", "min_age_years", "ath_change_pct", "categories", "flags",
    "diversifying", "rank",
]

_REJECT_COLS = ["symbol", "name", "market_cap", "reason"]


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in patterns)


def is_pegged(name: str, symbol: str, price: float | None, change_24h_pct: float | None) -> bool:
    """True when the token is a stablecoin in name or in behaviour."""
    if _matches(name, _STABLE_PATTERNS) or _matches(symbol, _STABLE_PATTERNS):
        return True
    if price is None or not np.isfinite(price):
        return False
    near_one = abs(price - 1.0) * 100.0 <= _PEG_TOLERANCE_PCT
    quiet = change_24h_pct is None or abs(change_24h_pct) <= _PEG_MAX_DAILY_MOVE_PCT
    return near_one and quiet


def is_derivative(name: str) -> bool:
    """True when the token is a wrapper/claim on another asset."""
    return _matches(name, _DERIVATIVE_PATTERNS)


def context_flags(categories: list[str]) -> list[str]:
    """Descriptive tags for a candidate's categories (never a filter)."""
    low = " | ".join(categories).lower()
    flags: list[str] = []
    for pattern, flag in _FLAG_RULES:
        if flag not in flags and re.search(pattern, low):
            flags.append(flag)
    return flags


def coin_categories(categories: pd.DataFrame) -> dict[str, list[str]]:
    """Invert a category snapshot into ``coingecko_id -> [category name, ...]``.

    ``top_coins`` only names each category's leading coins, so the map is
    partial by construction — a coin absent from it is "categories unknown",
    never "belongs to nothing".
    """
    mapping: dict[str, list[str]] = {}
    if categories.empty or "top_coins" not in categories.columns:
        return mapping
    for row in categories.to_dict("records"):
        raw = row.get("top_coins")
        if not isinstance(raw, str) or not raw:
            continue
        label = str(row.get("name") or row.get("category_id") or "")
        for coin_id in (c.strip() for c in raw.split(",")):
            if coin_id:
                mapping.setdefault(coin_id, []).append(label)
    return mapping


def min_age_years(atl_date: object, as_of: pd.Timestamp) -> float:
    """Lower bound on the coin's age, in years, from its all-time-low date.

    Public because ``fundamentals`` uses it as the fallback when the provider has
    no genesis date. A *lower* bound only: a recent all-time low says nothing
    about when the coin was created.
    """
    if atl_date is None or (isinstance(atl_date, float) and np.isnan(atl_date)):
        return float("nan")
    try:
        ts = pd.Timestamp(cast("str", atl_date))
    except (ValueError, TypeError):
        return float("nan")
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return max(0.0, float((as_of - ts).days) / 365.25)


def screen_candidates(
    markets: pd.DataFrame,
    held_symbols: list[str] | None = None,
    categories: pd.DataFrame | None = None,
    min_market_cap: float = DEFAULT_MIN_MARKET_CAP,
    min_turnover: float = DEFAULT_MIN_TURNOVER,
    max_turnover: float = DEFAULT_MAX_TURNOVER,
    top_n: int = 10,
    as_of: pd.Timestamp | str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Filtered universe and rejection log from a coin-markets snapshot.

    ``markets`` is the output of ``CoinGeckoSource.fetch_markets``. Returns
    ``(survivors, rejected)``: the coins that cleared every filter, ordered by
    **market cap and nothing else**, capped at ``top_n``; and every excluded coin
    with the reason it failed — the rejections are half the answer, so they are
    returned rather than dropped.

    There is deliberately no quality score here. Ordering by size is a statement
    about size; ranking these coins against each other requires knowing what they
    do, which is ``fundamentals.profile_frame``'s job. ``top_n`` exists because
    the next stage costs one API call per coin, so the universe has to be cut
    somewhere — cutting by size is the least opinionated cut available.
    """
    if markets.empty:
        return pd.DataFrame(columns=_OUT_COLS), pd.DataFrame(columns=_REJECT_COLS)

    now = cast(
        "pd.Timestamp",
        pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.now(tz="UTC"),
    )
    if now.tzinfo is None:
        now = cast("pd.Timestamp", now.tz_localize("UTC"))
    held = {s.upper() for s in (held_symbols or [])}
    cat_map = coin_categories(categories) if categories is not None else {}
    held_categories = {
        c
        for row in markets.to_dict("records")
        if str(row.get("symbol") or "").upper() in held
        for c in cat_map.get(str(row.get("coingecko_id") or ""), [])
    }

    kept: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []

    for row in markets.to_dict("records"):
        symbol = str(row.get("symbol") or "").upper()
        name = str(row.get("name") or "")
        market_cap = _num(row.get("market_cap"))
        volume = _num(row.get("total_volume"))
        price = _num(row.get("current_price"))
        change = _num(row.get("price_change_24h_pct"))
        base = {"symbol": symbol, "name": name, "market_cap": market_cap}

        if symbol in held:
            rejected.append({**base, "reason": "already_held"})
            continue
        if is_pegged(name, symbol, price, change):
            rejected.append({**base, "reason": "stablecoin_or_pegged"})
            continue
        if is_derivative(name):
            rejected.append({**base, "reason": "wrapped_or_derivative"})
            continue
        if market_cap is None or market_cap < min_market_cap:
            rejected.append({**base, "reason": "market_cap_below_floor"})
            continue
        turnover = (volume / market_cap) if (volume is not None and market_cap > 0) else None
        if turnover is None or turnover < min_turnover:
            rejected.append({**base, "reason": "illiquid"})
            continue
        if turnover > max_turnover:
            rejected.append({**base, "reason": "turnover_anomaly"})
            continue

        coin_id = str(row.get("coingecko_id") or "")
        cats = cat_map.get(coin_id, [])
        kept.append(
            {
                "symbol": symbol,
                "name": name,
                "coingecko_id": coin_id,
                "market_cap": market_cap,
                "market_cap_rank": _num(row.get("market_cap_rank")),
                "turnover": round(turnover, 5),
                "min_age_years": round(min_age_years(row.get("atl_date"), now), 2),
                "ath_change_pct": _num(row.get("ath_change_pct")),
                "categories": ", ".join(cats) if cats else None,
                "flags": ", ".join(context_flags(cats)) if cats else None,
                # No category info means we cannot claim it diversifies. Unknown
                # is reported as False, not optimistically as True.
                "diversifying": bool(cats) and not (set(cats) & held_categories),
            }
        )

    reject_frame = pd.DataFrame(rejected, columns=_REJECT_COLS)
    if not kept:
        return pd.DataFrame(columns=_OUT_COLS), reject_frame

    out = pd.DataFrame(kept)
    out = out.sort_values(
        ["market_cap", "symbol"], ascending=[False, True], kind="stable"
    ).head(top_n)
    out["rank"] = np.arange(1, len(out) + 1)
    out.index = pd.RangeIndex(start=1, stop=len(out) + 1, name="rank")
    return cast("pd.DataFrame", out[_OUT_COLS]), reject_frame


def _num(value: object) -> float | None:
    """Plain float, or ``None`` for missing/NaN (never invent a value)."""
    if value is None:
        return None
    try:
        f = float(cast("float", value))
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(f) else f
