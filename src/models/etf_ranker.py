# pyright: strict, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Cross-sectional ranking models for the ETF panel (WP3, ADR-034).

The question is relative, not absolute: *which* sector ETFs beat SPY over the
next h sessions, not whether the market goes up. So every model here consumes a
single day's cross-section and returns one score per symbol; the score's absolute
level is meaningless, only the ordering and (where available) the probability are.

Four models plus two negative controls, all behind one ``RankerModel`` interface
so the runner can treat them interchangeably:

- ``MomentumRanker`` — rank on ``rel_ret_60``, no fitting. The pre-registered H1
  baseline, and the honest thing to beat: a rule this simple needs no training
  data and cannot overfit.
- ``LogisticRanker`` — L2 logistic regression on the WP2 features, standardised
  on the **train fold only**. The H2 candidate.
- ``RidgeRanker`` — L2 regression on the excess return itself, ranked. Predicts
  magnitude rather than sign, which is a different bet on the same features.
- ``RandomRanker(seed)`` and ``ClimatologyBaseline`` — the controls. A model that
  cannot beat a seeded coin flip has not earned a comparison with the others,
  and the climatology (train-set frequency of outperformance) is the constant
  predictor that any claimed probabilistic skill must improve on.

Design constraints that are not negotiable here:

- **Fit sees train only.** Scalers, coefficients and the climatology rate are all
  estimated inside ``fit``; ``predict_proba`` never re-fits. This is what makes
  the walk-forward honest, and it is asserted in the tests.
- **Deterministic.** Same data plus same seed gives the same numbers, so a result
  can be reproduced rather than re-rolled.
- **No boosting, no deep learning** (decision D11): logistic/ridge/isotonic are
  already in scikit-learn, and a stronger learner on features that have not yet
  shown an edge would only make the overfitting easier to hide.

NaN handling: a row whose features are not yet defined (warm-up, short history)
is *not* imputed. Imputing would invent data precisely where the panel is honest
about not having any. Rows with missing features are dropped from ``fit`` and
receive NaN from ``predict_proba``, which the metrics then skip.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import cast

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler


class RankerModel(ABC):
    """One day's cross-section in, one score per row out.

    ``fit`` estimates every parameter from the training fold. ``predict_proba``
    returns a probability of outperformance in ``[0, 1]`` (NaN where features are
    missing); ``rank`` turns those into within-date percentile ranks.
    """

    name: str = "ranker"
    #: Whether ``predict_proba`` output is a genuine probability (vs a rank proxy).
    calibratable: bool = True

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series) -> RankerModel:
        """Estimate parameters from the training fold. Returns self."""

    @abstractmethod
    def predict_proba(self, X: pd.DataFrame) -> pd.Series:
        """Probability of outperformance per row, indexed like ``X``."""

    def rank(self, X: pd.DataFrame, dates: pd.Series) -> pd.Series:
        """Within-date percentile rank of ``predict_proba``, in ``[0, 1]``.

        ``dates`` labels the cross-section each row belongs to. Ranking per date
        is what makes the output a *cross-sectional* signal: comparing scores
        across days would mix regimes.
        """
        scores = self.predict_proba(X)
        frame = pd.DataFrame({"score": scores.to_numpy(), "date": dates.to_numpy()})
        ranked = frame.groupby("date")["score"].rank(pct=True, method="average")
        return pd.Series(ranked.to_numpy(), index=X.index, name="rank")


def _finite_mask(X: pd.DataFrame) -> pd.Series:
    """Rows whose features are all present and finite."""
    values = X.to_numpy(dtype="float64")
    return pd.Series(np.isfinite(values).all(axis=1), index=X.index)


class MomentumRanker(RankerModel):
    """Rank on a single momentum column. No parameters, nothing to fit (H1).

    The probability it reports is the within-date percentile rank of the momentum
    column, which is a *monotone* stand-in for a probability, not a calibrated
    one — hence ``calibratable = True`` is still meaningful: the isotonic step
    downstream is precisely what turns this ordering into a usable probability.
    """

    name = "momentum"

    def __init__(self, column: str = "rel_ret_60") -> None:
        self.column = column

    def fit(self, X: pd.DataFrame, y: pd.Series) -> MomentumRanker:
        return self

    def predict_proba(self, X: pd.DataFrame) -> pd.Series:
        col = cast("pd.Series", X[self.column]).astype("float64")
        # Percentile rank over the whole block; the runner ranks per date after.
        ranked = col.rank(pct=True, method="average")
        return pd.Series(ranked.to_numpy(), index=X.index, name="proba")


