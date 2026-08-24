# pyright: strict, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Append-only ledger of every weekly selection, written before the outcome (WP4).

The point of this file is uncomfortable on purpose: it records what the system
said **before** the market answered, so a future reader can score it without
taking anyone's word for it. A track record assembled after the fact is not a
track record, and every honest-looking backtest in this repo exists because
someone could still cheat on the dates. Here they cannot: a row is written at
emission time, and the only field that may ever change afterwards is
``outcome``, once, when the horizon has actually matured.

Storage is JSONL under ``data/predictions/`` — one small line per
``(emitted_at, asset, horizon)``, committed to git. Parquet would be smaller and
would rewrite the whole blob on every append (ADR-033's lesson); a JSONL line is
a diff of one line, and the git history itself becomes part of the audit trail.

**No calibrated probabilities here** (ADR-036). WP3 measured the calibration as
failing out of sample — the logistic predicts 0,974 where 0,461 happens — so
under a non-predictive rule the forecast fields (``probability_outperform``,
``expected_excess_return``, ``expected_volatility``) stay ``null`` and a
validator *refuses* a non-null value when ``predictive`` is ``False``. Writing
an uncalibrated number into a field called "probability" is the single most
misleading thing this system could do, so the schema makes it impossible rather
than merely discouraged.

What the ledger records instead is the observed state the rule actually used:
the selection score, the rank inside the universe, the realised 60-session
volatility. Those are facts about the past, and they are named as such.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_LEDGER_PATH = Path("data/predictions/etf_ranking.jsonl")

#: Identity of a row, as the plan specifies it.
KEY_FIELDS = ("emitted_at", "asset", "horizon_days")
#: The stronger identity actually enforced: you may not predict the same bar twice.
#: A cron retry three hours later carries a new ``emitted_at`` but the same data
#: cutoff, and two rows about one bar would let a later reader pick the flattering
#: one. Duplicate on *either* key is refused, so this is a superset of KEY_FIELDS.
CUTOFF_KEY_FIELDS = ("data_cutoff", "asset", "horizon_days")

ConfidenceLevel = Literal["low", "medium", "high", "not_applicable"]


class Factor(BaseModel):
    """One driver of a selection, with the direction it pushed in."""

    model_config = ConfigDict(extra="forbid")

    name: str
    direction: Literal["positive", "negative", "neutral"]
    value: float | None = None


class Outcome(BaseModel):
    """What actually happened over the horizon. Written once, never revised."""

    model_config = ConfigDict(extra="forbid")

    resolved_at: str
    resolved_price_date: str
    asset_return: float
    benchmark_return: float
    excess_return: float
    outperformed: bool


class Prediction(BaseModel):
    """One row: what was said about one asset, at one moment, for one horizon.

    ``emitted_at`` is when the decision was taken and ``data_cutoff`` the last
    bar it could see — two separate timestamps because conflating them is how
    look-ahead sneaks into a ledger that looks rigorous.

    ``predictive`` is the flag that governs the whole schema. Under the
    non-predictive fallback of ADR-034/036 it is ``False``, and then the three
    forecast fields must be ``None``: the model validator enforces it, so a
    future caller cannot quietly start writing uncalibrated probabilities.
    """

    model_config = ConfigDict(extra="forbid")

    emitted_at: str
    data_cutoff: str
    model_version: str
    dataset_version: str
    asset: str
    ticker: str | None = None
    benchmark: str
    horizon_days: int = Field(gt=0)

    # --- the honesty switch -------------------------------------------------
    predictive: bool = False
    rule: str
    non_predictive_reason: str | None = None

    # --- forecast fields: null unless a model passed the adoption bar --------
    probability_outperform: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_excess_return: float | None = None
    expected_volatility: float | None = Field(default=None, ge=0.0)
    confidence: ConfidenceLevel = "not_applicable"

    # --- observed state the rule actually used (facts, not forecasts) -------
    selection_score: float | None = None
    selection_rank: int | None = Field(default=None, gt=0)
    universe_size: int | None = Field(default=None, gt=0)
    realized_vol_60: float | None = Field(default=None, ge=0.0)
    selected: bool = False
    target_weight: float = Field(default=0.0, ge=0.0, le=1.0)
    regime: str = "unknown"
    top_factors: list[Factor] = Field(default_factory=list)

    outcome: Outcome | None = None

    @model_validator(mode="after")
    def _forbid_uncalibrated_forecasts(self) -> Prediction:
        """A non-predictive rule may not fill the forecast fields (ADR-036).

        This is the guard rail, not a style preference: the calibration failed
        out of sample, so any number placed in these fields would be presented
        as reliable while being measurably worse than a constant.
        """
        if self.predictive:
            return self
        offenders = [
            name
            for name in ("probability_outperform", "expected_excess_return", "expected_volatility")
            if getattr(self, name) is not None
        ]
        if offenders:
            raise ValueError(
                "non-predictive rule cannot carry forecast fields "
                f"{sorted(offenders)} (ADR-036): use selection_score / "
                "realized_vol_60 for observed state"
            )
        if self.confidence != "not_applicable":
            raise ValueError(
                "non-predictive rule cannot claim a confidence level (ADR-036): "
                f"got {self.confidence!r}, expected 'not_applicable'"
            )
        return self

    def key(self) -> tuple[str, str, int]:
        """Identity used for idempotent appends (emission time)."""
        return (self.emitted_at, self.asset, self.horizon_days)

    def cutoff_key(self) -> tuple[str, str, int]:
        """Identity by decision bar: one prediction per bar, per asset, per horizon."""
        return (self.data_cutoff, self.asset, self.horizon_days)

    def to_record(self) -> dict[str, Any]:
        """JSON-ready dict, with ``None`` preserved (a missing value is data)."""
        return self.model_dump(mode="json")


def _key_of(record: dict[str, Any]) -> tuple[str, str, int]:
    return (str(record["emitted_at"]), str(record["asset"]), int(record["horizon_days"]))


def _cutoff_key_of(record: dict[str, Any]) -> tuple[str, str, int]:
    return (str(record["data_cutoff"]), str(record["asset"]), int(record["horizon_days"]))


class PredictionLedger:
    """Append-only JSONL ledger with a single-writer, idempotent contract.

    Reads return raw dicts as well as parsed models: ``backfill_outcomes``
    rewrites the file from the **raw** dicts and touches only the ``outcome``
    key, so no round-trip through the schema can silently reshape a row that
    was written months ago under an older field set.
    """

    def __init__(self, path: str | Path = DEFAULT_LEDGER_PATH) -> None:
        self.path = Path(path)

    # -- reading -----------------------------------------------------------

    def raw_records(self) -> list[dict[str, Any]]:
        """Every line as a plain dict, in file order. Missing file -> empty."""
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parsed = json.loads(stripped)
            if not isinstance(parsed, dict):
                raise ValueError(f"corrupt ledger line in {self.path}: {stripped[:80]!r}")
            records.append(cast("dict[str, Any]", parsed))
        return records

    def read(self) -> list[Prediction]:
        """Parsed rows. Raises on a row the current schema cannot validate."""
        return [Prediction.model_validate(r) for r in self.raw_records()]

    def frame(self) -> pd.DataFrame:
        """The ledger as a flat frame (reporting convenience, not the source)."""
        records = self.raw_records()
        if not records:
            return pd.DataFrame()
        return pd.json_normalize(records)

    # -- writing -----------------------------------------------------------

    def append(self, predictions: list[Prediction]) -> int:
        """Append rows whose keys are not already present; returns how many landed.

        Idempotent by ``(emitted_at, asset, horizon_days)`` **and** by
        ``(data_cutoff, asset, horizon_days)``. The second key is what a cron
        actually needs: a retry two hours later stamps a new ``emitted_at`` but
        still refers to the same decision bar, and recording that twice would
        leave a future reader two versions of one prediction to choose between.

        An existing row is **never** overwritten — a second opinion about the
        same moment would erase the first one, which is the whole thing this
        ledger exists to prevent.
        """
        if not predictions:
            return 0
        stored = self.raw_records()
        existing = {_key_of(r) for r in stored}
        existing_cutoffs = {_cutoff_key_of(r) for r in stored}
        fresh: list[Prediction] = []
        seen: set[tuple[str, str, int]] = set()
        seen_cutoffs: set[tuple[str, str, int]] = set()
        for pred in predictions:
            key, cutoff_key = pred.key(), pred.cutoff_key()
            if key in existing or key in seen:
                continue
            if cutoff_key in existing_cutoffs or cutoff_key in seen_cutoffs:
                continue
            seen.add(key)
            seen_cutoffs.add(cutoff_key)
            fresh.append(pred)
        if not fresh:
            return 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            for pred in fresh:
                fh.write(json.dumps(pred.to_record(), ensure_ascii=False, sort_keys=True) + "\n")
        return len(fresh)

    # -- outcomes ----------------------------------------------------------

    def backfill_outcomes(
        self,
        closes: dict[str, pd.Series],
        benchmark: pd.Series,
        now: pd.Timestamp | None = None,
    ) -> int:
        """Resolve rows whose horizon has matured; returns how many were resolved.

        ``closes`` maps the ledger's ``asset`` symbols to close series and
        ``benchmark`` is the benchmark close series, both indexed by date and
        covering the emission date plus ``horizon_days`` **sessions** after it.

        A row is resolved only when the price series actually contains
        ``horizon_days`` bars after the data cutoff. Not enough bars means the
        future has not happened yet, and an unmatured horizon is left ``null``
        rather than scored against whatever the last available bar happens to
        be — the mistake that turns a ledger into a performance brochure.

        Rows already carrying an outcome are never touched again, and every
        other field is copied through verbatim from the stored dict.
        """
        records = self.raw_records()
        if not records:
            return 0
        ref = now if now is not None else pd.Timestamp.now(tz="UTC")
        if ref.tzinfo is None:
            ref = ref.tz_localize("UTC")

        resolved = 0
        for record in records:
            if record.get("outcome") is not None:
                continue
            asset = str(record["asset"])
            series = closes.get(asset)
            if series is None:
                continue
            cutoff = pd.Timestamp(str(record["data_cutoff"]))
            if cutoff is pd.NaT:
                raise ValueError(f"corrupt data_cutoff in ledger row: {record['data_cutoff']!r}")
            outcome = _resolve_outcome(
                asset_close=series,
                benchmark_close=benchmark,
                cutoff=cast("pd.Timestamp", cutoff),
                horizon_days=int(record["horizon_days"]),
                resolved_at=ref,
            )
            if outcome is None:
                continue
            record["outcome"] = outcome.model_dump(mode="json")
            resolved += 1

        if resolved:
            self._rewrite(records)
        return resolved

    def _rewrite(self, records: list[dict[str, Any]]) -> None:
        """Rewrite the file from raw dicts (only ``outcome`` may have changed)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records
        )
        self.path.write_text(payload, encoding="utf-8")


def _normalize_index(series: pd.Series) -> pd.Series:
    """Sorted, tz-aware (UTC) copy of a close series."""
    out = series.dropna().sort_index()
    idx = pd.DatetimeIndex(out.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    return pd.Series(out.to_numpy(dtype="float64"), index=idx, name=series.name)


def _resolve_outcome(
    asset_close: pd.Series,
    benchmark_close: pd.Series,
    cutoff: pd.Timestamp,
    horizon_days: int,
    resolved_at: pd.Timestamp,
) -> Outcome | None:
    """Realised excess return over ``horizon_days`` sessions after ``cutoff``.

    Returns ``None`` while the horizon is unmatured — for either leg. The
    benchmark matters as much as the asset here: an excess return computed
    against a benchmark bar that does not exist yet would be pure invention.
    """
    asset = _normalize_index(asset_close)
    bench = _normalize_index(benchmark_close)
    cut = cutoff if cutoff.tzinfo is not None else cutoff.tz_localize("UTC")

    asset_start = _value_at_or_before(asset, cut)
    bench_start = _value_at_or_before(bench, cut)
    if asset_start is None or bench_start is None:
        return None

    asset_end = _value_n_sessions_after(asset, cut, horizon_days)
    bench_end = _value_n_sessions_after(bench, cut, horizon_days)
    if asset_end is None or bench_end is None:
        return None

    asset_ret = asset_end[1] / asset_start - 1.0
    bench_ret = bench_end[1] / bench_start - 1.0
    excess = asset_ret - bench_ret
    # Both legs matured; date the outcome by the later of the two closing bars.
    price_date = max(asset_end[0], bench_end[0])
    return Outcome(
        resolved_at=resolved_at.isoformat(),
        resolved_price_date=price_date.isoformat(),
        asset_return=float(asset_ret),
        benchmark_return=float(bench_ret),
        excess_return=float(excess),
        outperformed=bool(excess > 0.0),
    )


def _value_at_or_before(series: pd.Series, ts: pd.Timestamp) -> float | None:
    """Last observed value at or before ``ts`` (the price the decision saw)."""
    window = series.loc[series.index <= ts]
    return float(cast("float", window.iloc[-1])) if len(window) else None


def _value_n_sessions_after(
    series: pd.Series, ts: pd.Timestamp, n: int
) -> tuple[pd.Timestamp, float] | None:
    """The ``n``-th bar strictly after ``ts``, or ``None`` if it has not happened."""
    future = series.loc[series.index > ts]
    if len(future) < n:
        return None
    return (cast("pd.Timestamp", future.index[n - 1]), float(cast("float", future.iloc[n - 1])))
