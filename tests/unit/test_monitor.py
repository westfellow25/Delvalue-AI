"""Tests for the monitoring agent."""

import pytest
import numpy as np
from core.agents.monitor import MonitorAgent, AccuracyMetrics


@pytest.fixture
def monitor():
    return MonitorAgent()


@pytest.fixture
def completed_traces():
    """Synthetic traces with predicted vs actual."""
    np.random.seed(42)
    traces = []
    for i in range(20):
        predicted_roi = np.random.uniform(50, 300)
        noise = np.random.normal(0, predicted_roi * 0.15)
        actual_roi = predicted_roi + noise
        traces.append({
            "id": f"trace-{i}",
            "process_name": f"Process {i}",
            "category": "finance",
            "predicted_roi": predicted_roi,
            "actual_roi": actual_roi,
            "predicted_annual_savings": predicted_roi * 1000,
            "actual_annual_savings": actual_roi * 1000,
            "predicted_implementation_cost": 80_000,
            "actual_implementation_cost": 80_000 * (1 + np.random.normal(0, 0.1)),
            "predicted_confidence": 0.7,
        })
    return traces


def test_compute_accuracy(monitor, completed_traces):
    metrics = monitor.compute_accuracy(completed_traces)
    assert isinstance(metrics, AccuracyMetrics)
    assert metrics.sample_size == 20
    assert metrics.roi_mape >= 0
    assert metrics.roi_rmse >= 0


def test_insufficient_data_returns_none(monitor):
    traces = [{"predicted_roi": 100, "actual_roi": 110}] * 3
    assert monitor.compute_accuracy(traces) is None


def test_accuracy_within_20pct_is_bounded(monitor, completed_traces):
    metrics = monitor.compute_accuracy(completed_traces)
    assert 0 <= metrics.accuracy_within_20pct <= 1


def test_variance_alerts(monitor, completed_traces):
    # Add a big outlier
    completed_traces.append({
        "id": "outlier",
        "process_name": "Bad Process",
        "predicted_roi": 200,
        "actual_roi": 50,
        "predicted_annual_savings": 200_000,
        "actual_annual_savings": 50_000,
        "predicted_implementation_cost": 80_000,
        "actual_implementation_cost": 120_000,
        "predicted_confidence": 0.8,
    })
    alerts = monitor.check_variance_alerts(completed_traces)
    # The outlier should trigger an alert
    outlier_alerts = [a for a in alerts if a.process_name == "Bad Process"]
    assert len(outlier_alerts) > 0
    assert outlier_alerts[0].severity in ("moderate", "severe")


def test_learning_insights(monitor, completed_traces):
    insights = monitor.generate_learning_insights(completed_traces)
    assert len(insights) > 0
    assert any("accuracy" in i.lower() or "roi" in i.lower() for i in insights)


def test_drift_detection_no_drift(monitor, completed_traces):
    alerts = monitor.detect_drift(completed_traces[:10], completed_traces[10:])
    # Same distribution — small splits may trigger calibration noise
    assert len(alerts) <= 2
    # No MAPE drift expected from the same generating distribution
    mape_alerts = [a for a in alerts if a.metric == "roi_mape"]
    assert len(mape_alerts) == 0


def test_record_outcome_without_repo(monitor):
    result = monitor.record_outcome(
        trace_id="t1",
        actual_roi=150.0,
        actual_savings=200_000,
        actual_cost=85_000,
        actual_payback_months=5.1,
    )
    assert result["trace_id"] == "t1"
    assert result["actual_roi"] == 150.0
