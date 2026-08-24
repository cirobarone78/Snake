"""Offline tests for the point-in-time ETF panel (WP2). No network.

The tests that matter here are the causality ones: a feature that peeks at the
future is a silent bug that looks like a great model. Everything is synthetic and
deterministic.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd
import pytest

from src.assets.asset import get_asset_by_symbol
from src.features.etf_dataset import (
    FEATURE_COLUMNS,
    SCHEMA_VERSION,
    assemble,
    build_feature_panel,
    build_targets,
    coverage_report,
    dataset_metadata,
    target_columns,
)
from src.ingestion.tier1.yahoo_finance import YahooFinanceSource


def _dates(n: int, start: str = "2020-01-01") -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="B", tz="UTC")


def _closes(n: int = 400, n_assets: int = 5, seed: int = 0) -> pd.DataFrame:
    idx = _dates(n)
    rng = np.random.default_rng(seed)
    cols = {
        f"A{i}": 100.0 * np.cumprod(1.0 + rng.normal(0.0002, 0.01, n)) for i in range(n_assets)
    }
    return pd.DataFrame(cols, index=idx)


def _benchmark(n: int = 400, seed: int = 99) -> pd.Series:
    idx = _dates(n)
    rng = np.random.default_rng(seed)
    return pd.Series(300.0 * np.cumprod(1.0 + rng.normal(0.0003, 0.008, n)), index=idx, name="SPY")


def _volumes(closes: pd.DataFrame, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        rng.lognormal(15.0, 0.3, closes.shape), index=closes.index, columns=closes.columns
    )


# --- registry ---------------------------------------------------------------


def test_spy_benchmark_is_registered() -> None:
    spy = get_asset_by_symbol("SPY")
    assert spy is not None
    assert spy.yahoo_symbol == "SPY"
    assert spy.asset_class.value == "etf"
    assert spy.trading_calendar.value == "nyse"
    assert spy.tier == 3


# --- 1. causality -----------------------------------------------------------


def test_features_do_not_change_when_future_bars_are_added() -> None:
    """Adding bars after t must leave every feature at t byte-identical."""
    closes = _closes(400)
    bench = _benchmark(400)
    vols = _volumes(closes)
    cut = 300

    truncated = build_feature_panel(closes.iloc[:cut], vols.iloc[:cut], bench.iloc[:cut])
    full = build_feature_panel(closes, vols, bench)

    last_date = closes.index[cut - 1]
    full_prefix = full[full["date"] <= last_date].reset_index(drop=True)
    pd.testing.assert_frame_equal(truncated, full_prefix)


def test_target_uses_the_future_and_feature_does_not() -> None:
    """Sanity check on the check: perturbing a future bar moves the target only."""
    closes = _closes(200)
    bench = _benchmark(200)
    t = closes.index[100]

    base_feat = build_feature_panel(closes, None, bench)
    base_targ = build_targets(closes, bench, horizons=(20,))

    shocked = closes.copy()
    shocked.iloc[120:, 0] = shocked.iloc[120:, 0] * 1.5
    shock_feat = build_feature_panel(shocked, None, bench)
    shock_targ = build_targets(shocked, bench, horizons=(20,))

    def _at(frame: pd.DataFrame, col: str) -> float:
        row = frame[(frame["date"] == t) & (frame["symbol"] == "A0")]
        return float(row[col].to_numpy()[0])

    assert _at(base_feat, "ret_20") == pytest.approx(_at(shock_feat, "ret_20"))
    assert _at(base_targ, "excess_ret_20") != pytest.approx(_at(shock_targ, "excess_ret_20"))


# --- 2. targets are shifted forward ----------------------------------------


def test_target_is_the_realised_future_and_tail_is_nan() -> None:
    closes = _closes(120, n_assets=2)
    bench = _benchmark(120)
    targets = build_targets(closes, bench, horizons=(20,))

    t = closes.index[50]
    row = targets[(targets["date"] == t) & (targets["symbol"] == "A0")]
    expected_asset = closes["A0"].iloc[70] / closes["A0"].iloc[50] - 1.0
    expected_bench = bench.iloc[70] / bench.iloc[50] - 1.0
    assert float(row["excess_ret_20"].to_numpy()[0]) == pytest.approx(
        expected_asset - expected_bench
    )

    # The last `horizon` dates have no realised future: NaN, never filled.
    tail = targets[targets["date"] > closes.index[-21]]
    assert tail["excess_ret_20"].isna().all()
    assert tail["outperform_20"].isna().all()
    assert not tail.empty


def test_outperform_is_the_strict_sign_of_the_excess() -> None:
    closes = _closes(120, n_assets=3)
    bench = _benchmark(120)
    targets = build_targets(closes, bench, horizons=(20, 60))
    for h in (20, 60):
        excess = targets[f"excess_ret_{h}"]
        flag = targets[f"outperform_{h}"]
        realised = excess.notna()
        assert set(flag[realised].unique()) <= {0.0, 1.0}
        assert (flag[realised] == (excess[realised] > 0).astype("float64")).all()
        assert flag[~realised].isna().all()


# --- 3. an asset identical to the benchmark has zero excess ----------------


def test_asset_equal_to_benchmark_has_zero_excess_and_no_outperformance() -> None:
    bench = _benchmark(150)
    closes = pd.DataFrame({"CLONE": bench.to_numpy()}, index=bench.index)
    targets = build_targets(closes, bench, horizons=(20, 60))
    realised = targets["excess_ret_20"].notna()
    assert targets.loc[realised, "excess_ret_20"].abs().max() == pytest.approx(0.0, abs=1e-12)
    assert (targets.loc[realised, "outperform_20"] == 0.0).all()
    assert (targets.loc[targets["excess_ret_60"].notna(), "outperform_60"] == 0.0).all()

    features = build_feature_panel(closes, None, bench)
    for col in ("rel_ret_20", "rel_ret_60", "rel_ret_126"):
        defined = features[col].notna()
        assert features.loc[defined, col].abs().max() == pytest.approx(0.0, abs=1e-12)


# --- 4. short histories are kept, not dropped ------------------------------


def test_short_history_keeps_rows_with_nan_on_long_windows() -> None:
    closes = _closes(400, n_assets=2)
    bench = _benchmark(400)
    closes.iloc[:300, 1] = np.nan  # a fund that listed 100 bars ago
    features = build_feature_panel(closes, None, bench)

    short = features[features["symbol"] == "A1"]
    assert len(short) == 100  # rows kept, one per listed day
    assert short["ret_252"].isna().all()  # no 252-day history yet
    assert short["ret_20"].notna().any()  # short windows still defined
    # Pre-listing days produce no rows at all (the fund did not exist).
    assert short["date"].min() == closes.index[300]


# --- 5. alignment: inner join between universe and benchmark ---------------


def test_dates_are_the_inner_join_with_the_benchmark() -> None:
    closes = _closes(120, n_assets=2)
    bench = _benchmark(120).drop(index=[closes.index[10], closes.index[11]])
    features = build_feature_panel(closes, None, bench)
    targets = build_targets(closes, bench, horizons=(20,))
    expected = closes.index.intersection(bench.index)
    assert set(features["date"].unique()) == set(expected)
    assert set(targets["date"].unique()) == set(expected)
    assert closes.index[10] not in set(features["date"].unique())


# --- 6. cross-sectional rank ------------------------------------------------


def test_rank_is_bounded_and_neutral_on_a_degenerate_universe() -> None:
    closes = _closes(200, n_assets=6)
    bench = _benchmark(200)
    features = build_feature_panel(closes, None, bench)
    ranks = features["rank_rel_ret_60"].dropna()
    assert not ranks.empty
    assert ranks.min() >= 0.0
    assert ranks.max() <= 1.0
    # Every fully-defined date spans the whole [0, 1] range across the universe.
    by_date = features.dropna(subset=["rank_rel_ret_60"]).groupby("date")["rank_rel_ret_60"]
    assert by_date.min().max() == pytest.approx(0.0)
    assert by_date.max().min() == pytest.approx(1.0)

    single = build_feature_panel(closes[["A0"]], None, bench)
    solo_ranks = single["rank_rel_ret_60"].dropna()
    assert not solo_ranks.empty
    assert (solo_ranks == 0.5).all()


def test_rank_orders_by_relative_return() -> None:
    closes = _closes(200, n_assets=4)
    bench = _benchmark(200)
    features = build_feature_panel(closes, None, bench)
    day = features[features["date"] == closes.index[-1]].dropna(subset=["rank_rel_ret_60"])
    ordered = day.sort_values("rel_ret_60")["rank_rel_ret_60"].to_numpy()
    assert (np.diff(ordered) > 0).all()


# --- 7. regime attached by date --------------------------------------------


def test_regime_is_attached_per_date_and_unknown_where_missing() -> None:
    closes = _closes(150, n_assets=3)
    bench = _benchmark(150)
    features = build_feature_panel(closes, None, bench)
    targets = build_targets(closes, bench, horizons=(20,))
    labels = pd.Series("bull_low_vol", index=closes.index[:100], name="regime_4state")
    panel = assemble(features, targets, labels)

    assert (panel.loc[panel["date"] < closes.index[100], "regime"] == "bull_low_vol").all()
    assert (panel.loc[panel["date"] >= closes.index[100], "regime"] == "unknown").all()
    assert set(panel.columns) == {
        "date", "symbol", "close", "regime", *FEATURE_COLUMNS, *target_columns((20,))
    }


def test_assemble_keeps_one_row_per_date_symbol() -> None:
    closes = _closes(150, n_assets=3)
    bench = _benchmark(150)
    panel = assemble(
        build_feature_panel(closes, None, bench),
        build_targets(closes, bench),
        pd.Series("bull_high_vol", index=closes.index),
    )
    assert not panel.duplicated(subset=["date", "symbol"]).any()
    assert panel.attrs["schema_version"] == SCHEMA_VERSION
    assert panel.attrs["targets"] == target_columns()


# --- 8. determinism ---------------------------------------------------------


def test_two_builds_on_the_same_input_are_identical() -> None:
    closes = _closes(250, n_assets=4)
    bench = _benchmark(250)
    vols = _volumes(closes)
    regime = pd.Series("bear_high_vol", index=closes.index)

    first = assemble(
        build_feature_panel(closes, vols, bench), build_targets(closes, bench), regime
    )
    second = assemble(
        build_feature_panel(closes, vols, bench), build_targets(closes, bench), regime
    )
    pd.testing.assert_frame_equal(first, second)
    # Column order is part of the contract (the schema hash depends on it).
    assert dataset_metadata(first) == dataset_metadata(second)


def test_column_order_is_independent_of_input_column_order() -> None:
    closes = _closes(200, n_assets=4)
    bench = _benchmark(200)
    shuffled = closes[list(reversed(closes.columns))]
    a = build_feature_panel(closes, None, bench)
    b = build_feature_panel(shuffled, None, bench)
    pd.testing.assert_frame_equal(
        a.sort_values(["date", "symbol"]).reset_index(drop=True),
        b.sort_values(["date", "symbol"]).reset_index(drop=True),
    )


# --- 9. timezone ------------------------------------------------------------


def test_utc_index_in_utc_dates_out() -> None:
    closes = _closes(150, n_assets=2)
    bench = _benchmark(150)
    panel = assemble(
        build_feature_panel(closes, None, bench),
        build_targets(closes, bench, horizons=(20,)),
        pd.Series("bull_low_vol", index=closes.index),
    )
    dates = pd.DatetimeIndex(panel["date"])
    assert dates.tz is not None
    assert str(dates.tz) == "UTC"


# --- feature formulas -------------------------------------------------------


def test_feature_formulas_match_their_definitions() -> None:
    closes = _closes(400, n_assets=3)
    bench = _benchmark(400)
    vols = _volumes(closes)
    features = build_feature_panel(closes, vols, bench)
    t = closes.index[-1]
    row = features[(features["date"] == t) & (features["symbol"] == "A0")].iloc[0]
    px = closes["A0"]
    ret = px / px.shift(1) - 1.0

    assert float(row["ret_20"]) == pytest.approx(px.iloc[-1] / px.iloc[-21] - 1.0)
    assert float(row["rel_ret_60"]) == pytest.approx(
        (px.iloc[-1] / px.iloc[-61] - 1.0) - (bench.iloc[-1] / bench.iloc[-61] - 1.0)
    )
    assert float(row["vol_20"]) == pytest.approx(
        float(ret.iloc[-20:].std(ddof=0)) * np.sqrt(252)
    )
    assert float(row["dist_sma50"]) == pytest.approx(px.iloc[-1] / px.iloc[-50:].mean() - 1.0)
    assert float(row["dist_52w_high"]) == pytest.approx(px.iloc[-1] / px.iloc[-252:].max() - 1.0)
    assert float(row["drawdown"]) == pytest.approx(px.iloc[-1] / px.max() - 1.0)
    assert float(row["corr_60"]) == pytest.approx(
        float(ret.iloc[-60:].corr((bench / bench.shift(1) - 1.0).iloc[-60:]))
    )
    assert float(row["volume_z20"]) == pytest.approx(
        float(
            (vols["A0"].iloc[-1] - vols["A0"].iloc[-20:].mean())
            / vols["A0"].iloc[-20:].std(ddof=0)
        )
    )
    assert float(row["downside_vol_60"]) == pytest.approx(
        float(ret.iloc[-60:][ret.iloc[-60:] < 0].std(ddof=0)) * np.sqrt(252)
    )
    assert float(row["drawdown"]) <= 0.0


def test_beta_against_self_is_one() -> None:
    bench = _benchmark(300)
    closes = pd.DataFrame({"CLONE": bench.to_numpy()}, index=bench.index)
    features = build_feature_panel(closes, None, bench)
    beta = features["beta_60"].dropna()
    assert not beta.empty
    assert beta.max() == pytest.approx(1.0)
    assert features["corr_60"].dropna().min() == pytest.approx(1.0)


def test_volume_is_optional() -> None:
    closes = _closes(200, n_assets=3)
    bench = _benchmark(200)
    assert build_feature_panel(closes, None, bench)["volume_z20"].isna().all()
    partial = _volumes(closes)[["A0"]]
    features = build_feature_panel(closes, partial, bench)
    assert features.loc[features["symbol"] == "A0", "volume_z20"].notna().any()
    assert features.loc[features["symbol"] == "A1", "volume_z20"].isna().all()


# --- degenerate inputs ------------------------------------------------------


def test_empty_input_gives_typed_empty_frames() -> None:
    empty = pd.DataFrame()
    bench = _benchmark(10)
    features = build_feature_panel(empty, None, bench)
    targets = build_targets(empty, bench)
    assert features.empty
    assert list(features.columns) == ["date", "symbol", "close", *FEATURE_COLUMNS]
    assert targets.empty
    assert list(targets.columns) == ["date", "symbol", *target_columns()]
    assert coverage_report(features).empty


def test_build_targets_rejects_non_positive_horizon() -> None:
    closes = _closes(50, n_assets=2)
    with pytest.raises(ValueError, match="horizon must be positive"):
        build_targets(closes, _benchmark(50), horizons=(0,))


# --- reporting --------------------------------------------------------------


def test_coverage_report_flags_the_short_history() -> None:
    closes = _closes(400, n_assets=3)
    bench = _benchmark(400)
    closes.iloc[:300, 2] = np.nan
    features = build_feature_panel(closes, None, bench)
    report = coverage_report(features)

    assert list(report["symbol"]) == ["A0", "A1", "A2"]
    short = report[report["symbol"] == "A2"].iloc[0]
    long_lived = report[report["symbol"] == "A0"].iloc[0]
    assert int(short["rows"]) == 100
    assert float(short["missing_feature_pct"]) > float(long_lived["missing_feature_pct"])
    assert short["first_date"] == str(closes.index[300])[:10]


def test_metadata_describes_the_panel() -> None:
    closes = _closes(300, n_assets=3)
    bench = _benchmark(300)
    panel = assemble(
        build_feature_panel(closes, None, bench),
        build_targets(closes, bench),
        pd.Series("bull_low_vol", index=closes.index),
    )
    meta = dataset_metadata(panel)
    assert meta["rows"] == len(panel)
    assert meta["n_symbols"] == 3
    assert meta["symbols"] == ["A0", "A1", "A2"]
    assert meta["features"] == FEATURE_COLUMNS
    assert meta["targets"] == target_columns()
    assert meta["date_start"] == str(closes.index[0])[:10]
    assert meta["date_end"] == str(closes.index[-1])[:10]
    assert isinstance(meta["schema_hash"], str)
    assert len(str(meta["schema_hash"])) == 16


# --- CLI orchestration (no network: a stub source stands in for Yahoo) -------


class _StubSource:
    """Minimal ``YahooFinanceSource`` stand-in: canned bars, scripted failures."""

    def __init__(self, bars: dict[str, pd.DataFrame], failures: set[str] | None = None) -> None:
        self.bars = bars
        self.failures = failures or set()
        self.requested: list[str] = []

    def fetch_ohlcv(
        self, asset: object, start: object, end: object = None, interval: str = "1d"
    ) -> pd.DataFrame:
        symbol = str(getattr(asset, "symbol", ""))
        self.requested.append(symbol)
        if symbol in self.failures:
            raise RuntimeError(f"boom {symbol}")
        return self.bars.get(symbol, pd.DataFrame())


def _ohlcv(series: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"close": series, "volume": 1e6}, index=series.index)


def test_cli_fetch_skips_failed_and_empty_symbols() -> None:
    from src.assets.asset import Asset, AssetClass
    from src.ingestion.tier1.build_etf_dataset import _fetch_close_volume

    idx = _dates(30)
    good = Asset(symbol="GOOD", asset_class=AssetClass.ETF, name="ok", yahoo_symbol="G")
    broken = Asset(symbol="BROKEN", asset_class=AssetClass.ETF, name="ko", yahoo_symbol="B")
    silent = Asset(symbol="SILENT", asset_class=AssetClass.ETF, name="mute", yahoo_symbol="S")
    source = _StubSource(
        {"GOOD": _ohlcv(pd.Series(100.0, index=idx))}, failures={"BROKEN"}
    )

    closes, volumes = _fetch_close_volume(
        cast("YahooFinanceSource", source), [good, broken, silent], "2020-01-01"
    )
    assert list(closes) == ["GOOD"]
    assert list(volumes) == ["GOOD"]
    assert source.requested == ["GOOD", "BROKEN", "SILENT"]


def test_cli_regime_is_a_four_state_label_from_prices_only() -> None:
    from src.ingestion.tier1.build_etf_dataset import benchmark_regime

    bench = _benchmark(600)
    regime = benchmark_regime(bench)
    labels = set(regime.unique())
    assert labels <= {
        "bull_low_vol", "bull_high_vol", "bear_low_vol", "bear_high_vol", "unknown"
    }
    assert (regime.iloc[:100] == "unknown").all()  # 200-day SMA warm-up
    assert (regime != "unknown").any()
    # The vol classifier drops the first bar (no return there), so the label
    # series is a subset of the price index — `assemble` fills the gap with
    # "unknown" rather than guessing.
    assert regime.index.isin(bench.index).all()
    assert bench.index.difference(regime.index).tolist() == [bench.index[0]]
