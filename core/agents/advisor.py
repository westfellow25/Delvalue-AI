"""
DelValue AI — Advisor Agent

Strategic recommendations agent. Portfolio-level analysis:
  - Optimal portfolio selection under budget/capacity constraints (knapsack)
  - Phased implementation roadmap
  - Quick wins identification
  - Strategic theme detection across processes
  - Quarterly business review generation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PortfolioRecommendation:
    selected_processes: list[dict]
    total_investment: float
    total_expected_savings: float
    portfolio_roi: float
    portfolio_risk_score: float
    rationale: str

    def to_dict(self) -> dict:
        return {
            "selected_processes": self.selected_processes,
            "total_investment": self.total_investment,
            "total_expected_savings": self.total_expected_savings,
            "portfolio_roi": self.portfolio_roi,
            "portfolio_risk_score": self.portfolio_risk_score,
            "rationale": self.rationale,
        }


@dataclass
class Roadmap:
    phases: list[dict]
    total_duration_months: int
    total_investment: float
    total_expected_savings: float

    def to_dict(self) -> dict:
        return {
            "phases": self.phases,
            "total_duration_months": self.total_duration_months,
            "total_investment": self.total_investment,
            "total_expected_savings": self.total_expected_savings,
        }


class AdvisorAgent:
    """
    Portfolio-level strategic advisor.
    Works on top of individual process scores.
    """

    def __init__(self, llm_client=None, default_model: str = "claude-sonnet-4-20250514"):
        self.llm_client = llm_client
        self.default_model = default_model

    # -- Portfolio optimization --

    def recommend_portfolio(
        self,
        scored_processes: list[dict],
        budget: float,
        max_parallel_implementations: int = 5,
        min_confidence: float = 0.5,
        risk_tolerance: str = "balanced",  # conservative|balanced|aggressive
    ) -> PortfolioRecommendation:
        """
        Select optimal portfolio under constraints using greedy knapsack.

        Scored_processes format: list of dicts with 'process' and 'prediction' keys.
        """
        # Filter by confidence threshold
        candidates = [
            p for p in scored_processes
            if p["prediction"]["confidence"] >= min_confidence
        ]

        # Compute efficiency score (savings/cost, risk-adjusted)
        risk_penalty = {
            "conservative": 0.5,
            "balanced": 0.3,
            "aggressive": 0.1,
        }.get(risk_tolerance, 0.3)

        for c in candidates:
            pred = c["prediction"]
            cost = max(pred["estimated_implementation_cost"], 1)
            efficiency = pred["estimated_annual_savings"] / cost
            risk_adj = efficiency * (1 - risk_penalty * pred["risk_score"])
            c["_efficiency"] = risk_adj
            c["_cost"] = cost

        # Sort by risk-adjusted efficiency
        candidates.sort(key=lambda c: c["_efficiency"], reverse=True)

        # Greedy selection under budget + parallel constraints
        selected = []
        remaining_budget = budget
        for c in candidates:
            if len(selected) >= max_parallel_implementations:
                break
            if c["_cost"] > remaining_budget:
                continue
            selected.append(c)
            remaining_budget -= c["_cost"]

        total_cost = sum(p["_cost"] for p in selected)
        total_savings = sum(p["prediction"]["estimated_annual_savings"] for p in selected)
        portfolio_roi = ((total_savings - total_cost) / max(total_cost, 1)) * 100
        avg_risk = sum(p["prediction"]["risk_score"] for p in selected) / max(len(selected), 1)

        rationale = self._build_portfolio_rationale(
            selected, total_cost, total_savings, portfolio_roi, budget, risk_tolerance,
        )

        return PortfolioRecommendation(
            selected_processes=[{
                "name": p.get("process", {}).get("name", "Unknown"),
                "estimated_savings": p["prediction"]["estimated_annual_savings"],
                "estimated_cost": p["prediction"]["estimated_implementation_cost"],
                "roi": p["prediction"]["estimated_roi"],
                "confidence": p["prediction"]["confidence"],
                "risk_level": p["prediction"]["risk_level"],
            } for p in selected],
            total_investment=total_cost,
            total_expected_savings=total_savings,
            portfolio_roi=portfolio_roi,
            portfolio_risk_score=avg_risk,
            rationale=rationale,
        )

    @staticmethod
    def _build_portfolio_rationale(
        selected, total_cost, total_savings, roi, budget, risk_tolerance,
    ) -> str:
        utilization = (total_cost / max(budget, 1)) * 100
        return (
            f"Selected {len(selected)} processes consuming ${total_cost:,.0f} "
            f"({utilization:.0f}% of ${budget:,.0f} budget) with expected annual "
            f"savings of ${total_savings:,.0f} (portfolio ROI: {roi:.0f}%). "
            f"Selection optimized for {risk_tolerance} risk tolerance using "
            f"risk-adjusted savings/cost ratio."
        )

    # -- Quick wins --

    def identify_quick_wins(
        self,
        scored_processes: list[dict],
        max_payback_months: float = 12.0,
        min_confidence: float = 0.6,
        max_cost: float = 100_000,
    ) -> list[dict]:
        """Find high-ROI, low-risk, short-payback opportunities."""
        quick_wins = []
        for p in scored_processes:
            pred = p["prediction"]
            if (pred["estimated_payback_months"] <= max_payback_months
                and pred["confidence"] >= min_confidence
                and pred["estimated_implementation_cost"] <= max_cost
                and pred["risk_score"] < 0.5
                and pred["recommendation"] in ("automate_now", "strong_candidate")):
                quick_wins.append({
                    "name": p.get("process", {}).get("name", "Unknown"),
                    "estimated_savings": pred["estimated_annual_savings"],
                    "estimated_cost": pred["estimated_implementation_cost"],
                    "payback_months": pred["estimated_payback_months"],
                    "confidence": pred["confidence"],
                    "rationale": (
                        f"${pred['estimated_annual_savings']:,.0f} annual savings "
                        f"for ${pred['estimated_implementation_cost']:,.0f} investment, "
                        f"payback in {pred['estimated_payback_months']:.1f} months "
                        f"with {pred['confidence']:.0%} confidence."
                    ),
                })
        quick_wins.sort(key=lambda x: x["payback_months"])
        return quick_wins

    # -- Roadmap generation --

    def generate_roadmap(
        self,
        scored_processes: list[dict],
        horizon_months: int = 18,
        max_concurrent: int = 3,
        budget: Optional[float] = None,
    ) -> Roadmap:
        """Generate a phased implementation roadmap."""
        # Filter eligible processes
        eligible = [
            p for p in scored_processes
            if p["prediction"]["recommendation"] in ("automate_now", "strong_candidate")
        ]
        # Sort by ROI (highest first)
        eligible.sort(key=lambda p: p["prediction"]["estimated_roi"], reverse=True)

        # Phase 1 (months 1-6): Quick wins
        # Phase 2 (months 7-12): Medium complexity
        # Phase 3 (months 13-18): Strategic initiatives

        phases = [
            {
                "name": "Quick Wins",
                "months": "1-6",
                "focus": "Fast payback, low risk",
                "processes": [],
                "expected_savings": 0,
                "investment": 0,
            },
            {
                "name": "Scale Automation",
                "months": "7-12",
                "focus": "Proven patterns, expanded scope",
                "processes": [],
                "expected_savings": 0,
                "investment": 0,
            },
            {
                "name": "Strategic Transformation",
                "months": "13-18",
                "focus": "Complex, high-value initiatives",
                "processes": [],
                "expected_savings": 0,
                "investment": 0,
            },
        ]

        remaining_budget = budget or float("inf")
        for p in eligible:
            pred = p["prediction"]
            cost = pred["estimated_implementation_cost"]
            if cost > remaining_budget:
                continue

            # Phase assignment based on payback + complexity
            if pred["estimated_payback_months"] <= 6 and pred["complexity_score"] < 0.4:
                phase_idx = 0
            elif pred["estimated_payback_months"] <= 12 and pred["complexity_score"] < 0.6:
                phase_idx = 1
            else:
                phase_idx = 2

            if len(phases[phase_idx]["processes"]) >= max_concurrent * 2:
                continue

            phases[phase_idx]["processes"].append({
                "name": p.get("process", {}).get("name", "Unknown"),
                "roi": pred["estimated_roi"],
                "savings": pred["estimated_annual_savings"],
                "cost": cost,
            })
            phases[phase_idx]["expected_savings"] += pred["estimated_annual_savings"]
            phases[phase_idx]["investment"] += cost
            remaining_budget -= cost

        total_cost = sum(phase["investment"] for phase in phases)
        total_savings = sum(phase["expected_savings"] for phase in phases)

        return Roadmap(
            phases=phases,
            total_duration_months=horizon_months,
            total_investment=total_cost,
            total_expected_savings=total_savings,
        )

    # -- Strategic initiatives --

    def detect_strategic_themes(
        self,
        scored_processes: list[dict],
    ) -> list[dict]:
        """Find cross-cutting themes across multiple processes."""
        from collections import defaultdict

        category_stats = defaultdict(lambda: {
            "count": 0,
            "total_savings": 0,
            "processes": [],
        })

        for p in scored_processes:
            cat = p.get("process", {}).get("category", "unknown")
            category_stats[cat]["count"] += 1
            category_stats[cat]["total_savings"] += p["prediction"]["estimated_annual_savings"]
            category_stats[cat]["processes"].append(
                p.get("process", {}).get("name", "Unknown")
            )

        themes = []
        for cat, stats in category_stats.items():
            if stats["count"] >= 3 and stats["total_savings"] > 500_000:
                themes.append({
                    "category": cat,
                    "process_count": stats["count"],
                    "total_potential_savings": stats["total_savings"],
                    "description": (
                        f"Strategic opportunity in {cat}: {stats['count']} related "
                        f"processes totaling ${stats['total_savings']:,.0f} in potential "
                        f"annual savings. Consider a unified {cat} transformation program."
                    ),
                    "example_processes": stats["processes"][:5],
                })

        themes.sort(key=lambda t: t["total_potential_savings"], reverse=True)
        return themes

    # -- Quarterly review --

    def generate_quarterly_review(
        self,
        portfolio_summary: dict,
        completed_implementations: list[dict],
        active_implementations: list[dict],
        quarter_label: str,
    ) -> dict:
        """Generate a quarterly business review report."""
        total_delivered = sum(i.get("actual_annual_savings", 0) for i in completed_implementations)
        total_predicted = sum(i.get("predicted_annual_savings", 0) for i in completed_implementations)
        variance_pct = (
            ((total_delivered - total_predicted) / total_predicted * 100)
            if total_predicted > 0 else 0
        )

        return {
            "quarter": quarter_label,
            "summary": {
                "completed_implementations": len(completed_implementations),
                "active_implementations": len(active_implementations),
                "total_portfolio_value": portfolio_summary.get("total_potential_savings", 0),
                "savings_delivered": total_delivered,
                "savings_predicted": total_predicted,
                "variance_pct": variance_pct,
                "prediction_accuracy": (
                    max(0, 100 - abs(variance_pct))
                    if total_predicted > 0 else None
                ),
            },
            "completed": [
                {
                    "name": i.get("process_name", "Unknown"),
                    "predicted_savings": i.get("predicted_annual_savings", 0),
                    "actual_savings": i.get("actual_annual_savings", 0),
                    "variance": i.get("variance_savings", 0),
                }
                for i in completed_implementations
            ],
            "active": [
                {
                    "name": i.get("process_name", "Unknown"),
                    "status": i.get("implementation_status", "unknown"),
                    "predicted_completion": i.get("predicted_completion"),
                }
                for i in active_implementations
            ],
            "key_takeaways": self._generate_takeaways(
                variance_pct, total_delivered, len(completed_implementations),
            ),
        }

    @staticmethod
    def _generate_takeaways(variance_pct: float, delivered: float, count: int) -> list[str]:
        takeaways = []
        if count == 0:
            takeaways.append("No implementations completed this quarter — focus on execution velocity.")
            return takeaways

        if variance_pct > 10:
            takeaways.append(
                f"Outperformed predictions by {variance_pct:.1f}% — model is conservative, "
                "consider raising confidence thresholds."
            )
        elif variance_pct < -10:
            takeaways.append(
                f"Underperformed predictions by {abs(variance_pct):.1f}% — recalibrate "
                "the scoring model with recent outcome data."
            )
        else:
            takeaways.append(
                f"Predictions within {abs(variance_pct):.1f}% of actual — model is well-calibrated."
            )

        takeaways.append(
            f"${delivered:,.0f} in savings delivered across {count} implementations."
        )
        return takeaways
