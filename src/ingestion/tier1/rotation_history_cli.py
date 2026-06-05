"""CLI: the probabilistic rotation layer on real history.

"Given a rotation state, what did the forward return look like historically?"
Fetches years of sector-ETF closes, builds a point-in-time panel, and reports the
conditional forward-return table per momentum bucket (weak/mid/strong), three ways:

1. **Plain** — overlapping daily observations (inflated n, quick read).
2. **Enriched state** — momentum bucket x **market regime** (S&P 500 bull/bear x
   high/low vol), to see if momentum pays off differently across regimes.
3. **Validated** — **non-overlapping** windows (honest n) and an **out-of-sample**
   train/test split: does the in-sample bucket ranking survive out-of-sample?

Honest by design (CLAUDE.md): the state is reconstructed point-in-time (no
look-ahead). A description of the past distribution, never a promise about the
future.

Run:
  uv run python -m src.ingestion.tier1.rotation_history_cli
  uv run python -m src.ingestion.tier1.rotation_history_cli --lookback 63 --start 2010-01-01
"""

from __future__ import annotations

import argparse

import pandas as pd

from src.assets.asset import get_asset_by_symbol
from src.assets.sectors import SECTOR_ETFS
from src.features.conditional_outcomes import (
    conditional_outcome_table,
    rotation_observations,
    rotation_outcomes,
    split_by_date,
    state_ranking,
)
from src.features.regime import classify_regime, classify_vol_regime, combine_regimes
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource

DEFAULT_START = "2012-01-01"
DEFAULT_HORIZONS = (5, 21, 63)  # ~1 week, ~1 month, ~1 quarter (trading days)


def build_panel(start: str) -> pd.DataFrame:
    """Fetch each sector ETF's daily close and assemble a date x symbol panel."""
    src = YahooFinanceSource()
    closes: dict[str, pd.Series] = {}
    for asset in SECTOR_ETFS:
        try:
            ohlcv = src.fetch_ohlcv(asset, start=start, interval="1d")
        except Exception:  # tolerate a flaky single feed
            continue
        if not ohlcv.empty:
            closes[asset.symbol] = ohlcv["close"]
    if not closes:
        return pd.DataFrame()
    return pd.concat(closes, axis=1).sort_index()


def market_regime(start: str) -> pd.Series:
    """S&P 500 4-state regime (bull/bear x high/low vol), causal, per date."""
    spx = get_asset_by_symbol("SPX")
    if spx is None:
        return pd.Series(dtype=object)
    close = YahooFinanceSource().fetch_ohlcv(spx, start=start, interval="1d").sort_index()["close"]
    trend = classify_regime(close, window=200)
    vol = classify_vol_regime(close.pct_change().dropna())
    return combine_regimes(trend, vol)


def _summary_line(table: pd.DataFrame) -> str:
    base = table[table["state"] == "ALL"].iloc[0]
    strong = table[table["state"] == "strong"]
    if strong.empty:
        return "  (nessun bucket 'strong')"
    s = strong.iloc[0]
    d_hit = (s["hit_rate"] - base["hit_rate"]) * 100.0
    d_mean = s["mean_fwd_pct"] - base["mean_fwd_pct"]
    return f"  strong vs baseline: hit-rate {d_hit:+.1f}pp, media {d_mean:+.2f}pp"


def main() -> None:
    parser = argparse.ArgumentParser(description="Probabilistic rotation layer on history.")
    parser.add_argument("--start", default=DEFAULT_START, help="History start date (YYYY-MM-DD).")
    parser.add_argument("--lookback", type=int, default=21, help="Momentum lookback (days).")
    parser.add_argument("--buckets", type=int, default=3, help="Cross-sectional buckets.")
    args = parser.parse_args()

    panel = build_panel(args.start)
    if panel.empty:
        raise SystemExit("No sector data fetched.")
    regime = market_regime(args.start)

    span = f"{panel.index.min().date()} → {panel.index.max().date()}"
    print(f"\n=== Layer probabilistico rotazione settoriale (equity) — {span} ===")
    print(f"Universo: {panel.shape[1]} ETF | lookback momentum: {args.lookback}g | "
          f"bucket cross-sectional: {args.buckets}")
    print("Ipotesi (scritte prima): H1 il momentum di settore persiste a 1-3 mesi; "
          "H2 il momentum 'paga' più nei regimi bull/low-vol che nei bear/high-vol; "
          "H3 con n non sovrapposto e OOS le differenze si riducono ulteriormente.\n")

    for horizon in DEFAULT_HORIZONS:
        print(f"========== Forward {horizon}g (stato = momentum {args.lookback}g) ==========")

        # 1) plain, overlapping
        plain = rotation_outcomes(panel, lookback=args.lookback, horizon=horizon,
                                  n_buckets=args.buckets)
        print("--- (1) plain (n sovrapposto) ---")
        print(plain.to_string(index=False))
        print(_summary_line(plain))

        # 2) enriched: momentum bucket x market regime
        if not regime.empty:
            obs_r = rotation_observations(
                panel, lookback=args.lookback, horizon=horizon, n_buckets=args.buckets,
                extra_states={"regime": regime},
            )
            obs_r = obs_r[obs_r["regime"] != "unknown"]
            table_r = conditional_outcome_table(obs_r, state_col=["bucket", "regime"])
            print("\n--- (2) stato arricchito: momentum x regime S&P 500 ---")
            print(table_r.to_string(index=False))

        # 3) validated: non-overlapping + OOS train/test
        obs_no = rotation_observations(panel, lookback=args.lookback, horizon=horizon,
                                       n_buckets=args.buckets, step=horizon)
        nonoverlap = conditional_outcome_table(obs_no, labels=["weak", "mid", "strong"])
        train, test = split_by_date(obs_no, train_frac=0.5)
        t_train = conditional_outcome_table(train, labels=["weak", "mid", "strong"])
        t_test = conditional_outcome_table(test, labels=["weak", "mid", "strong"])
        print("\n--- (3) non-overlapping (n onesto) ---")
        print(nonoverlap.to_string(index=False))
        print(_summary_line(nonoverlap))
        print(f"  OOS ranking (hit-rate)  train: {state_ranking(t_train)}  "
              f"|  test: {state_ranking(t_test)}")
        print()

    print("Nota: stato point-in-time (no look-ahead). In (1) n = osservazioni "
          "SOVRAPPOSTE (indicativo); (3) usa finestre non sovrapposte e un test "
          "OOS. Se il ranking train≠test, l'edge era rumore in-sample.")


if __name__ == "__main__":
    main()
