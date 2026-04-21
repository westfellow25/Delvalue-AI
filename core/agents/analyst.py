"""
DelValue AI — Analyst Agent

Primary AI agent that performs deep process analysis.
Combines ML scoring + Monte Carlo + benchmarks with LLM reasoning for
executive-quality insights.

The LLM is used ONLY for reasoning and narrative generation. All numbers
come from the deterministic engines — this separation is critical for
enterprise trust (reproducible, auditable quantitative analysis).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    prediction: dict
    simulation: Optional[dict]
    benchmark: Optional[dict]
    executive_summary: str
    detailed_reasoning: str
    implementation_plan: list[str]
    risk_analysis: list[str]
    success_factors: list[str]
    model_version: str

    def to_dict(self) -> dict:
        return {
            "prediction": self.prediction,
            "simulation": self.simulation,
            "benchmark": self.benchmark,
            "executive_summary": self.executive_summary,
            "detailed_reasoning": self.detailed_reasoning,
            "implementation_plan": self.implementation_plan,
            "risk_analysis": self.risk_analysis,
            "success_factors": self.success_factors,
            "model_version": self.model_version,
        }


class AnalystAgent:
    """Deep process analysis agent with LLM-powered narrative."""

    SYSTEM_PROMPT = """You are a senior automation transformation advisor at a top-tier consulting firm.
You analyze business processes for automation potential and provide executive-grade recommendations.

Your analysis is:
- Quantitatively grounded (you cite specific numbers from the analysis)
- Honest about uncertainty (you reference probability distributions)
- Actionable (you provide concrete next steps)
- Industry-contextualized (you compare to benchmarks)

Always return structured output in the requested format. Never invent numbers —
only use values provided in the analysis context."""

    def __init__(
        self,
        scoring_engine,
        benchmark_engine=None,
        llm_client=None,
        default_model: str = "claude-sonnet-4-20250514",
    ):
        self.scoring_engine = scoring_engine
        self.benchmark_engine = benchmark_engine
        self.llm_client = llm_client
        self.default_model = default_model

    def analyze(
        self,
        process_data: dict,
        run_simulation: bool = True,
        run_benchmark: bool = True,
        industry: Optional[str] = None,
        simulation_iterations: int = 10_000,
        include_llm_narrative: bool = True,
    ) -> AnalysisResult:
        """
        Full deep analysis of a process.
        """
        # Step 1: Score + Simulate
        scoring = self.scoring_engine.score_process(
            process_data,
            run_simulation=run_simulation,
            simulation_iterations=simulation_iterations,
        )

        # Step 2: Benchmark comparison
        benchmark_dict = None
        if run_benchmark and self.benchmark_engine:
            benchmark = self.benchmark_engine.compare(
                category=process_data.get("category", "operations"),
                process_roi=scoring["prediction"]["estimated_roi"],
                process_savings=scoring["prediction"]["estimated_annual_savings"],
                process_payback_months=scoring["prediction"]["estimated_payback_months"],
                industry=industry,
            )
            if benchmark:
                benchmark_dict = benchmark.to_dict()

        # Step 3: Generate narrative (LLM or template)
        if include_llm_narrative and self.llm_client:
            narrative = self._generate_llm_narrative(process_data, scoring, benchmark_dict)
        else:
            narrative = self._generate_template_narrative(process_data, scoring, benchmark_dict)

        return AnalysisResult(
            prediction=scoring["prediction"],
            simulation=scoring.get("simulation"),
            benchmark=benchmark_dict,
            executive_summary=narrative["executive_summary"],
            detailed_reasoning=narrative["detailed_reasoning"],
            implementation_plan=narrative["implementation_plan"],
            risk_analysis=narrative["risk_analysis"],
            success_factors=narrative["success_factors"],
            model_version=scoring["model"]["version"],
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=False,
    )
    def _generate_llm_narrative(
        self,
        process_data: dict,
        scoring: dict,
        benchmark: Optional[dict],
    ) -> dict:
        """Use LLM to generate executive-quality narrative from the numbers."""
        context = self._build_analysis_context(process_data, scoring, benchmark)

        prompt = f"""Analyze this business process for automation and provide an executive summary.

Process context and quantitative analysis:
{context}

