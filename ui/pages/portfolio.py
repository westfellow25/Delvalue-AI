"""Portfolio Analysis — budget optimization, roadmap, quick wins."""

from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from core.agents.advisor import AdvisorAgent
from core.engines.scoring import ScoringEngine
from data.database import engine
from data.models.process import Process
from data.repositories.process_repository import ProcessRepository
from ui.components.charts import portfolio_scatter

DEMO_ORG = "demo-org"


def render():
    st.title("Portfolio Analysis")
    st.caption("Optimize your automation investment portfolio")

    with Session(engine) as db:
        repo = ProcessRepository(db, DEMO_ORG)
        processes, total = repo.list_all(limit=500)

    if not processes:
        st.warning("No processes available. Add processes in the library first.")
        return

    # Config
    col1, col2, col3 = st.columns(3)
    with col1:
        budget = st.number_input("Budget ($)", min_value=10_000, value=500_000, step=50_000)
    with col2:
        risk_tolerance = st.selectbox("Risk Tolerance", ["conservative", "balanced", "aggressive"])
    with col3:
        max_parallel = st.slider("Max Parallel Implementations", 1, 10, 5)

    if st.button("Analyze Portfolio", type="primary", use_container_width=True):
        with st.spinner("Scoring all processes and optimizing portfolio..."):
            _run_portfolio(processes, budget, risk_tolerance, max_parallel)


def _run_portfolio(processes, budget, risk_tolerance, max_parallel):
    scoring_engine = ScoringEngine()
    advisor = AdvisorAgent()

    # Score all processes
    process_dicts = [_to_dict(p) for p in processes]
    portfolio_result = scoring_engine.score_portfolio(process_dicts, run_simulation=False)

    scored = [
        {"process": pd, "prediction": r["prediction"]}
        for pd, r in zip(process_dicts, portfolio_result["results"])
    ]

    # Quick wins
    quick_wins = advisor.identify_quick_wins(scored)

    # Portfolio recommendation
    recommendation = advisor.recommend_portfolio(
        scored, budget=budget, risk_tolerance=risk_tolerance,
        max_parallel_implementations=max_parallel,
    )

    # Roadmap
    roadmap = advisor.generate_roadmap(scored, budget=budget)

    # Strategic themes
    themes = advisor.detect_strategic_themes(scored)

    # -- Display --
    st.divider()

    # Summary
    summary = portfolio_result["summary"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Processes Scored", summary["total_processes"])
    c2.metric("Total Potential Savings", f"${summary['total_potential_savings']:,.0f}")
    c3.metric("Portfolio ROI", f"{summary['portfolio_roi']:.0f}%")
    c4.metric("Avg Confidence", f"{summary['average_confidence']:.0%}")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Recommended Portfolio", "Quick Wins", "Roadmap", "Strategic Themes", "Portfolio Map",
    ])

    with tab1:
        rec = recommendation.to_dict()
        st.info(rec["rationale"])
        st.metric("Selected Processes", len(rec["selected_processes"]))
        st.metric("Total Investment", f"${rec['total_investment']:,.0f}")
        st.metric("Expected Savings", f"${rec['total_expected_savings']:,.0f}")

        for i, p in enumerate(rec["selected_processes"], 1):
            st.markdown(
                f"**{i}. {p['name']}** — "
                f"ROI: {p['roi']:.0f}% | "
                f"Savings: ${p['estimated_savings']:,.0f} | "
                f"Cost: ${p['estimated_cost']:,.0f} | "
                f"Risk: {p['risk_level']}"
            )

    with tab2:
        if quick_wins:
            for i, qw in enumerate(quick_wins, 1):
                st.success(f"**{i}. {qw['name']}** — {qw['rationale']}")
        else:
            st.info("No quick wins found with current criteria.")

    with tab3:
        rm = roadmap.to_dict()
        for phase in rm["phases"]:
            with st.expander(
                f"**{phase['name']}** (Months {phase['months']}) — "
                f"${phase['investment']:,.0f} investment, ${phase['expected_savings']:,.0f} savings",
                expanded=True,
            ):
                st.caption(f"Focus: {phase['focus']}")
                for p in phase["processes"]:
                    st.markdown(f"- **{p['name']}** — ROI: {p['roi']:.0f}%, Savings: ${p['savings']:,.0f}")
                if not phase["processes"]:
                    st.caption("No processes assigned to this phase.")

    with tab4:
        if themes:
            for t in themes:
                st.markdown(f"**{t['category'].title()}** ({t['process_count']} processes)")
                st.markdown(t["description"])
                st.divider()
        else:
            st.info("No cross-cutting strategic themes detected.")

    with tab5:
        chart_data = [
            {"name": pd.get("name", "?"), "prediction": r["prediction"]}
            for pd, r in zip(process_dicts, portfolio_result["results"])
        ]
        st.plotly_chart(portfolio_scatter(chart_data), use_container_width=True)


def _to_dict(p: Process) -> dict:
    return {
        "name": p.name, "description": p.description,
        "category": p.category.value, "frequency": p.frequency.value,
        "duration_minutes": p.duration_minutes, "annual_volume": p.annual_volume,
        "people_involved": p.people_involved, "hourly_cost": p.hourly_cost,
        "systems_used": p.systems_used, "pain_points": p.pain_points,
        "stakeholders": p.stakeholders, "dependencies": p.dependencies,
        "num_decision_points": p.num_decision_points, "num_exceptions": p.num_exceptions,
        "requires_judgment": p.requires_judgment, "structured_data_pct": p.structured_data_pct,
        "error_rate_pct": p.error_rate_pct,
        "documentation_quality": p.documentation_quality.value,
        "sop_exists": p.sop_exists,
    }
