"""Simulation Lab — interactive Monte Carlo with parameter sliders."""

from __future__ import annotations

import streamlit as st

from core.engines.simulation import MonteCarloEngine, SimulationConfig
from ui.components.charts import roi_distribution_chart


def render():
    st.title("Simulation Lab")
    st.caption("Interactive Monte Carlo simulation for automation ROI")

    st.markdown("Adjust parameters to explore different scenarios and see how uncertainty affects outcomes.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Input Parameters")
        base_savings = st.number_input(
            "Expected Annual Savings ($)", min_value=1_000, value=200_000, step=10_000,
        )
        base_cost = st.number_input(
            "Implementation Cost ($)", min_value=1_000, value=80_000, step=5_000,
        )
        base_duration = st.number_input(
            "Implementation Duration (months)", min_value=1.0, value=6.0, step=1.0,
        )

    with col2:
        st.subheader("Uncertainty Parameters")
        automation_rate = st.slider("Automation Rate", 0.1, 1.0, 0.65, 0.05)
        complexity = st.slider("Process Complexity", 0.0, 1.0, 0.4, 0.05)
        confidence = st.slider("Estimate Confidence", 0.2, 0.95, 0.6, 0.05)

    col3, col4 = st.columns(2)
    with col3:
        iterations = st.select_slider("Iterations", [1000, 5000, 10000, 50000, 100000], value=10000)
    with col4:
        discount_rate = st.slider("Discount Rate", 0.0, 0.25, 0.10, 0.01)
        horizon = st.slider("Time Horizon (years)", 1, 10, 3)

    if st.button("Run Simulation", type="primary", use_container_width=True):
        config = SimulationConfig(
            iterations=iterations,
            discount_rate=discount_rate,
            time_horizon_years=horizon,
        )
        engine = MonteCarloEngine(config=config)

        with st.spinner(f"Running {iterations:,} simulations..."):
            result = engine.simulate(
                base_savings=base_savings,
                base_cost=base_cost,
                base_duration_months=base_duration,
                automation_rate=automation_rate,
                complexity_factor=complexity,
                confidence_level=confidence,
            )

        st.divider()

        # KPIs
        st.subheader("Results")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Mean ROI", f"{result.roi_mean:.0f}%")
        k2.metric("Median ROI", f"{result.roi_median:.0f}%")
        k3.metric("P(ROI > 0%)", f"{result.prob_positive_roi:.0%}")
        k4.metric("P(ROI > 100%)", f"{result.prob_roi_above_100:.0%}")

        k5, k6, k7, k8 = st.columns(4)
        k5.metric("Mean Savings", f"${result.savings_mean:,.0f}")
        k6.metric("Mean Cost", f"${result.cost_mean:,.0f}")
        k7.metric("Mean Payback", f"{result.payback_mean:.1f} mo")
        k8.metric("NPV (mean)", f"${result.npv_mean:,.0f}")

        # Distribution chart
        st.subheader("ROI Distribution")
        st.plotly_chart(
            roi_distribution_chart(result.roi_histogram, "ROI Distribution (%)"),
            use_container_width=True,
        )

        # Percentiles table
        tab1, tab2, tab3 = st.tabs(["Percentiles", "Risk Metrics", "Input Distributions"])

        with tab1:
            pcols = st.columns(len(result.roi_percentiles))
            for col, (label, val) in zip(pcols, result.roi_percentiles.items()):
                col.metric(label.upper(), f"{val:.0f}%")

            st.markdown(
                f"**80% Confidence Interval:** "
                f"[{result.roi_percentiles.get('p10', 0):.0f}%, "
                f"{result.roi_percentiles.get('p90', 0):.0f}%]"
            )

        with tab2:
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("VaR (5%)", f"{result.value_at_risk_5pct:.0f}%",
                      help="Value at Risk: worst-case ROI at 5th percentile")
            r2.metric("CVaR (5%)", f"{result.conditional_var_5pct:.0f}%",
                      help="Conditional VaR: expected ROI in the worst 5% of scenarios")
            r3.metric("Max Loss", f"{result.max_loss:.0f}%")
            r4.metric("Downside Dev", f"{result.downside_deviation:.1f}%")

            st.markdown(f"**P(Payback < 6mo):** {result.prob_payback_under_6mo:.0%}")
            st.markdown(f"**P(Payback < 12mo):** {result.prob_payback_under_12mo:.0%}")
            st.markdown(f"**P(Payback < 24mo):** {result.prob_payback_under_24mo:.0%}")

        with tab3:
            for dist in result.input_distributions:
                st.markdown(f"**{dist['name']}:** {dist['type']} — {dist}")

        st.caption(f"Simulation completed in {result.run_duration_ms}ms")
