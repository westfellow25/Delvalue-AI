"""Dashboard — executive overview with KPIs, charts, and quick actions."""

from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from data.database import engine
from data.models.process import (
    BenchmarkEntry,
    DecisionTrace,
    OpportunityScore,
    Process,
)
from data.repositories.process_repository import ProcessRepository, ScoreRepository
from ui.components.charts import portfolio_scatter, savings_waterfall

# Default org for demo mode
DEMO_ORG = "demo-org"


def render():
    st.title("Dashboard")
    st.caption("Executive overview of your automation portfolio")

    with Session(engine) as db:
        process_count = (
            db.query(Process)
            .filter(Process.organization_id == DEMO_ORG, Process.is_deleted == False)
            .count()
        )
        scores = (
            db.query(OpportunityScore)
            .filter(OpportunityScore.organization_id == DEMO_ORG)
            .all()
        )
        traces = (
            db.query(DecisionTrace)
            .filter(DecisionTrace.organization_id == DEMO_ORG)
            .all()
        )

    total_savings = sum(s.estimated_annual_savings for s in scores) if scores else 0
    total_cost = sum(s.implementation_cost for s in scores) if scores else 0
    avg_roi = (sum(s.roi_percentage for s in scores) / len(scores)) if scores else 0
    avg_confidence = (sum(s.confidence_level for s in scores) / len(scores)) if scores else 0

    # -- KPI Cards --
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Processes", f"{process_count}")
    col2.metric("Scored", f"{len(scores)}")
    col3.metric("Total Savings", f"${total_savings:,.0f}")
    col4.metric("Avg ROI", f"{avg_roi:.0f}%")
    col5.metric("Avg Confidence", f"{avg_confidence:.0%}")

    st.divider()

    # -- Quick actions --
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.info("**Quick Start**: Add a process in the Process Library, then analyze it.")
    with col_b:
        st.info(f"**Benchmarks**: {_benchmark_count()} industry benchmarks loaded across 12 categories.")
    with col_c:
        completed = len([t for t in traces if t.actual_roi is not None])
        st.info(f"**Learning Loop**: {completed} completed implementations feeding the ML model.")

    if not scores:
        st.warning("No processes scored yet. Go to **Process Library** to add and analyze processes.")
        return

    # -- Charts --
    st.subheader("Portfolio Overview")

    tab1, tab2, tab3 = st.tabs(["Category Breakdown", "Top Opportunities", "Savings Waterfall"])

    with tab1:
        import plotly.express as px
        category_data = {}
        for s in scores:
            cat = s.process.category.value if s.process else "unknown"
            if cat not in category_data:
                category_data[cat] = {"count": 0, "savings": 0}
            category_data[cat]["count"] += 1
            category_data[cat]["savings"] += s.estimated_annual_savings

        if category_data:
            import pandas as pd
            df = pd.DataFrame([
                {"Category": k, "Processes": v["count"], "Total Savings": v["savings"]}
                for k, v in category_data.items()
            ])
            fig = px.bar(
                df, x="Category", y="Total Savings",
                color="Processes", color_continuous_scale="Blues",
                title="Savings Potential by Category",
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        top = sorted(scores, key=lambda s: s.overall_score, reverse=True)[:10]
        for i, s in enumerate(top, 1):
            name = s.process.name if s.process else "Unknown"
            rec_color = {
                "automate_now": "🟢",
                "strong_candidate": "🔵",
                "investigate_further": "🟡",
                "defer": "🟠",
                "not_recommended": "🔴",
            }.get(s.recommendation.value, "⚪")
            st.markdown(
                f"**{i}. {rec_color} {name}** — "
                f"Score: {s.overall_score:.2f} | "
                f"ROI: {s.roi_percentage:.0f}% | "
                f"Savings: ${s.estimated_annual_savings:,.0f} | "
                f"Confidence: {s.confidence_level:.0%}"
            )

    with tab3:
        waterfall_data = [
            {"name": s.process.name if s.process else "?", "estimated_savings": s.estimated_annual_savings}
            for s in sorted(scores, key=lambda s: s.estimated_annual_savings, reverse=True)[:10]
        ]
        st.plotly_chart(savings_waterfall(waterfall_data), use_container_width=True)

    # -- Recommendation distribution --
    st.subheader("Recommendation Distribution")
    rec_counts = {}
    for s in scores:
        r = s.recommendation.value
        rec_counts[r] = rec_counts.get(r, 0) + 1
    cols = st.columns(len(rec_counts))
    for col, (rec, count) in zip(cols, rec_counts.items()):
        col.metric(rec.replace("_", " ").title(), count)


def _benchmark_count() -> int:
    with Session(engine) as db:
        return db.query(BenchmarkEntry).count()
