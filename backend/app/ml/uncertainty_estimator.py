"""
uncertainty_estimator.py — AnemiaLens v6 prediction uncertainty module.

Provides conformal-prediction-style interval estimates and ensemble
disagreement scores that can be used to:
  1. Flag borderline predictions for human review ("uncertain case").
  2. Gate automated decisions — only act automatically when uncertainty is low.
  3. Report calibrated confidence intervals to end-users / clinicians.

Design
------
We use *inductive conformal prediction* (split-conformal) over the stacked
ensemble.  During retraining, a calibration set (held-out fold) is scored, and
the residuals are stored.  At inference time, we look up the appropriate
quantile to form Hb prediction intervals.

Additionally, we compute an *ensemble disagreement score* — the spread between
the ExtraTrees and XGBoost base-learner predictions.  High disagreement on a
sample indicates the feature space is sparse near this point, so predictions
should be treated with caution.

Classes
-------
UncertaintyEstimator
    Fitted at training time; serialised into the model artifact.

Usage (inference)
-----------------
    ue = artifact["uncertainty_estimator"]
    result = ue.estimate(
        row_matrix,              # shape (1, n_features) float32
        stacked_reg,             # StackedRegressor
        stacked_clf,             # StackedClassifier
        hb_pred=12.3,            # final Hb prediction
        blend_score=0.61,        # final risk blend score
    )
    # result.uncertainty_level  ∈ {"low", "moderate", "high"}
    # result.hb_interval        → (hb_lower, hb_upper) at configured coverage
    # result.ensemble_disagreement → float [0, 1]
    # result.confidence_pct     → int  e.g. 78
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from app.ml.stacked_model import StackedClassifier, StackedRegressor


# ─────────────────────────────────────────────────────────────────────────────
# Public result type
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class UncertaintyResult:
    """Uncertainty diagnostics for a single inference call."""
    uncertainty_level: str          # "low" | "moderate" | "high"
    hb_interval: tuple[float, float]  # (lower, upper) Hb g/dL
    ensemble_disagreement: float    # [0, 1] — spread between base learners
    confidence_pct: int             # integer percentage, 0-100
    flag_for_review: bool           # True when human review is recommended
    details: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Estimator
# ─────────────────────────────────────────────────────────────────────────────

class UncertaintyEstimator:
    """
    Conformal + ensemble-disagreement based uncertainty estimator.

    Fitting
    -------
    Call :meth:`fit_calibration` with held-out (calibration) set residuals
    once after training the stacked ensemble.

    Inference
    ---------
    Call :meth:`estimate` to obtain an :class:`UncertaintyResult` for a
    single sample.

    Parameters
    ----------
    coverage : float
        Desired conformal coverage level (e.g. 0.90 for 90% intervals).
        Determines the α quantile of stored residuals.
    review_threshold : float
        ensemble_disagreement above this value → flag for human review.
    """

    def __init__(
        self,
        coverage: float = 0.90,
        review_threshold: float = 0.35,
    ) -> None:
        self.coverage = coverage
        self.review_threshold = review_threshold
        # Calibration residuals (|true_hb - predicted_hb|) for conformal PI
        self._residuals: np.ndarray | None = None
        # Calibration blend scores for probability interval
        self._blend_residuals: np.ndarray | None = None
        self._q_hb: float = 2.0        # quantile from residuals (default wide)
        self._q_blend: float = 0.20    # quantile from blend residuals

    # ----------------------------------------------------------------- fit --

    def fit_calibration(
        self,
        true_hb: np.ndarray,
        pred_hb: np.ndarray,
        true_labels: np.ndarray,
        blend_scores: np.ndarray,
    ) -> "UncertaintyEstimator":
        """
        Fit calibration set.

        Parameters
        ----------
        true_hb : (n,) float — ground-truth Hb values on held-out set
        pred_hb : (n,) float — ensemble Hb predictions on same set
        true_labels : (n,) int — 0/1 anemia labels
        blend_scores : (n,) float — final blend scores on held-out set
        """
        self._residuals = np.abs(true_hb - pred_hb)
        self._q_hb = float(np.quantile(self._residuals, self.coverage))
        # For blend: calibrate as absolute deviation from 0 (non-anemic) or
        # 1 (anemic) depending on true label → measures calibration gap
        target_blend = true_labels.astype(float)
        blend_res = np.abs(blend_scores - target_blend)
        self._blend_residuals = blend_res
        self._q_blend = float(np.quantile(blend_res, self.coverage))
        return self

    # ------------------------------------------------------------- estimate --

    def estimate(
        self,
        row: np.ndarray,
        stacked_reg: "StackedRegressor",
        stacked_clf: "StackedClassifier",
        hb_pred: float,
        blend_score: float,
    ) -> UncertaintyResult:
        """
        Compute uncertainty diagnostics for a single inference row.

        Parameters
        ----------
        row : np.ndarray shape (1, n_features)
        stacked_reg : fitted StackedRegressor
        stacked_clf : fitted StackedClassifier
        hb_pred : float — final Hb prediction (already computed)
        blend_score : float — final risk blend score

        Returns
        -------
        UncertaintyResult
        """
        q_hb = self._q_hb if self._q_hb is not None else 2.0

        # ── Conformal Hb interval ────────────────────────────────────────────
        hb_lower = round(max(0.0, hb_pred - q_hb), 2)
        hb_upper = round(hb_pred + q_hb, 2)
        hb_width = q_hb * 2.0

        # ── Ensemble disagreement ────────────────────────────────────────────
        disagreement = self._ensemble_disagreement(row, stacked_reg, stacked_clf)

        # ── Uncertainty level ────────────────────────────────────────────────
        #  Two signals: (1) interval width relative to clinical threshold,
        #  (2) ensemble disagreement.
        # A wide interval (> 3 g/dL) OR high disagreement (> 0.45) → high.
        # Moderate: interval 1.5-3 g/dL OR disagreement 0.20-0.45.
        # Low: otherwise.
        if hb_width > 3.0 or disagreement > 0.45:
            level = "high"
        elif hb_width > 1.5 or disagreement > 0.20:
            level = "moderate"
        else:
            level = "low"

        # ── Confidence percentage ───────────────────────────────────────────
        # Mapping: low→85-95%, moderate→65-84%, high→40-64%
        # Use disagreement and interval width as continuous modifiers.
        base_conf = {"low": 90, "moderate": 75, "high": 50}[level]
        penalty = int(disagreement * 20) + max(0, int((hb_width - 1.5) * 5))
        confidence_pct = max(30, min(98, base_conf - penalty))

        flag = (
            level == "high"
            or disagreement > self.review_threshold
            or (level == "moderate" and abs(blend_score - 0.5) < 0.12)
        )

        return UncertaintyResult(
            uncertainty_level=level,
            hb_interval=(hb_lower, hb_upper),
            ensemble_disagreement=round(float(disagreement), 4),
            confidence_pct=confidence_pct,
            flag_for_review=flag,
            details={
                "conformal_q_hb": round(q_hb, 3),
                "hb_interval_width": round(hb_width, 3),
                "coverage_target": self.coverage,
                "calibration_n": (
                    int(len(self._residuals)) if self._residuals is not None else 0
                ),
            },
        )

    # ------------------------------------------------------ private helpers --

    @staticmethod
    def _ensemble_disagreement(
        row: np.ndarray,
        stacked_reg: "StackedRegressor",
        stacked_clf: "StackedClassifier",
    ) -> float:
        """
        Compute normalised disagreement between ET and XGB base learners.

        For regression: (|et_hb - xgb_hb|) / 5.0  (5 g/dL = large gap)
        For classification: |et_prob - xgb_prob|
        Returns the mean of both signals, clipped to [0, 1].
        """
        try:
            et_reg = stacked_reg.et_reg
            xgb_reg = stacked_reg.xgb_reg
            et_clf = stacked_clf.et_clf
            xgb_clf = stacked_clf.xgb_clf

            et_hb = float(et_reg.predict(row)[0])
            xgb_hb = (
                float(xgb_reg.predict(row)[0]) if xgb_reg is not None else et_hb
            )
            reg_disagree = abs(et_hb - xgb_hb) / 5.0

            et_p = float(et_clf.predict_proba(row)[0, 1])
            xgb_p = (
                float(xgb_clf.predict_proba(row)[0, 1])
                if xgb_clf is not None
                else et_p
            )
            clf_disagree = abs(et_p - xgb_p)

            return float(np.clip((reg_disagree + clf_disagree) / 2.0, 0.0, 1.0))
        except Exception:
            return 0.5  # conservative fallback: moderate uncertainty

    # ─────────────────────────────────────────────────────── serialisation ──

    def __repr__(self) -> str:
        n = len(self._residuals) if self._residuals is not None else 0
        return (
            f"UncertaintyEstimator("
            f"coverage={self.coverage}, q_hb={self._q_hb:.3f}, "
            f"calibration_n={n})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Convenience helper to fit from training output
# ─────────────────────────────────────────────────────────────────────────────

def build_uncertainty_estimator(
    true_hb: np.ndarray,
    pred_hb: np.ndarray,
    true_labels: np.ndarray,
    blend_scores: np.ndarray,
    coverage: float = 0.90,
) -> UncertaintyEstimator:
    """
    Build and calibrate an UncertaintyEstimator from held-out predictions.

    Parameters
    ----------
    true_hb : ground-truth Hb values (held-out calibration set)
    pred_hb : stacked regressor Hb predictions on those samples
    true_labels : 0/1 anemia labels
    blend_scores : final risk blend scores on those samples
    coverage : conformal coverage target (default 0.90)
    """
    ue = UncertaintyEstimator(coverage=coverage)
    ue.fit_calibration(true_hb, pred_hb, true_labels, blend_scores)
    return ue
