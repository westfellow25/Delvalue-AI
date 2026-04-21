"""Monitoring — implementation tracking, accuracy metrics, learning loop."""

from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from core.agents.monitor import MonitorAgent
from data.database import engine
from data.models.process import DecisionTrace, ImplementationStatus
from data.repositories.process_repository import TraceRepository

DEMO_ORG = "demo-org"


def render():
    st.title("Monitoring & Learning")
    st.caption("Track implementations, measure prediction accuracy, improve the model")

    with Session(engine) as db:
        repo = TraceRepository(db, DEMO_ORG)
        all_traces = repo.get_completed_traces()
        traces_dicts = [_trace_to_dict(t) for t in all_traces]

    monitor = MonitorAgent()

    tab1, tab2, tab3 = st.tabs(["Accuracy Metrics", "Variance Alerts", "Learning Insights"])

    with tab1:
        metrics = monitor.compute_accuracy(traces_dicts)
        if metrics:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("ROI MAPE", f"{metrics.roi_mape:.1f}%",
                      help="Mean Absolute Percentage Error — lower is better")
            c2.metric("ROI RMSE", f"{metrics.roi_rmse:.1f}%")
            c3.metric("Within 20%", f"{metrics.accuracy_within_20pct:.0%}",
                      help="% of predictions within 20% of actual")
            c4.metric("Calibration Error", f"{metrics.calibration_error:.3f}",
                      help="Difference between stated confidence and actual hit rate")

            st.markdown(f"**Sample size:** {metrics.sample_size} completed implementations")
            st.markdown(f"**Savings MAPE:** {metrics.savings_mape:.1f}%")
            st.markdown(f"**Cost MAPE:** {metrics.cost_mape:.1f}%")

            if metrics.calibration_error > 0.15:
                st.warning("Calibration error exceeds threshold. Consider retraining the confidence layer.")
            else:
                st.success("Model is well-calibrated.")
        else:
            st.info(
                f"Need at least 5 completed implementations to compute accuracy. "
                f"Currently: {len(traces_dicts)} traces."
            )
            st.markdown(
                "Record actual outcomes by going to a scored process and entering "
                "the real ROI, savings, and costs after implementation."
            )

    with tab2:
        alerts = monitor.check_variance_alerts(traces_dicts)
        if alerts:
            for a in alerts:
                icon = {"severe": "🔴", "moderate": "🟡", "minor": "🟢"}.get(a.severity, "⚪")
                st.markdown(
                    f"{icon} **{a.process_name}** — "
                    f"Predicted: {a.predicted:.0f}% → Actual: {a.actual:.0f}% "
                    f"(variance: {a.variance_pct:+.0f}%)"
                )
                st.caption(a.recommendation)
        else:
            st.info("No variance alerts. Either no completed implementations or all within tolerance.")

    with tab3:
        insights = monitor.generate_learning_insights(traces_dicts)
        for insight in insights:
            st.markdown(f"- {insight}")

        st.divider()
        st.subheader("How the Learning Loop Works")
        st.markdown("""
1. **Score** a process → model predicts ROI, savings, cost
2. **Decide** to implement (or not) → decision is recorded
3. **Track** the implementation → status updates over time
4. **Record actuals** → real ROI, savings, cost after go-live
5. **Learn** → model compares predicted vs actual, recalibrates
6. **Improve** → retrain ML model with new outcome data

The more implementations you complete, the smarter the model becomes.
At 50+ completed traces, the ML scoring model activates.
""")


def _trace_to_dict(trace: DecisionTrace) -> dict:
    return {
        "id": trace.id,
        "process_name": trace.process.name if trace.process else "Unknown",
        "category": trace.process.category.value if trace.process else "unknown",
        "predicted_roi": trace.predicted_roi,
        "actual_roi": trace.actual_roi,
        "predicted_annual_savings": trace.predicted_annual_savings,
        "actual_annual_savings": trace.actual_annual_savings,
        "predicted_implementation_cost": trace.predicted_implementation_cost,
        "actual_implementation_cost": trace.actual_implementation_cost,
        "predicted_confidence": trace.predicted_confidence,
    }
