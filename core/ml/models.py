"""
DelValue AI — ML Model Definitions

Gradient-boosted scoring model with confidence calibration.
The model learns from real automation outcomes (predicted vs actual)
and improves its predictions over time — this is the data flywheel.

Architecture:
  1. Primary model: XGBoost/GradientBoosting for overall score prediction
  2. Calibration model: Isotonic regression for confidence calibration
  3. Residual model: Learns systematic biases from outcome data
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

try:
    import joblib
except ImportError:
    joblib = None

try:
    from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.isotonic import IsotonicRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from core.ml.features import FeatureVector, FEATURE_VERSION

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Output of the scoring model with uncertainty quantification."""

    # Core scores (0-1)
    overall_score: float
    feasibility_score: float
    value_score: float
    risk_score: float
    complexity_score: float

    # Financial predictions
    estimated_annual_savings: float
    estimated_implementation_cost: float
    estimated_roi: float
    estimated_payback_months: float

    # Confidence & uncertainty
    confidence: float
    prediction_interval_lower: float
    prediction_interval_upper: float

    # Classification
    recommendation: str
    automation_feasibility: str
    risk_level: str

    # Metadata
    model_version: str
    feature_vector: dict


class HeuristicScoringModel:
    """
    Heuristic scoring model — used when insufficient training data exists.
    Once enough outcome data accumulates (>50 traces), the ML model takes over.
    This ensures the system works from day one while improving with data.
    """

    VERSION = f"heuristic-{FEATURE_VERSION}"

    # Configurable weights — these are the defaults, orgs can customize
    DEFAULT_WEIGHTS = {
        "feasibility": 0.30,
        "value": 0.40,
        "risk": 0.20,
        "complexity": 0.10,
    }

    def __init__(self, weights: Optional[dict] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

    def predict(self, feature_vector: FeatureVector) -> PredictionResult:
        f = feature_vector.features

        # --- Feasibility Score ---
        feasibility = (
            0.30 * f["automation_readiness"]
            + 0.20 * f["structured_data_pct"]
            + 0.15 * f["doc_quality"]
            + 0.15 * f["sop_exists"]
            + 0.10 * (1.0 - f["decision_complexity"])
            + 0.10 * f["frequency_score"]
        )

        # --- Value Score ---
        # Normalize savings to 0-1 range using sigmoid
        savings = f["estimated_annual_savings"]
        savings_score = 1.0 / (1.0 + np.exp(-0.00002 * (savings - 100_000)))
        roi = f["estimated_roi"]
        roi_score = min(max(roi / 3.0, 0.0), 1.0)  # 300% ROI = max score
        value = (
            0.35 * savings_score
            + 0.25 * roi_score
            + 0.20 * f["pain_intensity"]
            + 0.10 * f["frequency_score"]
            + 0.10 * min(f["error_impact"] / 50_000, 1.0)
        )

        # --- Risk Score (lower = better, so invert for overall) ---
        risk = (
            0.25 * f["complexity_index"]
            + 0.20 * f["dependency_risk"]
            + 0.15 * f["stakeholder_complexity"]
            + 0.15 * f["category_risk"]
            + 0.15 * f["requires_judgment"]
            + 0.10 * (1.0 - f["doc_quality"])
        )

        # --- Complexity Score ---
        complexity = f["complexity_index"]

        # --- Overall Score ---
        overall = (
            self.weights["feasibility"] * feasibility
            + self.weights["value"] * value
            + self.weights["risk"] * (1.0 - risk)
            + self.weights["complexity"] * (1.0 - complexity)
        )
        overall = max(0.0, min(1.0, overall))

        # --- Financial estimates ---
        est_savings = f["estimated_annual_savings"]
        est_cost = f["estimated_impl_cost"]
        if est_cost > 0:
            est_roi = ((est_savings - est_cost) / est_cost) * 100
        else:
            est_roi = 0.0
        if est_savings > 0:
            est_payback = (est_cost / est_savings) * 12
        else:
            est_payback = 999.0

        # --- Confidence (heuristic — based on data completeness) ---
        data_completeness = np.mean([
            1.0 if f["doc_quality"] > 0 else 0.0,
            1.0 if f["annual_volume"] > 0 else 0.0,
            1.0 if f["num_systems"] > 0 else 0.0,
            1.0 if f["people_involved"] > 0 else 0.0,
            f["structured_data_pct"],
            f["sop_exists"],
        ])
        confidence = 0.40 + 0.40 * data_completeness  # range: 0.40 - 0.80

        # Uncertainty interval (wider with lower confidence)
        uncertainty_width = (1.0 - confidence) * 200  # percentage points
        pi_lower = max(est_roi - uncertainty_width, -100)
        pi_upper = est_roi + uncertainty_width

        # --- Classifications ---
        recommendation = self._classify_recommendation(overall, feasibility, risk)
        auto_feasibility = self._classify_feasibility(feasibility, complexity)
        risk_level = self._classify_risk(risk)

        return PredictionResult(
            overall_score=round(overall, 4),
            feasibility_score=round(feasibility, 4),
            value_score=round(value, 4),
            risk_score=round(risk, 4),
            complexity_score=round(complexity, 4),
            estimated_annual_savings=round(est_savings, 2),
            estimated_implementation_cost=round(est_cost, 2),
            estimated_roi=round(est_roi, 2),
            estimated_payback_months=round(est_payback, 1),
            confidence=round(confidence, 4),
            prediction_interval_lower=round(pi_lower, 2),
            prediction_interval_upper=round(pi_upper, 2),
            recommendation=recommendation,
            automation_feasibility=auto_feasibility,
            risk_level=risk_level,
            model_version=self.VERSION,
            feature_vector=feature_vector.to_dict(),
        )

    @staticmethod
    def _classify_recommendation(overall: float, feasibility: float, risk: float) -> str:
        if overall >= 0.75 and feasibility >= 0.6 and risk < 0.5:
            return "automate_now"
        if overall >= 0.60 and feasibility >= 0.5:
            return "strong_candidate"
        if overall >= 0.40:
            return "investigate_further"
        if overall >= 0.25:
            return "defer"
        return "not_recommended"

    @staticmethod
    def _classify_feasibility(feasibility: float, complexity: float) -> str:
        adjusted = feasibility * (1 - 0.3 * complexity)
        if adjusted >= 0.80:
            return "fully_automatable"
        if adjusted >= 0.60:
            return "high"
        if adjusted >= 0.40:
            return "moderate"
        if adjusted >= 0.20:
            return "low"
        return "not_feasible"

    @staticmethod
    def _classify_risk(risk: float) -> str:
        if risk >= 0.80:
            return "critical"
        if risk >= 0.60:
            return "high"
        if risk >= 0.40:
            return "medium"
        if risk >= 0.20:
            return "low"
        return "negligible"


class MLScoringModel:
    """
    Machine-learned scoring model trained on real automation outcomes.

    Takes over from HeuristicScoringModel once sufficient training data exists.
    Uses gradient boosting for the primary prediction, with isotonic regression
    for confidence calibration.

    Training data: completed DecisionTraces with actual outcomes.
    """

    VERSION_PREFIX = "ml"

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = model_dir or Path("data/ml_models")
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.scaler: Optional[StandardScaler] = None
        self.roi_model: Optional[GradientBoostingRegressor] = None
        self.savings_model: Optional[GradientBoostingRegressor] = None
        self.cost_model: Optional[GradientBoostingRegressor] = None
        self.success_model: Optional[GradientBoostingClassifier] = None
        self.calibrator: Optional[IsotonicRegression] = None
        self.is_trained = False
        self.training_metrics: dict = {}
        self.version = ""

    def train(
        self,
        feature_vectors: list[FeatureVector],
        outcomes: list[dict],
    ) -> dict:
        """
        Train all sub-models on historical outcome data.

        Args:
            feature_vectors: Feature vectors for each process
            outcomes: List of dicts with actual_roi, actual_savings, actual_cost, success (bool)

        Returns:
            Training metrics (RMSE, R2, calibration error)
        """
        if not HAS_SKLEARN:
            raise RuntimeError("scikit-learn is required for ML model training")

        n = len(feature_vectors)
        if n < 30:
            raise ValueError(f"Need at least 30 training samples, got {n}")

        # Prepare arrays
        X = np.array([fv.to_array() for fv in feature_vectors])
        y_roi = np.array([o["actual_roi"] for o in outcomes])
        y_savings = np.array([o["actual_savings"] for o in outcomes])
        y_cost = np.array([o["actual_cost"] for o in outcomes])
        y_success = np.array([1 if o.get("actual_roi", 0) > 0 else 0 for o in outcomes])

        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Train ROI model
        self.roi_model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            min_samples_leaf=5,
            random_state=42,
        )
        self.roi_model.fit(X_scaled, y_roi)
        roi_cv = cross_val_score(self.roi_model, X_scaled, y_roi, cv=min(5, n // 5), scoring="r2")

        # Train savings model
        self.savings_model = GradientBoostingRegressor(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            min_samples_leaf=5,
            random_state=42,
        )
        self.savings_model.fit(X_scaled, y_savings)

        # Train cost model
        self.cost_model = GradientBoostingRegressor(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            min_samples_leaf=5,
            random_state=42,
        )
        self.cost_model.fit(X_scaled, y_cost)

        # Train success classifier
        if len(set(y_success)) > 1:
            self.success_model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                random_state=42,
            )
            self.success_model.fit(X_scaled, y_success)

        # Calibrate confidence
        self._calibrate(X_scaled, y_roi, outcomes)

        self.is_trained = True
        self.version = f"{self.VERSION_PREFIX}-{FEATURE_VERSION}-n{n}"

        self.training_metrics = {
            "n_samples": n,
            "roi_r2_cv_mean": float(np.mean(roi_cv)),
            "roi_r2_cv_std": float(np.std(roi_cv)),
            "roi_rmse": float(np.sqrt(np.mean((self.roi_model.predict(X_scaled) - y_roi) ** 2))),
            "success_rate": float(np.mean(y_success)),
            "version": self.version,
        }

        logger.info(f"Model trained: {self.training_metrics}")
        return self.training_metrics

    def _calibrate(self, X: np.ndarray, y_roi: np.ndarray, outcomes: list[dict]) -> None:
        """
        Calibrate confidence using isotonic regression.
        Maps predicted confidence -> observed accuracy.
        """
        predictions = self.roi_model.predict(X)
        residuals = np.abs(predictions - y_roi)

        # Compute "raw confidence" from prediction variance in ensemble
        # Use stage predictions to get variance
        staged_preds = np.array(list(self.roi_model.staged_predict(X)))
        pred_std = np.std(staged_preds[-50:], axis=0)  # variance of last 50 trees
        raw_confidence = 1.0 / (1.0 + pred_std / (np.abs(y_roi.mean()) + 1))

        # Actual accuracy: 1 if within 20% of actual, 0 otherwise
        accuracy = (residuals / (np.abs(y_roi) + 1) < 0.20).astype(float)

        self.calibrator = IsotonicRegression(out_of_bounds="clip")
        self.calibrator.fit(raw_confidence, accuracy)

    def predict(self, feature_vector: FeatureVector) -> PredictionResult:
        if not self.is_trained:
            raise RuntimeError("Model is not trained — use HeuristicScoringModel as fallback")

        X = feature_vector.to_array().reshape(1, -1)
        X_scaled = self.scaler.transform(X)

        # Predictions
        pred_roi = float(self.roi_model.predict(X_scaled)[0])
        pred_savings = float(self.savings_model.predict(X_scaled)[0])
        pred_cost = float(self.cost_model.predict(X_scaled)[0])

        if pred_savings > 0:
            pred_payback = (pred_cost / pred_savings) * 12
        else:
            pred_payback = 999.0

        # Confidence calibration
        staged_preds = np.array(list(self.roi_model.staged_predict(X_scaled)))
        pred_std = float(np.std(staged_preds[-50:, 0]))
        raw_confidence = 1.0 / (1.0 + pred_std / (abs(pred_roi) + 1))

        if self.calibrator:
            confidence = float(self.calibrator.predict([raw_confidence])[0])
        else:
            confidence = raw_confidence

        # Prediction intervals from ensemble variance
        pi_lower = pred_roi - 1.96 * pred_std
        pi_upper = pred_roi + 1.96 * pred_std

        # Compute sub-scores from features
        f = feature_vector.features
        feasibility = f.get("automation_readiness", 0.5)
        value = min(max(pred_savings / 500_000, 0.0), 1.0)
        risk = f.get("complexity_index", 0.3) * 0.5 + f.get("category_risk", 0.3) * 0.5
        complexity = f.get("complexity_index", 0.3)

        # Success probability
        if self.success_model:
            success_prob = float(self.success_model.predict_proba(X_scaled)[0, 1])
        else:
            success_prob = 0.5

        overall = 0.30 * feasibility + 0.35 * value + 0.20 * (1 - risk) + 0.15 * success_prob
        overall = max(0.0, min(1.0, overall))

        return PredictionResult(
            overall_score=round(overall, 4),
            feasibility_score=round(feasibility, 4),
            value_score=round(value, 4),
            risk_score=round(risk, 4),
            complexity_score=round(complexity, 4),
            estimated_annual_savings=round(max(pred_savings, 0), 2),
            estimated_implementation_cost=round(max(pred_cost, 0), 2),
            estimated_roi=round(pred_roi, 2),
            estimated_payback_months=round(max(pred_payback, 0), 1),
            confidence=round(confidence, 4),
            prediction_interval_lower=round(pi_lower, 2),
            prediction_interval_upper=round(pi_upper, 2),
            recommendation=HeuristicScoringModel._classify_recommendation(overall, feasibility, risk),
            automation_feasibility=HeuristicScoringModel._classify_feasibility(feasibility, complexity),
            risk_level=HeuristicScoringModel._classify_risk(risk),
            model_version=self.version,
            feature_vector=feature_vector.to_dict(),
        )

    def save(self, path: Optional[Path] = None) -> Path:
        if not joblib:
            raise RuntimeError("joblib is required for model persistence")
        save_path = path or self.model_dir / f"scoring_model_{self.version}.joblib"
        joblib.dump({
            "scaler": self.scaler,
            "roi_model": self.roi_model,
            "savings_model": self.savings_model,
            "cost_model": self.cost_model,
            "success_model": self.success_model,
            "calibrator": self.calibrator,
            "version": self.version,
            "metrics": self.training_metrics,
        }, save_path)
        logger.info(f"Model saved to {save_path}")
        return save_path

    def load(self, path: Optional[Path] = None) -> None:
        if not joblib:
            raise RuntimeError("joblib is required for model persistence")
        load_path = path or max(self.model_dir.glob("scoring_model_*.joblib"), key=lambda p: p.stat().st_mtime)
        data = joblib.load(load_path)
        self.scaler = data["scaler"]
        self.roi_model = data["roi_model"]
        self.savings_model = data["savings_model"]
        self.cost_model = data["cost_model"]
        self.success_model = data["success_model"]
        self.calibrator = data["calibrator"]
        self.version = data["version"]
        self.training_metrics = data["metrics"]
        self.is_trained = True
        logger.info(f"Model loaded: {self.version}")
