"""CLI: the accumulation-plan briefing (sleeve pick + long-horizon candidates).

Reads the plan from ``config/dca_plan.yaml``, fetches what it needs, and writes
``REPORT_DCA.md`` plus ``public/data/dca_report.json`` for the dashboard tab.

Two things it deliberately does *not* do: touch the core allocation (BTC/ETH is
the user's decision, not the model's), and present the sleeve pick without the
backtest result that says the pick earns no return edge — the evidence travels
inside both outputs.

Run:
  uv run python -m src.ingestion.tier1.dca_cli              # full run
  uv run python -m src.ingestion.tier1.dca_cli --no-candidates  # skip CoinGecko
  uv run python -m src.ingestion.tier1.dca_cli --validate   # re-run the backtest
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, cast

import pandas as pd
import yaml

from src.assets.asset import Asset, get_asset_by_symbol
from src.features.dca_advisor import advise
from src.features.dca_backtest import compare, random_control, split_halves
from src.features.dca_candidates import min_age_years, screen_candidates
from src.features.dca_report import (
    dca_report_dict,
    format_report,
    write_markdown,
    write_report_json,
)
from src.features.fundamentals import profile_frame
from src.ingestion.freshness import check_freshness, last_timestamp_of
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

CONFIG_PATH = Path("config/dca_plan.yaml")
REPORT_PATH = Path("REPORT_DCA.md")
JSON_PATH = Path("public/data/dca_report.json")
CATEGORIES_PATH = Path("data/category_history/categories_latest.parquet")

# The advisor's discount term looks back 180 days; fetch a comfortable margin so
# the window is full even after a feed gap.
FETCH_START = "2024-06-01"
# Stale price data would silently freeze the pick on last week's weights.
MAX_AGE_DAYS = 5


def load_plan(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Read the plan config, or raise with a message the user can act on."""
    if not path.exists():
        raise SystemExit(f"Config non trovata: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SystemExit(f"Config non valida (atteso un mapping): {path}")
    return cast("dict[str, Any]", loaded)


def fetch_panel(symbols: list[str], start: str = FETCH_START) -> pd.DataFrame:
    """Daily closes for ``symbols`` as a date-indexed panel, one column each.

    A symbol that fails or comes back stale is dropped with a warning rather than
    poisoning the panel: a frozen feed would keep the pick pinned to old prices
    (the POL/MATIC lesson, ADR-026).
    """
    source = YahooFinanceSource()
    closes: dict[str, pd.Series] = {}
    for symbol in symbols:
        asset: Asset | None = get_asset_by_symbol(symbol)
        if asset is None or asset.yahoo_symbol is None:
            logger.warning("Nessun ticker Yahoo per %s: saltato", symbol)
            continue
        try:
            ohlcv = source.fetch_ohlcv(asset, start=start, interval="1d")
        except Exception:
            logger.exception("Fetch fallito per %s (%s)", symbol, asset.yahoo_symbol)
            continue
        if ohlcv.empty:
            logger.warning("Nessun dato per %s", symbol)
            continue
        fresh = check_freshness(last_timestamp_of(ohlcv), max_age_days=MAX_AGE_DAYS, name=symbol)
        if not fresh.is_fresh:
            logger.warning("Feed non aggiornato per %s: %s", symbol, fresh.message())
            continue
        closes[symbol] = cast("pd.Series", ohlcv["close"])
    if not closes:
        return pd.DataFrame()
    return pd.DataFrame(closes).sort_index()


def replay_units(
    panel: pd.DataFrame,
    targets: dict[str, float],
    budget_eur: float,
    start_date: str | None,
) -> dict[str, float]:
    """Units the plan would hold now, by replaying its own rule from ``start_date``.

    Used only when the config carries no real ``holdings_units``. It is an
    estimate of the position, not a statement about it, and both reports say so.
    """
    from src.features.dca_backtest import simulate

    result = simulate(
        panel,
        rule="advisor",
        budget_eur=budget_eur,
        target_weights=targets,
        start=start_date,
        fee_pct=0.5,
    )
    return cast("dict[str, float]", result["units"])


# One CoinGecko call per coin, throttled: the shortlist has to stay small enough
# that a daily cron finishes without tripping the free-tier limit.
MAX_PROFILED: int = 25

# Verdicts that always make the report even when they fall outside the top N.
# A shortlist that quietly drops them shows only what passed, which teaches the
# reader nothing about where the bar actually is.
DISQUALIFYING_VERDICTS: tuple[str, ...] = ("no_value_capture", "governance_only")


def _candidates(
    held: list[str], top_n: int
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Filter the universe, then profile the survivors on fundamentals.

    Two stages on purpose: the mechanical filters are one cheap call over the
    whole top-100, and the fundamental profile costs a call per coin. Ranking
    comes from the second stage — the first only decides who is worth the call.

    ``(None, None)`` if the market snapshot fails; a failure in the *profiling*
    stage still returns the filtered universe, unranked, rather than nothing.
    """
    from src.ingestion.tier1.coingecko import CoinGeckoSource

    source = CoinGeckoSource()
    try:
        markets = source.fetch_markets()
    except Exception:
        logger.exception("Fetch CoinGecko fallito: sezione progetti omessa")
        return None, None
    categories = pd.read_parquet(CATEGORIES_PATH) if CATEGORIES_PATH.exists() else None
    survivors, rejected = screen_candidates(
        markets, held_symbols=held, categories=categories, top_n=min(top_n * 2, MAX_PROFILED)
    )
    if survivors.empty:
        return survivors, rejected

    coin_ids = [str(c) for c in survivors["coingecko_id"] if c]
    try:
        details = source.fetch_coin_details(coin_ids)
    except Exception:
        logger.exception("Dettagli CoinGecko falliti: nessuna scheda fondamentale")
        return survivors, rejected
    if details.empty:
        return survivors, rejected

    # Genesis dates are missing for many coins; carry the all-time-low lower
    # bound across so the profile has a fallback age instead of a blank.
    now = pd.Timestamp.now(tz="UTC")
    fallback = {
        str(r.get("coingecko_id")): min_age_years(r.get("atl_date"), now)
        for r in markets.to_dict("records")
    }
    details["min_age_years"] = [fallback.get(str(c)) for c in details["coingecko_id"]]
    caps = {str(r.get("coingecko_id")): r.get("market_cap") for r in survivors.to_dict("records")}

    profiled = profile_frame(details)
    if profiled.empty:
        return survivors, rejected
    profiled["market_cap"] = [caps.get(str(c)) for c in profiled["coingecko_id"]]
    # Keep the top of the ranking, but never truncate away the projects that
    # failed on fundamentals: seeing *why* something is disqualified is the point
    # of the section, and those rows sort last precisely because they failed.
    head = profiled.head(top_n)
    disqualified = profiled.loc[profiled["verdict"].isin(list(DISQUALIFYING_VERDICTS))]
    shown = pd.concat([head, disqualified]).drop_duplicates(subset="symbol", keep="first")
    shown["rank"] = range(1, len(shown) + 1)
    return shown, rejected


def _validate(panel: pd.DataFrame) -> None:
    """Re-run the validation study and print it (the numbers behind the report)."""
    pd.set_option("display.width", 200)
    cols = ["rule", "multiple", "vs_split", "max_drawdown_pct", "weight_drift_pp", "n_purchases"]
    print("\n=== Periodo completo ===")
    print(compare(panel, fee_pct=0.5)[cols].to_string(index=False))
    halves = split_halves(panel, fee_pct=0.5)
    for label, frame in halves.items():
        print(f"\n=== Metà {label} ===")
        print(frame[cols].to_string(index=False))
    print("\n=== Controllo casuale (200 semi) ===")
    for rule in ("advisor", "momentum", "split"):
        print(rule, random_control(panel, rule=rule, n_seeds=200, fee_pct=0.5))


def main() -> None:
    parser = argparse.ArgumentParser(description="Briefing del piano di accumulo.")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Percorso del piano YAML.")
    parser.add_argument(
        "--no-candidates", action="store_true", help="Salta lo screen CoinGecko."
    )
    parser.add_argument("--top", type=int, default=10, help="Quante candidate mostrare.")
    parser.add_argument(
        "--validate", action="store_true", help="Ricalcola il backtest e stampalo."
    )
    args = parser.parse_args()

    plan = load_plan(Path(args.config))
    sleeve = cast("dict[str, Any]", plan.get("sleeve") or {})
    targets = cast("dict[str, float]", sleeve.get("target_weights") or {})
    budget = float(sleeve.get("budget_eur", 10.0))
    core = cast("dict[str, float]", plan.get("core") or {})
    if not targets:
        raise SystemExit("Config senza sleeve.target_weights: niente da classificare.")

    panel = fetch_panel(sorted(targets))
    if panel.empty:
        raise SystemExit("Nessun prezzo disponibile: impossibile produrre il briefing.")

    holdings = cast("dict[str, float]", plan.get("holdings_units") or {})
    holdings_estimated = not holdings
    if holdings_estimated:
        holdings = replay_units(panel, targets, budget, plan.get("start_date"))
        logger.info("holdings_units assente: posizione stimata replicando il piano")

    if args.validate:
        _validate(panel)

    ranked = advise(panel, target_weights=targets, holdings_units=holdings)
    held_symbols = [*core, *targets]
    shortlist, rejected = (
        (None, None) if args.no_candidates else _candidates(held_symbols, args.top)
    )

    text = format_report(
        ranked, shortlist, rejected, sleeve_eur=budget, holdings_estimated=holdings_estimated
    )
    write_markdown(text, REPORT_PATH)
    payload = dca_report_dict(
        ranked,
        shortlist,
        rejected,
        plan={
            "monthly_eur": plan.get("monthly_eur"),
            "start_date": plan.get("start_date"),
            "core": core,
            "sleeve_assets": sorted(targets),
            "holdings_estimated": holdings_estimated,
        },
        sleeve_eur=budget,
        holdings_estimated=holdings_estimated,
    )
    write_report_json(payload, JSON_PATH)
    logger.info("Scritti %s e %s", REPORT_PATH, JSON_PATH)
    print(text)


if __name__ == "__main__":
    main()
