"""
DelValue AI — Monitor Agent

Real outcome tracking (not fake data like the prototype's `random.random()`).
Powers the data flywheel:
  1. Record actual outcomes from real implementations
  2. Compute prediction accuracy metrics (MAPE, calibration error)
  3. Detect model drift
  4. Generate alerts for variance thresholds
  5. Feed outcome data back to ML training pipeline
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AccuracyMetrics:
    """Real prediction accuracy computed from completed DecisionTraces."""
    sample_size: int
    roi_mape: float  # Mean Absolute Percentage Error
    roi_rmse: float  # Root Mean Squared Error
    savings_mape: float
    cost_mape: float
    calibration_error: float  # Expected vs observed confidence
    accuracy_within_20pct: float  # % predictions within 20% of actual

    def to_dict(self) -> dict:
        return {
            "sample_size": self.sample_size,
            "roi_mape": self.roi_mape,
            "roi_rmse": self.roi_rmse,
            "savings_mape": self.savings_mape,
            "cost_mape": self.cost_mape,
            "calibration_error": self.calibration_error,
            "accuracy_within_20pct": self.accuracy_within_20pct,
        }


@dataclass
class DriftAlert:
    metric: str
    current_value: float
    baseline_value: float
    deviation: float
    severity: str  # low|medium|high|critical
    description: str


@dataclass
class VarianceAlert:
    process_name: str
    trace_id: str
    metric: str
    predicted: float
    actual: float
    variance_pct: float
    severity: str
    recommendation: str


class MonitorAgent:
    """
    Implementation tracking and model performance monitoring.
    Uses real DecisionTrace data — no mocks, no `random.random()`.
    """

    # Variance thresholds for alerting
    VARIANCE_THRESHOLDS = {
        "minor": 0.10,     # 10%
        "moderate": 0.25,  # 25%
        "severe": 0.50,    # 50%
    }

    def __init__(self, trace_repository=None):
        self.trace_repository = trace_repository

    # -- Accuracy metrics --

    def compute_accuracy(self, traces: list[dict]) -> Optional[AccuracyMetrics]:
        """
        Compute prediction accuracy from completed traces.

        traces: list of dicts with predicted_roi, actual_roi, etc.
        Requires at least 5 completed traces for meaningful statistics.
        """
        completed = [
            t for t in traces
            if t.get("actual_roi") is not None and t.get("predicted_roi") is not None
        ]
        if len(completed) < 5:
            return None

        predicted_roi = np.array([t["predicted_roi"] for t in completed])
        actual_roi = np.array([t["actual_roi"] for t in completed])

        predicted_savings = np.array([t.get("predicted_annual_savings", 0) for t in completed])
        actual_savings = np.array([t.get("actual_annual_savings", 0) for t in completed])

        predicted_cost = np.array([t.get("predicted_implementation_cost", 0) for t in completed])
        actual_cost = np.array([t.get("actual_implementation_cost", 0) for t in completed])

        # MAPE: Mean Absolute Percentage Error
        roi_mape = self._safe_mape(predicted_roi, actual_roi)
        savings_mape = self._safe_mape(predicted_savings, actual_savings)
        cost_mape = self._safe_mape(predicted_cost, actual_cost)

        # RMSE
        roi_rmse = float(np.sqrt(np.mean((predicted_roi - actual_roi) ** 2)))

        # Accuracy within 20%
        within_20 = np.abs((predicted_roi - actual_roi) / (np.abs(actual_roi) + 1)) < 0.20
        accuracy_20 = float(np.mean(within_20))

        # Calibration error — if confidence was reported, compare to hit rate
        predicted_confidences = np.array([t.get("predicted_confidence", 0.5) for t in completed])
        avg_confidence = float(np.mean(predicted_confidences))
        calibration_error = abs(avg_confidence - accuracy_20)

        return AccuracyMetrics(
            sample_size=len(completed),
            roi_mape=roi_mape,
            roi_rmse=roi_rmse,
            savings_mape=savings_mape,
            cost_mape=cost_mape,
            calibration_error=calibration_error,
            accuracy_within_20pct=accuracy_20,
        )

    @staticmethod
    def _safe_mape(predicted: np.ndarray, actual: np.ndarray) -> float:
        """Safe MAPE — avoids division by zero."""
        mask = np.abs(actual) > 1e-6
        if mask.sum() == 0:
            return 0.0
        return float(np.mean(np.abs((predicted[mask] - actual[mask]) / actual[mask])) * 100)

    # -- Drift detection --

    def detect_drift(
        self,
        recent_traces: list[dict],
        baseline_traces: list[dict],
    ) -> list[DriftAlert]:
        """
        Detect if model performance is degrading over time.
        Compare recent (last N traces) against historical baseline.
        """
        if len(recent_traces) < 10 or len(baseline_traces) < 10:
            return []

        recent_metrics = self.compute_accuracy(recent_traces)
        baseline_metrics = self.compute_accuracy(baseline_traces)

        if not recent_metrics or not baseline_metrics:
            return []

        alerts = []

        # MAPE drift
        mape_drift = recent_metrics.roi_mape - baseline_metrics.roi_mape
        if mape_drift > 5.0:  # 5pp increase in MAPE is concerning
            alerts.append(DriftAlert(
                metric="roi_mape",
                current_value=recent_metrics.roi_mape,
                baseline_value=baseline_metrics.roi_mape,
                deviation=mape_drift,
                severity=self._drift_severity(mape_drift, [5, 10, 20]),
                description=(
                    f"Recent ROI prediction error ({recent_metrics.roi_mape:.1f}% MAPE) "
                    f"has drifted {mape_drift:.1f}pp above baseline ({baseline_metrics.roi_mape:.1f}%). "
                    f"Consider retraining the scoring model."
                ),
            ))

        # Calibration drift
        cal_drift = recent_metrics.calibration_error - baseline_metrics.calibration_error
        if cal_drift > 0.10:
            alerts.append(DriftAlert(
                metric="calibration_error",
                current_value=recent_metrics.calibration_error,
                baseline_value=baseline_metrics.calibration_error,
                deviation=cal_drift,
                severity=self._drift_severity(cal_drift, [0.05, 0.15, 0.30]),
                description=(
                    f"Model confidence is drifting from actual accuracy by "
                    f"{recent_metrics.calibration_error:.2f}. Recalibrate the confidence layer."
                ),
            ))

        # Accuracy drift (within 20%)
        acc_drift = baseline_metrics.accuracy_within_20pct - recent_metrics.accuracy_within_20pct
        if acc_drift > 0.10:
            alerts.append(DriftAlert(
                metric="accuracy_within_20pct",
                current_value=recent_metrics.accuracy_within_20pct,
                baseline_value=baseline_metrics.accuracy_within_20pct,
                deviation=-acc_drift,
                severity=self._drift_severity(acc_drift, [0.05, 0.15, 0.25]),
                description=(
                    f"Share of predictions within 20% of actual dropped from "
                    f"{baseline_metrics.accuracy_within_20pct:.0%} to "
                    f"{recent_metrics.accuracy_within_20pct:.0%}."
                ),
            ))

        return alerts

    @staticmethod
    def _drift_severity(value: float, thresholds: list[float]) -> str:
        if value >= thresholds[2]:
            return "critical"
        if value >= thresholds[1]:
            return "high"
        if value >= thresholds[0]:
            return "medium"
        return "low"

    # -- Variance alerts --

    def check_variance_alerts(self, traces: list[dict]) -> list[VarianceAlert]:
        """Generate alerts for implementations with significant prediction variance."""
        alerts = []
        for t in traces:
            if t.get("actual_roi") is None or t.get("predicted_roi") is None:
                continue
            predicted = t["predicted_roi"]
            actual = t["actual_roi"]
            if abs(predicted) < 1e-6:
                continue

            variance_pct = (actual - predicted) / abs(predicted)

            severity = self._classify_variance_severity(variance_pct)
            if severity == "minor":
                continue

            recommendation = self._variance_recommendation(variance_pct, severity)

            alerts.append(VarianceAlert(
                process_name=t.get("process_name", "Unknown"),
                trace_id=t.get("id", ""),
                metric="roi",
                predicted=predicted,
                actual=actual,
                variance_pct=variance_pct * 100,
                severity=severity,
                recommendation=recommendation,
            ))

        return alerts

    def _classify_variance_severity(self, variance_pct: float) -> str:
        abs_var = abs(variance_pct)
        if abs_var >= self.VARIANCE_THRESHOLDS["severe"]:
            return "severe"
        if abs_var >= self.VARIANCE_THRESHOLDS["moderate"]:
            return "moderate"
        if abs_var >= self.VARIANCE_THRESHOLDS["minor"]:
            return "minor"
        return "none"

    @staticmethod
    def _variance_recommendation(variance_pct: float, severity: str) -> str:
        if variance_pct > 0:
            if severity == "severe":
                return (
                    "Significantly outperforming predictions. Investigate drivers "
                    "for replication across the portfolio."
                )
            return "Outperforming predictions — document success factors."
        else:
            if severity == "severe":
                return (
                    "Critically underperforming. Trigger root cause analysis and "
                    "flag similar processes in the pipeline for re-evaluation."
                )
            return "Underperforming predictions — review implementation approach."

    # -- Learning insights --

    def generate_learning_insights(self, traces: list[dict]) -> list[str]:
        """Extract patterns from historical outcomes."""
        insights = []

        completed = [t for t in traces if t.get("actual_roi") is not None]
        if len(completed) < 10:
            insights.append(
                f"Insufficient outcome data ({len(completed)} completed traces). "
                f"Need at least 10 for meaningful insights, 50+ for ML training."
            )
            return insights

        # Overall accuracy
        metrics = self.compute_accuracy(completed)
        if metrics:
            insights.append(
                f"Model accuracy: {metrics.accuracy_within_20pct:.0%} of predictions "
                f"within 20% of actual. ROI MAPE: {metrics.roi_mape:.1f}%."
            )

        # Success/failure split
        successful = [t for t in completed if t["actual_roi"] > 0]
        failed = [t for t in completed if t["actual_roi"] <= 0]
        success_rate = len(successful) / len(completed)
        insights.append(
            f"{success_rate:.0%} of implementations achieved positive ROI "
            f"({len(successful)} successes / {len(failed)} failures)."
        )

        # Category analysis
        from collections import defaultdict
        cat_outcomes = defaultdict(list)
        for t in completed:
            cat_outcomes[t.get("category", "unknown")].append(t["actual_roi"])

        best_cat = max(cat_outcomes, key=lambda c: np.mean(cat_outcomes[c]), default=None)
        if best_cat:
            avg_roi = float(np.mean(cat_outcomes[best_cat]))
            insights.append(
                f"Best-performing category: {best_cat} with average ROI of {avg_roi:.0f}%."
            )

        # Calibration insight
        if metrics and metrics.calibration_error > 0.15:
            insights.append(
                f"Confidence calibration error ({metrics.calibration_error:.2f}) exceeds "
                f"recommended threshold. Retrain calibration layer with latest outcomes."
            )

        return insights

    def record_outcome(
        self,
        trace_id: str,
        actual_roi: float,
        actual_savings: float,
        actual_cost: float,
        actual_payback_months: float,
        lessons_learned: Optional[str] = None,
    ) -> dict:
        """
        Record actual outcome for a decision trace.
        Uses the repository if available, otherwise returns the computed variances.
        """
        if self.trace_repository:
            trace = self.trace_repository.record_outcome(
                trace_id,
                actual_roi,
                actual_savings,
                actual_cost,
                actual_payback_months,
                lessons=lessons_learned,
            )
            if trace:
                return {
                    "trace_id": trace.id,
                    "variance_roi": trace.variance_roi,
                    "variance_savings": trace.variance_savings,
                    "variance_cost": trace.variance_cost,
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                }

        return {
            "trace_id": trace_id,
            "actual_roi": actual_roi,
            "actual_savings": actual_savings,
            "actual_cost": actual_cost,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
