from __future__ import annotations

from typing import Dict, List, Optional

from chaos_negotiator.models import DeploymentContext, RiskAssessment
from chaos_negotiator.models.outcome import DeploymentOutcome

from .ml_predictor import MLRiskPredictor
from .risk_predictor import RiskPredictor
from .history_store import DeploymentHistoryStore


class EnsembleRiskPredictor:
    """Combine heuristic risk prediction with an ML model.

    The result is produced as a :class:`RiskAssessment`, so it can be
    dropped into existing code paths without any change.  The ML score is
    expressed on the same 0–100 scale as the heuristic prediction and the
    two are averaged according to the weights provided.

    The reasoning string is augmented with a breakdown of the individual
    scores so users can see what influenced the final number.
    """

    def __init__(
        self,
        heuristic_weight: float = 0.6,
        ml_weight: float = 0.4,
        history_store: Optional[DeploymentHistoryStore] = None,
    ) -> None:
        self.heuristic = RiskPredictor()
        self.ml = MLRiskPredictor()

        # allow ops teams to tune weights without redeploying
        import os

        self.heuristic_weight = float(
            os.getenv("CN_HEURISTIC_WEIGHT", heuristic_weight)
        )
        self.ml_weight = float(os.getenv("CN_ML_WEIGHT", ml_weight))

        # weights are kept between 0.1 and 0.9 to avoid collapse
        self.heuristic_weight = max(0.1, min(self.heuristic_weight, 0.9))
        self.ml_weight = max(0.1, min(self.ml_weight, 0.9))

        # optional persistent store for outcomes
        self.history_store = history_store or DeploymentHistoryStore()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _combine_scores(
        self, heuristic: float, ml: float
    ) -> float:  # both in 0-100 space
        return round(heuristic * self.heuristic_weight + ml * self.ml_weight, 2)

    def _determine_level(self, score: float) -> str:
        if score >= 70:
            return "critical"
        elif score >= 50:
            return "high"
        elif score >= 30:
            return "medium"
        else:
            return "low"

    def predict(self, context: DeploymentContext) -> RiskAssessment:
        """Return a combined risk assessment for the deployment context."""
        # first gather the heuristic assessment (contains reasoning, factors, etc.)
        h_assessment = self.heuristic.predict(context)

        # compute ml risk in 0-1 and convert to 0-100
        ml_score = self.ml.predict(context) * 100

        # remember the heuristic score before we overwrite it
        h_score = h_assessment.risk_score
        final_score = self._combine_scores(h_score, ml_score)

        h_assessment.risk_score = final_score
        h_assessment.risk_level = self._determine_level(final_score)

        # Confidence estimation
        # Agreement-based: predictors closer together -> higher confidence
        agreement = 1.0 - abs(h_score - ml_score) / 100.0

        # Historical calibration (lower mean error -> higher calibration)
        calibration = 0.5
        try:
            if self.history_store:
                recent = self.history_store.recent(50)
                if recent:
                    errs = []
                    for o in recent:
                        actual = o.actual_error_rate_percent * 100
                        errs.append(abs(o.final_score - actual))
                    mean_err = sum(errs) / len(errs)
                    # map mean_err (0..100) to calibration (1..0) with a soft cap
                    calibration = max(0.0, min(1.0, 1.0 - (mean_err / 50.0)))
        except Exception:
            calibration = 0.5

        # combine signals: agreement (60%), heuristic baseline (20%), calibration (20%)
        baseline_conf = max(0.0, min(100.0, h_assessment.confidence_percent)) / 100.0
        conf_score = (agreement * 0.6) + (baseline_conf * 0.2) + (calibration * 0.2)
        h_assessment.confidence_percent = round(conf_score * 100.0, 2)

        # append breakdown info to reasoning
        breakdown = (
            f"\n[Ensemble] heuristic={h_score:.1f}, "
            f"ml={ml_score:.1f} → final={final_score:.1f}; "
            f"confidence={h_assessment.confidence_percent:.1f}%"
        )
        h_assessment.reasoning = (h_assessment.reasoning or "") + breakdown

        return h_assessment

    # --------------------------------------------------------------
    # learning helpers
    # --------------------------------------------------------------
    def record_outcome(self, outcome: DeploymentOutcome) -> None:
        """Record a deployment outcome for later analysis."""
        if self.history_store:
            self.history_store.save(outcome)

    def tune_weights(self, recent: int = 100) -> None:
        """Adjust weights based on historical accuracy.

        A very simple algorithm is used: compute the average error of the
        heuristic and ML predictors compared to a notional "actual" score,
        then shift the weights proportionally.  This keeps the system
        learning from real deployments without requiring an external
        training pipeline.
        """
        if not self.history_store:
            return

        outcomes: List[DeploymentOutcome] = self.history_store.recent(recent)
        if not outcomes:
            return

        total_h_err = 0.0
        total_ml_err = 0.0
        for o in outcomes:
            # assume actual risk correlates with error-rate percentage;
            # if more sophisticated metrics become available the mapping
            # can be replaced.
            actual_score = o.actual_error_rate_percent * 100
            total_h_err += abs(o.heuristic_score - actual_score)
            total_ml_err += abs(o.ml_score - actual_score)

        # avoid division by zero
        if total_h_err + total_ml_err == 0:
            return

        # inverse error weighting
        new_h = total_ml_err / (total_h_err + total_ml_err)
        new_ml = total_h_err / (total_h_err + total_ml_err)

        # clamp to safe bounds
        self.heuristic_weight = max(0.1, min(new_h, 0.9))
        self.ml_weight = max(0.1, min(new_ml, 0.9))
