"""Analyze Process — deep analysis with scoring, simulation, benchmarks."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import streamlit as st
from sqlalchemy.orm import Session

from core.engines.scoring import ScoringEngine
from core.engines.benchmark import BenchmarkEngine
from core.agents.analyst import AnalystAgent
from core.ml.models import HeuristicScoringModel
from data.database import engine
from data.models.process import OpportunityScore, Process
from data.repositories.process_repository import ProcessRepository
from ui.components.charts import roi_distribution_chart, score_radar_chart

DEMO_ORG = "demo-org"


def render():
    st.title("Analyze Process")
    st.caption("Deep analysis with ML scoring, Monte Carlo simulation, and industry benchmarks")

    with Session(engine) as db:
        repo = ProcessRepository(db, DEMO_ORG)
        processes, total = repo.list_all(limit=500)

    if not processes:
        st.warning("No processes in library. Add some first.")
        return

    process_map = {f"{p.name} ({p.category.value})": p for p in processes}
    selected_name = st.selectbox("Select a process to analyze", list(process_map.keys()))
    process = process_map[selected_name]

    # Options
    col1, col2, col3 = st.columns(3)
    with col1:
        run_sim = st.checkbox("Run Monte Carlo Simulation", value=True)
    with col2:
        sim_iterations = st.select_slider("Iterations", [1000, 5000, 10000, 50000], value=10000)
    with col3:
        run_benchmark = st.checkbox("Compare to Benchmarks", value=True)

    industry = None
    if run_benchmark:
        industry = st.selectbox("Industry (for benchmarks)", [
            None, "financial_services", "healthcare", "manufacturing",
            "retail", "technology", "insurance", "professional_services",
            "telecommunications", "energy", "government",
        ], format_func=lambda x: "All Industries" if x is None else x.replace("_", " ").title())

    if st.button("Run Analysis", type="primary", use_container_width=True):
        with st.spinner("Running analysis..."):
            _run_analysis(process, run_sim, sim_iterations, run_benchmark, industry)


def _run_analysis(process, run_sim, sim_iterations, run_benchmark, industry):
    process_data = _process_to_dict(process)

    scoring_engine = ScoringEngine()

    with Session(engine) as db:
        benchmark_engine = BenchmarkEngine(db) if run_benchmark else None
        analyst = AnalystAgent(
            scoring_engine=scoring_engine,
            benchmark_engine=benchmark_engine,
        )

        result = analyst.analyze(
            process_data,
            run_simulation=run_sim,
            run_benchmark=run_benchmark,
            industry=industry,
            simulation_iterations=sim_iterations,
            include_llm_narrative=False,
        )

        # Persist score
        pred = result.prediction
        score = OpportunityScore(
            organization_id=DEMO_ORG,
            process_id=process.id,
            feasibility_score=pred["feasibility_score"],
            value_score=pred["value_score"],
            risk_score=pred["risk_score"],
            complexity_score=pred["complexity_score"],
            overall_score=pred["overall_score"],
            estimated_annual_savings=pred["estimated_annual_savings"],
            implementation_cost=pred["estimated_implementation_cost"],
            roi_percentage=pred["estimated_roi"],
            payback_months=pred["estimated_payback_months"],
            confidence_level=pred["confidence"],
            automation_feasibility=pred["automation_feasibility"],
            risk_level=pred["risk_level"],
            recommendation=pred["recommendation"],
            scoring_model_version=result.model_version,
            reasoning=result.detailed_reasoning,
            analyzed_at=datetime.now(timezone.utc),
        )
        if result.simulation:
            sim = result.simulation
            score.roi_p10 = sim.get("roi", {}).get("percentiles", {}).get("p10")
            score.roi_p50 = sim.get("roi", {}).get("percentiles", {}).get("p50")
            score.roi_p90 = sim.get("roi", {}).get("percentiles", {}).get("p90")
            score.npv_3yr = sim.get("npv", {}).get("mean")
        if result.benchmark:
            score.industry_percentile = result.benchmark["positioning"]["roi_percentile"]

        db.add(score)
        db.commit()

    # -- Display results --
    st.divider()
    st.subheader("Analysis Results")

    # Executive summary
    rec_emoji = {
        "automate_now": "🟢", "strong_candidate": "🔵",
        "investigate_further": "🟡", "defer": "🟠", "not_recommended": "🔴",
    }
    emoji = rec_emoji.get(pred["recommendation"], "⚪")
    st.markdown(f"### {emoji} {pred['recommendation'].replace('_', ' ').title()}")
    st.info(result.executive_summary)

    # KPI row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Overall Score", f"{pred['overall_score']:.2f}")
    c2.metric("ROI", f"{pred['estimated_roi']:.0f}%")
    c3.metric("Annual Savings", f"${pred['estimated_annual_savings']:,.0f}")
    c4.metric("Payback", f"{pred['estimated_payback_months']:.1f} mo")
    c5.metric("Confidence", f"{pred['confidence']:.0%}")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Score Breakdown", "Simulation", "Benchmark", "Details",
    ])

    with tab1:
        st.plotly_chart(
            score_radar_chart(
                pred["feasibility_score"], pred["value_score"],
                pred["risk_score"], pred["complexity_score"],
                pred["confidence"],
            ),
            use_container_width=True,
        )

    with tab2:
        if result.simulation:
            sim = result.simulation
            prob = sim["probabilities"]

            pc1, pc2, pc3, pc4 = st.columns(4)
            pc1.metric("P(ROI > 0%)", f"{prob['positive_roi']:.0%}")
            pc2.metric("P(ROI > 100%)", f"{prob['roi_above_100']:.0%}")
            pc3.metric("P(Payback < 12mo)", f"{prob['payback_under_12mo']:.0%}")
            pc4.metric("Value at Risk (5%)", f"{sim['risk']['value_at_risk_5pct']:.0f}%")

            roi_hist = sim.get("roi", {}).get("percentiles", {})
            st.markdown(
                f"**80% confidence interval:** "
                f"[{roi_hist.get('p10', 0):.0f}%, {roi_hist.get('p90', 0):.0f}%]"
            )

            if "roi" in sim:
                hist_data = sim.get("roi", {})
                # The histogram data is nested under the simulation result
                # Reconstruct from percentiles for display
                st.markdown(f"**NPV (3yr):** ${sim.get('npv', {}).get('mean', 0):,.0f}")
                st.markdown(f"**Iterations:** {sim.get('metadata', {}).get('num_iterations', 0):,}")
        else:
            st.info("Simulation not run. Enable Monte Carlo above.")

    with tab3:
        if result.benchmark:
            bm = result.benchmark
            pos = bm["positioning"]
            st.markdown(f"**Industry Positioning:** {pos['tier'].replace('_', ' ').title()}")
            st.markdown(f"**ROI Percentile:** {pos['roi_percentile']:.0f}th")
            st.markdown(f"**Sample Size:** {bm['sample_size']} companies")
            st.markdown(f"**Industry Avg ROI:** {bm['industry_benchmarks']['avg_roi']:.0f}%")
            st.markdown(f"**Success Rate:** {bm['industry_benchmarks']['success_rate']:.0%}")

            if bm.get("improvement_targets"):
                st.markdown("**Improvement Targets:**")
                for t in bm["improvement_targets"]:
                    st.markdown(f"- {t['description']}")
        else:
            st.info("Benchmark comparison not run.")

    with tab4:
        st.markdown("**Implementation Plan:**")
        for step in result.implementation_plan:
            st.markdown(f"- {step}")

        st.markdown("**Risk Analysis:**")
        for risk in result.risk_analysis:
            st.markdown(f"- {risk}")

        st.markdown("**Success Factors:**")
        for factor in result.success_factors:
            st.markdown(f"- {factor}")


def _process_to_dict(process: Process) -> dict:
    return {
        "id": process.id,
        "name": process.name,
        "description": process.description,
        "category": process.category.value,
        "frequency": process.frequency.value,
        "duration_minutes": process.duration_minutes,
        "annual_volume": process.annual_volume,
        "people_involved": process.people_involved,
        "hourly_cost": process.hourly_cost,
        "systems_used": process.systems_used,
        "pain_points": process.pain_points,
        "stakeholders": process.stakeholders,
        "dependencies": process.dependencies,
        "num_decision_points": process.num_decision_points,
        "num_exceptions": process.num_exceptions,
        "requires_judgment": process.requires_judgment,
        "structured_data_pct": process.structured_data_pct,
        "error_rate_pct": process.error_rate_pct,
        "documentation_quality": process.documentation_quality.value,
        "sop_exists": process.sop_exists,
    }
