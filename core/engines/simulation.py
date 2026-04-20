"""
DelValue AI — Monte Carlo Simulation Engine

Runs 10,000+ simulations to quantify uncertainty in automation ROI predictions.
Uses calibrated probability distributions for each uncertain parameter.

This is a key competitive differentiator — most competitors give point estimates.
We give full probability distributions with confidence intervals.

Distribution choices:
  - Savings: LogNormal (right-skewed, always positive)
  - Costs: LogNormal (implementation costs skew right — overruns are common)
  - Timeline: Triangular (bounded with mode — expert judgment)
  - Automation rate: Beta (bounded 0-1, flexible shape)
  - Adoption rate: Beta (bounded 0-1, S-curve characteristics)
  - Error reduction: Beta (bounded improvement %)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy import stats


@dataclass
class DistributionParams:
    """Parameters for a probability distribution."""

    name: str
    distribution: str  # lognormal, beta, triangular, normal, uniform
    params: dict[str, float]
    description: str = ""


@dataclass
class SimulationConfig:
    """Configuration for a single simulation run."""

    iterations: int = 10_000
    seed: Optional[int] = None
    confidence_levels: list[float] = field(
        default_factory=lambda: [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
    )
    discount_rate: float = 0.10  # annual discount rate for NPV
    time_horizon_years: int = 3


@dataclass
class SimulationResult:
    """Complete output of a Monte Carlo simulation run."""

    # Summary statistics
    roi_mean: float
    roi_std: float
    roi_median: float
    roi_percentiles: dict[str, float]  # {"p5": ..., "p10": ..., etc.}

    savings_mean: float
    savings_std: float
    savings_percentiles: dict[str, float]

    cost_mean: float
    cost_std: float
    cost_percentiles: dict[str, float]

    payback_mean: float
    payback_median: float
    payback_percentiles: dict[str, float]

    # Probability metrics (the real value)
    prob_positive_roi: float
    prob_roi_above_50: float
    prob_roi_above_100: float
    prob_roi_above_200: float
    prob_payback_under_6mo: float
    prob_payback_under_12mo: float
    prob_payback_under_24mo: float

    # Risk metrics
    value_at_risk_5pct: float  # VaR at 5% — worst-case ROI
    conditional_var_5pct: float  # CVaR — expected loss in worst 5%
    max_loss: float
    downside_deviation: float

    # NPV analysis
    npv_mean: float
    npv_percentiles: dict[str, float]
    prob_positive_npv: float
    irr_mean: float

    # Distribution data (for charts)
    roi_histogram: dict  # bins + counts
    savings_histogram: dict
    cost_histogram: dict

    # Metadata
    num_iterations: int
    seed: Optional[int]
    run_duration_ms: int
    input_distributions: list[dict]

    def to_dict(self) -> dict:
        return {
            "roi": {
                "mean": self.roi_mean,
                "std": self.roi_std,
                "median": self.roi_median,
                "percentiles": self.roi_percentiles,
            },
            "savings": {
                "mean": self.savings_mean,
                "std": self.savings_std,
                "percentiles": self.savings_percentiles,
            },
            "cost": {
                "mean": self.cost_mean,
                "std": self.cost_std,
                "percentiles": self.cost_percentiles,
            },
            "payback": {
                "mean": self.payback_mean,
                "median": self.payback_median,
                "percentiles": self.payback_percentiles,
            },
            "probabilities": {
                "positive_roi": self.prob_positive_roi,
                "roi_above_50": self.prob_roi_above_50,
                "roi_above_100": self.prob_roi_above_100,
                "roi_above_200": self.prob_roi_above_200,
                "payback_under_6mo": self.prob_payback_under_6mo,
                "payback_under_12mo": self.prob_payback_under_12mo,
                "payback_under_24mo": self.prob_payback_under_24mo,
            },
            "risk": {
                "value_at_risk_5pct": self.value_at_risk_5pct,
                "conditional_var_5pct": self.conditional_var_5pct,
                "max_loss": self.max_loss,
                "downside_deviation": self.downside_deviation,
            },
            "npv": {
                "mean": self.npv_mean,
                "percentiles": self.npv_percentiles,
                "prob_positive": self.prob_positive_npv,
                "irr_mean": self.irr_mean,
            },
            "metadata": {
                "num_iterations": self.num_iterations,
                "seed": self.seed,
                "run_duration_ms": self.run_duration_ms,
            },
        }


class MonteCarloEngine:
    """
    Monte Carlo simulation engine for automation ROI uncertainty quantification.

    Generates calibrated probability distributions for all financial projections,
    enabling risk-adjusted decision making.
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()

    def simulate(
        self,
        base_savings: float,
        base_cost: float,
        base_duration_months: float,
        automation_rate: float = 0.6,
        complexity_factor: float = 0.5,
        confidence_level: float = 0.6,
        overrides: Optional[dict] = None,
    ) -> SimulationResult:
        """
        Run Monte Carlo simulation for a process automation scenario.

        Args:
            base_savings: Expected annual savings (point estimate)
            base_cost: Expected implementation cost
            base_duration_months: Expected implementation timeline
            automation_rate: Expected % of process that can be automated (0-1)
            complexity_factor: Process complexity (0=simple, 1=very complex)
            confidence_level: Model confidence in estimates (0-1)
            overrides: Optional parameter overrides

        Returns:
            SimulationResult with full distribution analysis
        """
        start_time = time.perf_counter()

        rng = np.random.default_rng(self.config.seed)
        n = self.config.iterations

        # Build distributions based on process characteristics
        distributions = self._build_distributions(
            base_savings, base_cost, base_duration_months,
            automation_rate, complexity_factor, confidence_level,
            overrides,
        )

        # --- Sample from distributions ---
        # Savings distribution (LogNormal — always positive, right-skewed)
        savings_mu = np.log(max(base_savings, 1000))
        savings_sigma = self._uncertainty_to_sigma(confidence_level, complexity_factor, 0.15, 0.60)
        savings_samples = rng.lognormal(savings_mu, savings_sigma, n)

        # Implementation cost (LogNormal — overruns are right-skewed)
        cost_mu = np.log(max(base_cost, 1000))
        cost_sigma = self._uncertainty_to_sigma(confidence_level, complexity_factor, 0.10, 0.50)
        cost_samples = rng.lognormal(cost_mu, cost_sigma, n)

        # Automation rate (Beta — bounded 0-1)
        ar_alpha, ar_beta = self._rate_to_beta_params(automation_rate, confidence_level)
        automation_samples = rng.beta(ar_alpha, ar_beta, n)

        # Adoption rate (Beta — how much of potential savings is realized)
        adoption_base = 0.80 - 0.30 * complexity_factor  # simpler processes have higher adoption
        ad_alpha, ad_beta = self._rate_to_beta_params(adoption_base, confidence_level)
        adoption_samples = rng.beta(ad_alpha, ad_beta, n)

        # Implementation timeline multiplier (Triangular — expert judgment)
        timeline_low = 0.7
        timeline_mode = 1.0
        timeline_high = 1.5 + 1.0 * complexity_factor  # more complex = more risk of overrun
        timeline_samples = rng.triangular(timeline_low, timeline_mode, timeline_high, n)

        # --- Compute derived quantities ---
        # Actual annual savings = base * automation_rate * adoption_rate
        actual_savings = savings_samples * automation_samples * adoption_samples

        # Actual implementation cost (adjusted by timeline overruns)
        actual_cost = cost_samples * (0.7 + 0.3 * timeline_samples)

        # Actual implementation duration
        actual_duration = base_duration_months * timeline_samples

        # ROI (%)
        roi_samples = np.where(
            actual_cost > 0,
            ((actual_savings - actual_cost) / actual_cost) * 100,
            0.0,
        )

        # Payback period (months)
        monthly_savings = actual_savings / 12.0
        payback_samples = np.where(
            monthly_savings > 0,
            actual_cost / monthly_savings,
            999.0,
        )

        # NPV calculation (multi-year)
        npv_samples = self._compute_npv(
            actual_savings, actual_cost, actual_duration,
            self.config.discount_rate, self.config.time_horizon_years, n,
        )

        # IRR approximation
        irr_samples = self._compute_irr_approx(actual_savings, actual_cost)

        # --- Compute statistics ---
        confidence_levels = self.config.confidence_levels

        roi_percentiles = self._percentiles(roi_samples, confidence_levels)
        savings_percentiles = self._percentiles(actual_savings, confidence_levels)
        cost_percentiles = self._percentiles(actual_cost, confidence_levels)
        payback_percentiles = self._percentiles(payback_samples, confidence_levels)
        npv_percentiles = self._percentiles(npv_samples, confidence_levels)

        # Risk metrics
        var_5 = float(np.percentile(roi_samples, 5))
        worst_5pct = roi_samples[roi_samples <= var_5]
        cvar_5 = float(np.mean(worst_5pct)) if len(worst_5pct) > 0 else var_5

        negative_returns = roi_samples[roi_samples < 0]
        downside_dev = float(np.std(negative_returns)) if len(negative_returns) > 0 else 0.0

        # Distribution data for charts
        roi_hist = self._histogram(roi_samples, bins=50)
        savings_hist = self._histogram(actual_savings, bins=50)
        cost_hist = self._histogram(actual_cost, bins=50)

        # Input distribution descriptions
        input_dists = [
            {"name": "savings", "type": "lognormal", "mu": float(savings_mu), "sigma": float(savings_sigma)},
            {"name": "cost", "type": "lognormal", "mu": float(cost_mu), "sigma": float(cost_sigma)},
            {"name": "automation_rate", "type": "beta", "alpha": float(ar_alpha), "beta": float(ar_beta)},
            {"name": "adoption_rate", "type": "beta", "alpha": float(ad_alpha), "beta": float(ad_beta)},
            {"name": "timeline", "type": "triangular", "low": timeline_low, "mode": timeline_mode, "high": timeline_high},
        ]

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return SimulationResult(
            roi_mean=float(np.mean(roi_samples)),
            roi_std=float(np.std(roi_samples)),
            roi_median=float(np.median(roi_samples)),
            roi_percentiles=roi_percentiles,
            savings_mean=float(np.mean(actual_savings)),
            savings_std=float(np.std(actual_savings)),
            savings_percentiles=savings_percentiles,
            cost_mean=float(np.mean(actual_cost)),
            cost_std=float(np.std(actual_cost)),
            cost_percentiles=cost_percentiles,
            payback_mean=float(np.mean(payback_samples)),
            payback_median=float(np.median(payback_samples)),
            payback_percentiles=payback_percentiles,
            prob_positive_roi=float(np.mean(roi_samples > 0)),
            prob_roi_above_50=float(np.mean(roi_samples > 50)),
            prob_roi_above_100=float(np.mean(roi_samples > 100)),
            prob_roi_above_200=float(np.mean(roi_samples > 200)),
            prob_payback_under_6mo=float(np.mean(payback_samples < 6)),
            prob_payback_under_12mo=float(np.mean(payback_samples < 12)),
            prob_payback_under_24mo=float(np.mean(payback_samples < 24)),
            value_at_risk_5pct=var_5,
            conditional_var_5pct=cvar_5,
            max_loss=float(np.min(roi_samples)),
            downside_deviation=downside_dev,
            npv_mean=float(np.mean(npv_samples)),
            npv_percentiles=npv_percentiles,
            prob_positive_npv=float(np.mean(npv_samples > 0)),
            irr_mean=float(np.mean(irr_samples)),
            roi_histogram=roi_hist,
            savings_histogram=savings_hist,
            cost_histogram=cost_hist,
            num_iterations=n,
            seed=self.config.seed,
            run_duration_ms=elapsed_ms,
            input_distributions=input_dists,
        )

    def simulate_portfolio(
        self,
        scenarios: list[dict],
        budget_constraint: Optional[float] = None,
    ) -> dict:
        """
        Simulate a portfolio of automation investments.
        Returns efficient frontier and optimal allocation.
        """
        rng = np.random.default_rng(self.config.seed)
        n = self.config.iterations

        portfolio_roi = np.zeros(n)
        portfolio_cost = np.zeros(n)
        portfolio_savings = np.zeros(n)
        individual_results = []

        for scenario in scenarios:
            result = self.simulate(**scenario)
            individual_results.append(result)

        # If budget constraint, compute optimal allocation
        if budget_constraint and budget_constraint > 0:
            frontier = self._compute_efficient_frontier(
                individual_results, budget_constraint, scenarios,
            )
        else:
            frontier = None

        return {
            "individual_results": [r.to_dict() for r in individual_results],
            "efficient_frontier": frontier,
            "total_scenarios": len(scenarios),
        }

    def _build_distributions(
        self,
        base_savings: float,
        base_cost: float,
        base_duration: float,
        automation_rate: float,
        complexity: float,
        confidence: float,
        overrides: Optional[dict],
    ) -> list[DistributionParams]:
        """Build the set of probability distributions for simulation inputs."""
        dists = []

        savings_sigma = self._uncertainty_to_sigma(confidence, complexity, 0.15, 0.60)
        dists.append(DistributionParams(
            name="annual_savings",
            distribution="lognormal",
            params={"mu": np.log(max(base_savings, 1000)), "sigma": savings_sigma},
            description="Annual cost savings from automation",
        ))

        cost_sigma = self._uncertainty_to_sigma(confidence, complexity, 0.10, 0.50)
        dists.append(DistributionParams(
            name="implementation_cost",
            distribution="lognormal",
            params={"mu": np.log(max(base_cost, 1000)), "sigma": cost_sigma},
            description="Total implementation cost including overruns",
        ))

        ar_alpha, ar_beta = self._rate_to_beta_params(automation_rate, confidence)
        dists.append(DistributionParams(
            name="automation_rate",
            distribution="beta",
            params={"alpha": ar_alpha, "beta": ar_beta},
            description="Fraction of process that can be automated",
        ))

        return dists

    @staticmethod
    def _uncertainty_to_sigma(
        confidence: float,
        complexity: float,
        min_sigma: float,
        max_sigma: float,
    ) -> float:
        """
        Convert confidence and complexity into distribution width.
        Lower confidence + higher complexity = wider distribution.
        """
        uncertainty = (1 - confidence) * 0.6 + complexity * 0.4
        return min_sigma + (max_sigma - min_sigma) * uncertainty

    @staticmethod
    def _rate_to_beta_params(rate: float, confidence: float) -> tuple[float, float]:
        """
        Convert a rate (0-1) and confidence into Beta distribution parameters.
        Higher confidence = more concentrated distribution around the rate.
        """
        rate = max(0.01, min(0.99, rate))
        # Concentration parameter scales with confidence
        kappa = 5 + 45 * confidence  # range 5-50
        alpha = rate * kappa
        beta = (1 - rate) * kappa
        return max(alpha, 1.01), max(beta, 1.01)

    @staticmethod
    def _compute_npv(
        savings: np.ndarray,
        cost: np.ndarray,
        duration_months: np.ndarray,
        discount_rate: float,
        horizon_years: int,
        n: int,
    ) -> np.ndarray:
        """Compute Net Present Value for each simulation iteration."""
        npv = -cost.copy()  # initial investment
        for year in range(1, horizon_years + 1):
            # Ramp-up: savings start flowing after implementation
            implementation_complete = (duration_months / 12.0) <= year
            year_savings = savings * implementation_complete.astype(float)
            # Partial year if implementation finishes mid-year
            partial = np.clip(year - duration_months / 12.0, 0, 1)
            year_savings = year_savings * partial
            npv += year_savings / (1 + discount_rate) ** year
        return npv

    @staticmethod
    def _compute_irr_approx(savings: np.ndarray, cost: np.ndarray) -> np.ndarray:
        """Approximate IRR using simplified formula."""
        return np.where(cost > 0, (savings / cost) - 1, 0.0)

    @staticmethod
    def _percentiles(data: np.ndarray, levels: list[float]) -> dict[str, float]:
        percentile_values = np.percentile(data, [l * 100 for l in levels])
        return {f"p{int(l * 100)}": float(v) for l, v in zip(levels, percentile_values)}

    @staticmethod
    def _histogram(data: np.ndarray, bins: int = 50) -> dict:
        counts, bin_edges = np.histogram(data, bins=bins)
        return {
            "counts": counts.tolist(),
            "bin_edges": bin_edges.tolist(),
            "bin_centers": ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist(),
        }

    def _compute_efficient_frontier(
        self,
        results: list[SimulationResult],
        budget: float,
        scenarios: list[dict],
    ) -> list[dict]:
        """
        Compute the efficient frontier — max return for each risk level.
        Uses a simplified approach: rank by risk-adjusted return.
        """
        frontier_points = []
        n = len(results)

        # Score each process by risk-adjusted return (Sharpe-like ratio)
        scored = []
        for i, (result, scenario) in enumerate(zip(results, scenarios)):
            if result.roi_std > 0:
                sharpe = result.roi_mean / result.roi_std
            else:
                sharpe = 0
            scored.append({
                "index": i,
                "cost": result.cost_mean,
                "roi_mean": result.roi_mean,
                "roi_std": result.roi_std,
                "sharpe": sharpe,
                "savings_mean": result.savings_mean,
            })

        # Sort by Sharpe ratio (best risk-adjusted return first)
        scored.sort(key=lambda x: x["sharpe"], reverse=True)

        # Build frontier by greedily adding best projects under budget
        cumulative_cost = 0
        selected = []
        for item in scored:
            if cumulative_cost + item["cost"] <= budget:
                cumulative_cost += item["cost"]
                selected.append(item["index"])
                frontier_points.append({
                    "selected_indices": list(selected),
                    "total_cost": cumulative_cost,
                    "expected_savings": sum(
                        results[i].savings_mean for i in selected
                    ),
                    "portfolio_roi_mean": sum(
                        results[i].roi_mean * results[i].cost_mean
                        for i in selected
                    ) / max(cumulative_cost, 1),
                })

        return frontier_points