class LogisticRanker(RankerModel):
    """L2 logistic regression on the WP2 features (H2 candidate).

    Features are standardised with a scaler fit on the training fold only, then
    the regression predicts P(outperform). ``C`` is left at a deliberately
    conservative default rather than tuned: tuning it against the same test set
    the model is judged on is the classic way to manufacture an edge that does
    not exist, and the plan forbids iterative tuning on one test (WP3, "non fare").
    """

    name = "logistic"

    def __init__(self, features: list[str], C: float = 0.1, seed: int = 0) -> None:
        self.features = list(features)
        self.C = C
        self.seed = seed
        self._scaler: StandardScaler | None = None
        self._model: LogisticRegression | None = None
        self._fallback: float = 0.5

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LogisticRanker:
        block = cast("pd.DataFrame", X[self.features])
        ok = _finite_mask(block) & y.notna()
        Xt = block[ok].to_numpy(dtype="float64")
        yt = cast("pd.Series", y[ok]).to_numpy(dtype="float64")
        self._fallback = float(yt.mean()) if yt.size else 0.5
        # A fold with one class present carries no discriminative information:
        # fall back to the base rate rather than fitting a degenerate model.
        if yt.size == 0 or len(np.unique(yt)) < 2:
            self._scaler, self._model = None, None
            return self
        scaler = StandardScaler().fit(Xt)
        # l1_ratio=0 is pure L2; `penalty=` is deprecated from sklearn 1.8.
        model = LogisticRegression(
            C=self.C, l1_ratio=0.0, solver="lbfgs", max_iter=2000, random_state=self.seed
        )
        model.fit(scaler.transform(Xt), yt)
        self._scaler, self._model = scaler, model
        return self

    def predict_proba(self, X: pd.DataFrame) -> pd.Series:
        block = cast("pd.DataFrame", X[self.features])
        out = pd.Series(np.nan, index=X.index, name="proba", dtype="float64")
        if self._model is None or self._scaler is None:
            ok = _finite_mask(block)
            out[ok] = self._fallback
            return out
        ok = _finite_mask(block)
        if not bool(ok.any()):
            return out
        Xt = self._scaler.transform(block[ok].to_numpy(dtype="float64"))
        proba = cast("np.ndarray", self._model.predict_proba(Xt))[:, 1]
        out[ok] = proba
        return out


class RidgeRanker(RankerModel):
    """L2 regression on the excess return, ranked (magnitude rather than sign).

    The predicted excess return is mapped to ``[0, 1]`` by percentile rank, so it
    plugs into the same interface. That mapping is monotone, so the IC is
    unaffected; the isotonic step supplies the probability.
    """

    name = "ridge"

    def __init__(self, features: list[str], alpha: float = 10.0) -> None:
        self.features = list(features)
        self.alpha = alpha
        self._scaler: StandardScaler | None = None
        self._model: Ridge | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RidgeRanker:
        block = cast("pd.DataFrame", X[self.features])
        ok = _finite_mask(block) & y.notna()
        Xt = block[ok].to_numpy(dtype="float64")
        yt = cast("pd.Series", y[ok]).to_numpy(dtype="float64")
        if yt.size == 0:
            self._scaler, self._model = None, None
            return self
        scaler = StandardScaler().fit(Xt)
        model = Ridge(alpha=self.alpha)
        model.fit(scaler.transform(Xt), yt)
        self._scaler, self._model = scaler, model
        return self

    def predict_proba(self, X: pd.DataFrame) -> pd.Series:
        block = cast("pd.DataFrame", X[self.features])
        out = pd.Series(np.nan, index=X.index, name="proba", dtype="float64")
        if self._model is None or self._scaler is None:
            return out
        ok = _finite_mask(block)
        if not bool(ok.any()):
            return out
        Xt = self._scaler.transform(block[ok].to_numpy(dtype="float64"))
        pred = pd.Series(cast("np.ndarray", self._model.predict(Xt)), index=block[ok].index)
        out[ok] = pred.rank(pct=True, method="average")
        return out


class RandomRanker(RankerModel):
    """Seeded random scores — the control that says what luck looks like.

    Deterministic given the seed and the number of rows, so a "beats random"
    claim is reproducible rather than a lucky draw.
    """

    name = "random"

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RandomRanker:
        return self

    def predict_proba(self, X: pd.DataFrame) -> pd.Series:
        rng = np.random.default_rng(self.seed)
        return pd.Series(rng.random(len(X)), index=X.index, name="proba")


class ClimatologyBaseline(RankerModel):
    """The constant predictor: the train-fold frequency of outperformance.

    It carries no cross-sectional information at all — every symbol gets the same
    number — which is exactly the point. In Brier score this is a genuinely hard
    baseline: a model that knows nothing but the base rate is already well
    calibrated, and beating it requires real discrimination, not just being
    roughly right on average.
    """

    name = "climatology"
    calibratable = False

    def __init__(self) -> None:
        self.rate: float = 0.5

    def fit(self, X: pd.DataFrame, y: pd.Series) -> ClimatologyBaseline:
        valid = y.dropna()
        self.rate = float(valid.mean()) if len(valid) else 0.5
        return self

    def predict_proba(self, X: pd.DataFrame) -> pd.Series:
        return pd.Series(self.rate, index=X.index, name="proba", dtype="float64")