Provide your response in this JSON format (no markdown, no commentary, just JSON):
{{
  "executive_summary": "3-4 sentence summary with specific numbers. Start with the recommendation.",
  "detailed_reasoning": "2 paragraph analysis explaining the scoring, uncertainty, and benchmark positioning.",
  "implementation_plan": ["4-6 concrete next steps as short bullets"],
  "risk_analysis": ["3-5 specific risks with their mitigation"],
  "success_factors": ["3-5 critical success factors"]
}}"""

        try:
            response = self.llm_client.messages.create(
                model=self.default_model,
                max_tokens=2048,
                temperature=0.3,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text if response.content else "{}"
            import json, re
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"LLM narrative generation failed: {e} — falling back to template")
            return self._generate_template_narrative(process_data, scoring, benchmark)

    def _generate_template_narrative(
        self,
        process_data: dict,
        scoring: dict,
        benchmark: Optional[dict],
    ) -> dict:
        """Template-based narrative (fallback when no LLM)."""
        pred = scoring["prediction"]
        name = process_data.get("name", "This process")

        recommendation_text = {
            "automate_now": "Strongly recommended for immediate automation.",
            "strong_candidate": "Strong automation candidate — prioritize for next quarter.",
            "investigate_further": "Warrants deeper investigation before committing.",
            "defer": "Defer automation — conditions are not yet favorable.",
            "not_recommended": "Not recommended for automation at this time.",
        }.get(pred["recommendation"], "Review recommended.")

        exec_summary = (
            f"{recommendation_text} {name} scores {pred['overall_score']:.2f} "
            f"overall with an expected ROI of {pred['estimated_roi']:.0f}% and "
            f"estimated annual savings of ${pred['estimated_annual_savings']:,.0f}. "
            f"Model confidence: {pred['confidence']:.0%}."
        )

        sim = scoring.get("simulation")
        sim_text = ""
        if sim:
            prob = sim["probabilities"]["positive_roi"]
            p10 = sim["roi"]["percentiles"].get("p10", 0)
            p90 = sim["roi"]["percentiles"].get("p90", 0)
            sim_text = (
                f" Monte Carlo simulation (10k iterations) shows {prob:.0%} probability "
                f"of positive ROI with 80% confidence interval of [{p10:.0f}%, {p90:.0f}%]."
            )

        bench_text = ""
        if benchmark:
            pos = benchmark["positioning"]
            bench_text = (
                f" Relative to industry peers ({benchmark['sample_size']} companies), "
                f"this process ranks in the {pos['roi_percentile']:.0f}th percentile "
                f"({pos['tier']})."
            )

        detailed = (
            f"The scoring engine assessed this process across four dimensions: "
            f"feasibility ({pred['feasibility_score']:.2f}), value "
            f"({pred['value_score']:.2f}), risk ({pred['risk_score']:.2f}), and "
            f"complexity ({pred['complexity_score']:.2f}). "
            f"Implementation is projected to cost ${pred['estimated_implementation_cost']:,.0f} "
            f"with a payback period of {pred['estimated_payback_months']:.1f} months.{sim_text}"
            f"{bench_text}"
        )

        plan = [
            "Validate process documentation and data quality",
            "Engage key stakeholders and process owners",
            "Define success metrics and acceptance criteria",
            "Pilot on a representative subset (2-4 weeks)",
            "Measure actuals vs predictions and scale if targets are met",
        ]

        risks = [
            f"Complexity score of {pred['complexity_score']:.2f} indicates potential integration challenges",
            f"Risk level '{pred['risk_level']}' warrants close change management",
            "Data quality and process documentation must be validated before build",
        ]

        success_factors = [
            "Executive sponsorship and clear ownership",
            "Dedicated implementation team (business + IT)",
            "Strong change management and user training",
            "Measurable KPIs tracked from pilot through scale",
        ]

        return {
            "executive_summary": exec_summary,
            "detailed_reasoning": detailed,
            "implementation_plan": plan,
            "risk_analysis": risks,
            "success_factors": success_factors,
        }

    @staticmethod
    def _build_analysis_context(
        process_data: dict,
        scoring: dict,
        benchmark: Optional[dict],
    ) -> str:
        """Build a structured context string for the LLM."""
        pred = scoring["prediction"]
        lines = [
            f"Process: {process_data.get('name', 'Unknown')}",
            f"Category: {process_data.get('category', 'unknown')}",
            f"Annual volume: {process_data.get('annual_volume', 0):,}",
            f"People involved: {process_data.get('people_involved', 0)}",
            "",
            "Scores (0-1):",
            f"  Overall: {pred['overall_score']:.3f}",
            f"  Feasibility: {pred['feasibility_score']:.3f}",
            f"  Value: {pred['value_score']:.3f}",
            f"  Risk: {pred['risk_score']:.3f}",
            f"  Complexity: {pred['complexity_score']:.3f}",
            "",
            "Financial projections:",
            f"  Annual savings: ${pred['estimated_annual_savings']:,.0f}",
            f"  Implementation cost: ${pred['estimated_implementation_cost']:,.0f}",
            f"  ROI: {pred['estimated_roi']:.1f}%",
            f"  Payback: {pred['estimated_payback_months']:.1f} months",
            f"  Confidence: {pred['confidence']:.0%}",
            "",
            f"Recommendation: {pred['recommendation']}",
            f"Automation feasibility: {pred['automation_feasibility']}",
            f"Risk level: {pred['risk_level']}",
        ]

        sim = scoring.get("simulation")
        if sim:
            lines.extend([
                "",
                "Monte Carlo simulation (10k iterations):",
                f"  ROI 10th percentile: {sim['roi']['percentiles'].get('p10', 0):.1f}%",
                f"  ROI 50th percentile: {sim['roi']['percentiles'].get('p50', 0):.1f}%",
                f"  ROI 90th percentile: {sim['roi']['percentiles'].get('p90', 0):.1f}%",
                f"  Prob. positive ROI: {sim['probabilities']['positive_roi']:.1%}",
                f"  Prob. ROI > 100%: {sim['probabilities']['roi_above_100']:.1%}",
                f"  Value at Risk (5%): {sim['risk']['value_at_risk_5pct']:.1f}%",
                f"  NPV mean: ${sim['npv']['mean']:,.0f}",
            ])

        if benchmark:
            lines.extend([
                "",
                f"Industry benchmark ({benchmark['sample_size']} companies):",
                f"  Industry avg ROI: {benchmark['industry_benchmarks']['avg_roi']:.1f}%",
                f"  Industry median ROI: {benchmark['industry_benchmarks']['median_roi']:.1f}%",
                f"  This process percentile: {benchmark['positioning']['roi_percentile']:.0f}th",
                f"  Positioning: {benchmark['positioning']['tier']}",
                f"  Success rate: {benchmark['industry_benchmarks']['success_rate']:.0%}",
            ])

        return "\n".join(lines)
