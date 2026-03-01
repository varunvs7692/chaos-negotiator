from __future__ import annotations

import math
from typing import List

from chaos_negotiator.models import DeploymentContext


class MLRiskPredictor:
    """Simple ML-style risk predictor.

    This class is designed to be a lightweight stand‑in for a real
    machine‑learning model.  It currently uses a handful of hand‑tuned
    weights over features extracted from the deployment context, then
    applies a sigmoid to map the raw score into a 0‑1 range.  Later this
    can be replaced with an actual trained model without changing any of
    the surrounding code.
    """

    def __init__(self) -> None:
        # initial feature weights; can be adjusted or learned later
        self.weights = {
            # normalized by the caps used in _extract_features
            "num_changes": 0.30,
            "total_lines": 0.25,
            "db_migration": 0.25,
            "api_changes": 0.20,
        }
        self.bias = 0.05

    # ------------------------------------------------------------------
    # feature engineering
    # ------------------------------------------------------------------
    def _extract_features(self, context: DeploymentContext) -> List[float]:
        """Convert the deployment context into a fixed‑length feature vector."""
        num_changes = len(context.changes)
        total_lines = (
            context.total_lines_changed
            or sum(c.lines_changed for c in context.changes)
        )

        # simple heuristics to detect certain risky change types
        descs = " ".join(c.description.lower() for c in context.changes)
        has_db = "migration" in descs or "db" in descs
        has_api = "api" in descs or "endpoint" in descs

        return [
            min(num_changes / 10, 1.0),
            min(total_lines / 1000, 1.0),
            1.0 if has_db else 0.0,
            1.0 if has_api else 0.0,
        ]

    # ------------------------------------------------------------------
    # utility
    # ------------------------------------------------------------------
    def _sigmoid(self, x: float) -> float:
        return 1 / (1 + math.exp(-x))

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def predict(self, context: DeploymentContext) -> float:
        """Return a risk score between 0.0 and 1.0 for the given context."""
        features = self._extract_features(context)
        weight_vec = [
            self.weights["num_changes"],
            self.weights["total_lines"],
            self.weights["db_migration"],
            self.weights["api_changes"],
        ]

        raw = sum(f * w for f, w in zip(features, weight_vec)) + self.bias
        return round(self._sigmoid(raw), 4)
