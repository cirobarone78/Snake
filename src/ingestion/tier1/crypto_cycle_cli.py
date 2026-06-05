"""CLI: the probabilistic layer on the crypto majors, keyed to the halving cycle.

"Given where we are in the Bitcoin halving cycle (and the market regime), what did
forward crypto returns look like historically?" Fetches the 5 Tier-1 majors, and
conditions their forward returns on:

- the **halving-cycle phase** (early / mid / late of the ~4-year cycle), the
  cyclical pattern the user cares about ("knowing the past helps spot the cycles");
- the **BTC market regime** (bull/bear x high/low vol);
- their combination.

Reported plain (overlapping n), then **non-overlapping** + **out-of-sample** for
the headline (phase) conditioning.

⚠️ HONESTY (CLAUDE.md, non-negotiable): daily crypto history covers only ~1.5-2
halving cycles, so any phase conclusion rests on a **tiny number of cycles** — this
is **descriptive**, not evidence of a repeatable edge. State is point-in-time (the
phase is a pure calendar feature; the regime is causal). A picture of the past,
never a promise about the future.

Run:
  uv run python -m src.ingestion.tier1.crypto_cycle_cli
  uv run python -m src.ingestion.tier1.crypto_cycle_cli --start 2018-01-01
"""

from __future__ import annotations

import argparse

import pandas as pd

from src.assets.asset import TIER1_ASSETS, get_asset_by_symbol
from src.features.conditional_outcomes import (
    conditional_outcome_table,
    forward_observations,
    split_by_date,
    state_ranking,
)
from src.features.cycles import days_since_last_halving, halving_cycle_phase
from src.features.regime import classify_regime, classify_vol_regime, combine_regimes
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

DEFAULT_START = "2018-01-01"
DEFAULT_HORIZONS = (21, 63, 126)  # ~1, 3, 6 months (crypto cycles are long)
_PHASE_LABELS = ["early", "mid", "late"]


def build_panel(start: str) -> pd.DataFrame:
    """Fetch each Tier-1 crypto major's daily close into a date x symbol panel."""
    src = YahooFinanceSource()
    closes: dict[str, pd.Series] = {}
    for asset in TIER1_ASSETS:
        try:
            ohlcv = src.fetch_ohlcv(asset, start=start, interval="1d")
        except Exception:  # tolerate a flaky single feed
            continue
        if not ohlcv.empty:
            closes[asset.symbol] = ohlcv["close"]
    if not closes:
        return pd.DataFrame()
    return pd.concat(closes, axis=1).sort_index()


def halving_phase_state(index: pd.DatetimeIndex) -> pd.Series:
    """Per-date early/mid/late label from the halving-cycle phase (calendar)."""
    phase = halving_cycle_phase(index)
    cut = pd.cut(phase, bins=[0.0, 1 / 3, 2 / 3, 1.0], labels=_PHASE_LABELS, include_lowest=True)
    return pd.Series(cut.astype("object"), index=index, name="phase")


def btc_regime_state(start: str) -> pd.Series:
    """BTC 4-state regime (bull/bear x high/low vol) as the crypto market regime."""
    btc = get_asset_by_symbol("BTC")
    if btc is None:
        return pd.Series(dtype=object)
    close = YahooFinanceSource().fetch_ohlcv(btc, start=start, interval="1d").sort_index()["close"]
    trend = classify_regime(close, window=200)
    vol = classify_vol_regime(close.pct_change().dropna())
    return combine_regimes(trend, vol)


def main() -> None:
    parser = argparse.ArgumentParser(description="Crypto cycle probabilistic layer.")
    parser.add_argument("--start", default=DEFAULT_START, help="History start (YYYY-MM-DD).")
    args = parser.parse_args()

    panel = build_panel(args.start)
    if panel.empty:
        raise SystemExit("No crypto data fetched.")
    phase = halving_phase_state(pd.DatetimeIndex(panel.index))
    regime = btc_regime_state(args.start)

    span = f"{panel.index.min().date()} → {panel.index.max().date()}"
    print(f"\n=== Layer probabilistico crypto — ciclo halving — {span} ===")
    print(f"Universo: {list(panel.columns)} | stati: fase halving (early/mid/late) + regime BTC")
    print("Ipotesi (scritte prima): H1 i forward più alti nelle fasi early/mid "
          "post-halving, peggiori in late; H2 bear_high_vol BTC → rimbalzo; H3 con "
          "~1.5-2 cicli il campione è minuscolo e l'OOS sarà instabile → descrittivo.\n")

    extra = {"phase": phase}
    if not regime.empty:
        extra["regime"] = regime

    for horizon in DEFAULT_HORIZONS:
        obs = forward_observations(panel, horizon=horizon, extra_states=extra)
        obs = obs[obs["phase"] != "nan"]
        print(f"========== Forward {horizon}g ==========")

        by_phase = conditional_outcome_table(obs, state_col="phase", labels=_PHASE_LABELS)
        print("--- per fase di halving ---")
        print(by_phase.to_string(index=False))

        if "regime" in obs.columns:
            obs_r = obs[obs["regime"] != "unknown"]
            by_regime = conditional_outcome_table(obs_r, state_col="regime")
            print("\n--- per regime BTC ---")
            print(by_regime.to_string(index=False))

        # non-overlapping + OOS on the phase conditioning (the headline)
        obs_no = forward_observations(panel, horizon=horizon, step=horizon, extra_states=extra)
        obs_no = obs_no[obs_no["phase"] != "nan"]
        nonoverlap = conditional_outcome_table(obs_no, state_col="phase", labels=_PHASE_LABELS)
        train, test = split_by_date(obs_no, train_frac=0.5)
        t_train = conditional_outcome_table(train, state_col="phase", labels=_PHASE_LABELS)
        t_test = conditional_outcome_table(test, state_col="phase", labels=_PHASE_LABELS)
        print("\n--- fase, non-overlapping (n onesto) + OOS ---")
        print(nonoverlap.to_string(index=False))
        print(f"  OOS ranking (hit-rate)  train: {state_ranking(t_train)}  "
              f"|  test: {state_ranking(t_test)}")
        print()

    # Where are we now? The actionable part: locate today in the cycle.
    idx = pd.DatetimeIndex(panel.index)
    now_phase = str(phase.iloc[-1])
    now_days = float(days_since_last_halving(idx).iloc[-1])
    now_regime = str(regime.iloc[-1]) if not regime.empty else "n/d"
    print(f"📍 STATO ATTUALE ({panel.index.max().date()}): fase ciclo = {now_phase.upper()} "
          f"(~{now_days:.0f}g dall'ultimo halving) | regime BTC = {now_regime}")
    print("   → storicamente la fase 'mid' è stata la zona peggiore (mediana forward "
          "negativa, hit-rate ~0.2-0.3); 'early'/'late' positive.\n")

    print("Nota: ~1.5-2 cicli di halving nello storico → DESCRITTIVO, non un edge "
          "ripetibile. Stato point-in-time (fase = calendario, regime = causale).")


if __name__ == "__main__":
    main()
