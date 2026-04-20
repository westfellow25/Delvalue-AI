"""
DelValue AI — Scoring Engine Orchestrator

Orchestrates the full scoring pipeline:
  1. Feature extraction
  2. ML model prediction (or heuristic fallback)
  3. Monte Carlo simulation
  4. Benchmark comparison
  5. Result assembly and persistence

Handles cold-start gracefully: starts with heuristics, transitions to ML
as outcome data accumulates.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from core.ml.features import extract_features, FeatureVector
from core.ml.models import HeuristicScoringModel, MLScoringModel, PredictionResult
from core.engines.simulation import MonteCarloEngine, SimulationConfig, SimulationResult

logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Unified scoring engine — the primary entry point for all process analysis.

    Strategy pattern: uses ML model when trained, heuristic model otherwise.
    Always runs Monte Carlo simulation for uncertainty quantification.
    """

    def __init__(
        self,
        ml_model: Optional[MLScoringModel] = None,
        heuristic_model: Optional[HeuristicScoringModel] = None,
        simulation_engine: Optional[MonteCarloEngine] = None,
        use_ml: bool = True,
    ):
        self.ml_model = ml_model
        self.heuristic_model = heuristic_model or HeuristicScoringModel()
        self.simulation_engine = simulation_engine or MonteCarloEngine()
        self.use_ml = use_ml

    @property
    def active_model_version(self) -> str:
        if self.use_ml and self.ml_model and self.ml_model.is_trained:
            return self.ml_model.version
        return self.heuristic_model.VERSION

    def score_process(
        self,
        process_data: dict,
        run_simulation: bool = True,
        simulation_iterations: int = 10_000,
    ) -> dict:
        """
        Score a single process end-to-end.

        Args:
            process_data: Dict with process attributes
            run_simulation: Whether to run Monte Carlo simulation
            simulation_iterations: Number of simulation iterations

        Returns:
            Complete scoring result with prediction, simulation, and metadata
        """
        # Step 1: Feature extraction
        features = extract_features(process_data)

        # Step 2: Model prediction
        if self.use_ml and self.ml_model and self.ml_model.is_trained:
            prediction = self.ml_model.predict(features)
            model_type = "ml"
        else:
            prediction = self.heuristic_model.predict(features)
            model_type = "heuristic"

        # Step 3: Monte Carlo simulation
        simulation = None
        if run_simulation:
            sim_config = SimulationConfig(iterations=simulation_iterations)
            sim_engine = MonteCarloEngine(config=sim_config)
            simulation = sim_engine.simulate(
                base_savings=prediction.estimated_annual_savings,
                base_cost=prediction.estimated_implementation_cost,
                base_duration_months=prediction.estimated_payback_months,
                automation_rate=prediction.feasibility_score,
                complexity_factor=prediction.complexity_score,
                confidence_level=prediction.confidence,
            )

        # Step 4: Assemble result
        result = self._assemble_result(prediction, simulation, features, model_type)
        return result

    def score_portfolio(
        self,
        processes: list[dict],
        run_simulation: bool = True,
        budget_constraint: Optional[float] = None,
    ) -> dict:
        """Score multiple processes and return portfolio analysis."""
        results = []
        for process_data in processes:
            result = self.score_process(process_data, run_simulation=run_simulation)
            results.append(result)

        # Sort by overall score
        results.sort(key=lambda r: r["prediction"]["overall_score"], reverse=True)

        # Portfolio summary
        total_savings = sum(r["prediction"]["estimated_annual_savings"] for r in results)
        total_cost = sum(r["prediction"]["estimated_implementation_cost"] for r in results)
        avg_roi = sum(r["prediction"]["estimated_roi"] for r in results) / max(len(results), 1)
        avg_confidence = sum(r["prediction"]["confidence"] for r in results) / max(len(results), 1)

        # Category breakdown
        categories = {}
        for r in results:
            cat = r.get("process_category", "unknown")
            if cat not in categories:
                categories[cat] = {"count": 0, "total_savings": 0, "avg_score": 0}
            categories[cat]["count"] += 1
            categories[cat]["total_savings"] += r["prediction"]["estimated_annual_savings"]
            categories[cat]["avg_score"] += r["prediction"]["overall_score"]
        for cat in categories:
            categories[cat]["avg_score"] /= categories[cat]["count"]

        # Recommendation distribution
        rec_counts = {}
        for r in results:
            rec = r["prediction"]["recommendation"]
            rec_counts[rec] = rec_counts.get(rec, 0) + 1

        return {
            "results": results,
            "summary": {
                "total_processes": len(results),
                "total_potential_savings": round(total_savings, 2),
                "total_implementation_cost": round(total_cost, 2),
                "portfolio_roi": round(
                    ((total_savings - total_cost) / max(total_cost, 1)) * 100, 2
                ),
                "average_roi": round(avg_roi, 2),
                "average_confidence": round(avg_confidence, 4),
                "recommendation_distribution": rec_counts,
                "category_breakdown": categories,
            },
            "model_version": self.active_model_version,
        }

    def compare_processes(self, processes: list[dict]) -> dict:
        """Side-by-side comparison of multiple processes."""
        results = [self.score_process(p) for p in processes]

        comparison = {
            "processes": [],
            "rankings": {
                "by_overall_score": [],
                "by_roi": [],
                "by_savings": [],
                "by_risk": [],
                "by_confidence": [],
            },
        }

        for i, (proc, result) in enumerate(zip(processes, results)):
            comparison["processes"].append({
                "index": i,
                "name": proc.get("name", f"Process {i+1}"),
                "prediction": result["prediction"],
                "simulation_summary": result.get("simulation_summary"),
            })

        # Rankings
        indices = list(range(len(results)))
        comparison["rankings"]["by_overall_score"] = sorted(
            indices, key=lambda i: results[i]["prediction"]["overall_score"], reverse=True
        )
        comparison["rankings"]["by_roi"] = sorted(
            indices, key=lambda i: results[i]["prediction"]["estimated_roi"], reverse=True
        )
        comparison["rankings"]["by_savings"] = sorted(
            indices, key=lambda i: results[i]["prediction"]["estimated_annual_savings"], reverse=True
        )
        comparison["rankings"]["by_risk"] = sorted(
            indices, key=lambda i: results[i]["prediction"]["risk_score"]
        )
        comparison["rankings"]["by_confidence"] = sorted(
            indices, key=lambda i: results[i]["prediction"]["confidence"], reverse=True
        )

        return comparison

    def _assemble_result(
        self,
        prediction: PredictionResult,
        simulation: Optional[SimulationResult],
        features: FeatureVector,
        model_type: str,
    ) -> dict:
        """Assemble the complete scoring result."""
        result = {
            "prediction": {
                "overall_score": prediction.overall_score,
                "feasibility_score": prediction.feasibility_score,
                "value_score": prediction.value_score,
                "risk_score": prediction.risk_score,
                "complexity_score": prediction.complexity_score,
                "estimated_annual_savings": prediction.estimated_annual_savings,
                "estimated_implementation_cost": prediction.estimated_implementation_cost,
                "estimated_roi": prediction.estimated_roi,
                "estimated_payback_months": prediction.estimated_payback_months,
                "confidence": prediction.confidence,
                "prediction_interval": {
                    "lower": prediction.prediction_interval_lower,
                    "upper": prediction.prediction_interval_upper,
                },
                "recommendation": prediction.recommendation,
                "automation_feasibility": prediction.automation_feasibility,
                "risk_level": prediction.risk_level,
            },
            "model": {
                "type": model_type,
                "version": prediction.model_version,
            },
            "features": features.to_dict(),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        if simulation:
            result["simulation"] = simulation.to_dict()
            result["simulation_summary"] = {
                "roi_p10": simulation.roi_percentiles.get("p10", 0),
                "roi_p50": simulation.roi_percentiles.get("p50", 0),
                "roi_p90": simulation.roi_percentiles.get("p90", 0),
                "prob_positive_roi": simulation.prob_positive_roi,
                "prob_roi_above_100": simulation.prob_roi_above_100,
                "value_at_risk": simulation.value_at_risk_5pct,
                "npv_mean": simulation.npv_mean,
            }

        return result
