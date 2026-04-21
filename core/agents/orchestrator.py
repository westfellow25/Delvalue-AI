"""
DelValue AI — Agent Orchestrator

Coordinates multi-agent workflows end-to-end:
  score -> simulate -> benchmark -> analyze -> track
Handles cross-agent dependencies and failure isolation.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Top-level orchestration of all AI agents.
    Exposes high-level workflows that the API and UI consume.
    """

    def __init__(
        self,
        scoring_engine,
        simulation_engine=None,
        benchmark_engine=None,
        analyst_agent=None,
        advisor_agent=None,
        monitor_agent=None,
        discovery_engine=None,
        nlp_engine=None,
    ):
        self.scoring_engine = scoring_engine
        self.simulation_engine = simulation_engine
        self.benchmark_engine = benchmark_engine
        self.analyst_agent = analyst_agent
        self.advisor_agent = advisor_agent
        self.monitor_agent = monitor_agent
        self.discovery_engine = discovery_engine
        self.nlp_engine = nlp_engine

    # -- Single-process workflow --

    def full_analysis(
        self,
        process_data: dict,
        industry: Optional[str] = None,
        include_narrative: bool = True,
    ) -> dict:
        """Full pipeline: score → simulate → benchmark → narrative."""
        if self.analyst_agent:
            result = self.analyst_agent.analyze(
                process_data,
                run_simulation=True,
                run_benchmark=bool(self.benchmark_engine),
                industry=industry,
                include_llm_narrative=include_narrative,
            )
            return result.to_dict()

        # Fallback — just scoring
        return self.scoring_engine.score_process(process_data, run_simulation=True)

    # -- Portfolio workflow --

    def portfolio_analysis(
        self,
        processes: list[dict],
        industry: Optional[str] = None,
        budget: Optional[float] = None,
        risk_tolerance: str = "balanced",
    ) -> dict:
        """Analyze a full portfolio and generate strategic recommendations."""
        # Score all processes
        scoring_result = self.scoring_engine.score_portfolio(processes, run_simulation=True)
        scored_processes = [
            {"process": proc, "prediction": r["prediction"], "simulation": r.get("simulation")}
            for proc, r in zip(processes, scoring_result["results"])
        ]

        result = {
            "portfolio_scoring": scoring_result,
            "scored_count": len(scored_processes),
        }

        if self.advisor_agent:
            # Quick wins
            result["quick_wins"] = self.advisor_agent.identify_quick_wins(scored_processes)

            # Strategic themes
            result["strategic_themes"] = self.advisor_agent.detect_strategic_themes(scored_processes)

            # Portfolio recommendation (if budget provided)
            if budget:
                portfolio_rec = self.advisor_agent.recommend_portfolio(
                    scored_processes, budget=budget, risk_tolerance=risk_tolerance,
                )
                result["recommended_portfolio"] = portfolio_rec.to_dict()

            # Roadmap
            roadmap = self.advisor_agent.generate_roadmap(
                scored_processes, budget=budget,
            )
            result["roadmap"] = roadmap.to_dict()

        return result

    # -- Discovery workflow --

    def discover_from_event_log(
        self,
        events: list[dict],
        organization_id: Optional[str] = None,
        hourly_cost: float = 75.0,
    ) -> dict:
        """Run process mining on event log data and rank automation candidates."""
        if not self.discovery_engine:
            raise RuntimeError("Discovery engine not configured")

        mining_result = self.discovery_engine.mine(
            events=events,
            organization_id=organization_id,
            hourly_cost=hourly_cost,
        )
        return mining_result.to_dict()

    def discover_from_document(
        self,
        document_text: str,
        max_processes: int = 10,
    ) -> list[dict]:
        """Extract processes from a document via NLP + LLM."""
        if not self.nlp_engine:
            raise RuntimeError("NLP engine not configured")

        processes = self.nlp_engine.extract_processes_from_text(
            document_text, max_processes=max_processes,
        )
        return processes

    # -- Learning loop workflow --

    def record_and_learn(
        self,
        trace_id: str,
        actual_roi: float,
        actual_savings: float,
        actual_cost: float,
        actual_payback_months: float,
        lessons_learned: Optional[str] = None,
    ) -> dict:
        """
        Record actual outcome, detect drift, generate alerts.
        Feeds data back into the learning loop.
        """
        if not self.monitor_agent:
            raise RuntimeError("Monitor agent not configured")

        outcome = self.monitor_agent.record_outcome(
            trace_id,
            actual_roi,
            actual_savings,
            actual_cost,
            actual_payback_months,
            lessons_learned=lessons_learned,
        )
        return outcome

    def get_model_health(self, traces: list[dict]) -> dict:
        """Overall model health report — accuracy, drift, calibration."""
        if not self.monitor_agent:
            return {"status": "monitor_agent_unavailable"}

        metrics = self.monitor_agent.compute_accuracy(traces)
        insights = self.monitor_agent.generate_learning_insights(traces)

        return {
            "accuracy_metrics": metrics.to_dict() if metrics else None,
            "learning_insights": insights,
            "model_version": self.scoring_engine.active_model_version,
        }
