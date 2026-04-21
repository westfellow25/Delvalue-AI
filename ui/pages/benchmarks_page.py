"""Benchmarks — industry comparisons and positioning."""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from sqlalchemy.orm import Session

from data.database import engine
from data.models.process import BenchmarkEntry, ProcessCategory


def render():
    st.title("Industry Benchmarks")
    st.caption("Compare automation outcomes across 12 categories and 10 industries")

    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox("Category", [c.value for c in ProcessCategory],
                                format_func=lambda x: x.replace("_", " ").title())
    with col2:
        industry_options = [
            None, "financial_services", "healthcare", "manufacturing",
            "retail", "technology", "insurance", "professional_services",
            "telecommunications", "energy", "government",
        ]
        industry = st.selectbox("Industry", industry_options,
                                format_func=lambda x: "All Industries (Global)" if x is None else x.replace("_", " ").title())

    with Session(engine) as db:
        q = db.query(BenchmarkEntry).filter(BenchmarkEntry.category == ProcessCategory(category))
        if industry:
            q = q.filter(BenchmarkEntry.industry == industry)
        else:
            q = q.filter(BenchmarkEntry.industry.is_(None))
        benchmark = q.first()

    if not benchmark:
        st.warning("No benchmark data available for this selection.")
        return

    st.divider()

    # KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Avg ROI", f"{benchmark.avg_roi:.0f}%")
    c2.metric("Median ROI", f"{benchmark.median_roi:.0f}%")
    c3.metric("Avg Savings", f"${benchmark.avg_savings:,.0f}")
    c4.metric("Success Rate", f"{benchmark.success_rate:.0%}")
    c5.metric("Sample Size", benchmark.sample_size)

    st.subheader("ROI Distribution")

    # Box plot visualization of percentiles
    fig = go.Figure()
    fig.add_trace(go.Box(
        q1=[benchmark.p25_roi],
        median=[benchmark.median_roi],
        q3=[benchmark.p75_roi],
        lowerfence=[max(benchmark.p25_roi - 1.5 * (benchmark.p75_roi - benchmark.p25_roi), 0)],
        upperfence=[benchmark.p75_roi + 1.5 * (benchmark.p75_roi - benchmark.p25_roi)],
        mean=[benchmark.avg_roi],
        name=f"{category.replace('_', ' ').title()}",
        marker_color="#3b82f6",
    ))
    fig.update_layout(
        title="ROI Percentile Distribution",
        yaxis_title="ROI (%)",
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Details table
    st.subheader("Benchmark Details")
    details = {
        "Metric": [
            "Average ROI", "Median ROI", "25th Percentile ROI", "75th Percentile ROI",
            "Avg Annual Savings", "Avg Implementation Cost", "Avg Payback (months)",
            "Success Rate", "Avg Implementation Time (months)", "ROI Std Dev",
        ],
        "Value": [
            f"{benchmark.avg_roi:.1f}%", f"{benchmark.median_roi:.1f}%",
            f"{benchmark.p25_roi:.1f}%", f"{benchmark.p75_roi:.1f}%",
            f"${benchmark.avg_savings:,.0f}", f"${benchmark.avg_implementation_cost:,.0f}",
            f"{benchmark.avg_payback_months:.1f}", f"{benchmark.success_rate:.0%}",
            f"{benchmark.avg_time_to_implement_months:.1f}", f"{benchmark.roi_std:.1f}%",
        ],
    }
    st.dataframe(details, use_container_width=True, hide_index=True)

    # Cross-category comparison
    st.subheader("Cross-Category Comparison")
    with Session(engine) as db:
        if industry:
            all_benchmarks = db.query(BenchmarkEntry).filter(BenchmarkEntry.industry == industry).all()
        else:
            all_benchmarks = db.query(BenchmarkEntry).filter(BenchmarkEntry.industry.is_(None)).all()

    if all_benchmarks:
        cats = [b.category.value.replace("_", " ").title() for b in all_benchmarks]
        rois = [b.avg_roi for b in all_benchmarks]
        success = [b.success_rate * 100 for b in all_benchmarks]

        import plotly.express as px
        import pandas as pd
        df = pd.DataFrame({"Category": cats, "Avg ROI (%)": rois, "Success Rate (%)": success})
        fig2 = px.bar(df, x="Category", y="Avg ROI (%)", color="Success Rate (%)",
                      color_continuous_scale="RdYlGn", title="ROI by Category")
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)
