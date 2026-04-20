"""
DelValue AI — Feature Engineering Pipeline

Transforms raw process data into ML-ready feature vectors.
Features are versioned — each version produces a deterministic, reproducible vector.

Feature categories:
  1. Operational — volume, frequency, duration, cost
  2. Complexity — systems, decision points, exceptions, judgment
  3. Documentation — quality, SOP existence
  4. Organizational — people, stakeholders, dependencies
  5. Derived — cost intensity, automation readiness index, risk proxies
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


FEATURE_VERSION = "v2"

# Frequency to annual multiplier mapping
FREQUENCY_MULTIPLIERS = {
    "real_time": 365 * 24,
    "hourly": 365 * 8,  # 8 working hours
    "daily": 250,  # working days
    "weekly": 52,
    "monthly": 12,
    "quarterly": 4,
    "annually": 1,
    "ad_hoc": 50,  # estimate
}

# Category risk priors (from industry data)
CATEGORY_RISK_PRIORS = {
    "finance": 0.35,
    "hr": 0.25,
    "operations": 0.30,
    "sales": 0.20,
    "marketing": 0.15,
    "it": 0.30,
    "legal": 0.45,
    "procurement": 0.25,
    "supply_chain": 0.35,
    "customer_service": 0.20,
    "compliance": 0.50,
    "r_and_d": 0.40,
}


@dataclass
class FeatureVector:
    """Typed, named feature vector with metadata."""

    features: dict[str, float]
    feature_names: list[str]
    version: str = FEATURE_VERSION

    def to_array(self) -> np.ndarray:
        return np.array([self.features[name] for name in self.feature_names])

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "features": self.features,
            "feature_names": self.feature_names,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FeatureVector:
        return cls(
            features=data["features"],
            feature_names=data["feature_names"],
            version=data.get("version", FEATURE_VERSION),
        )


def _safe_json_list(value: Optional[str]) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _doc_quality_score(quality: str) -> float:
    mapping = {"none": 0.0, "poor": 0.2, "basic": 0.5, "good": 0.8, "excellent": 1.0}
    return mapping.get(quality, 0.3)


def extract_features(process_data: dict) -> FeatureVector:
    """
    Extract a complete feature vector from process data.

    Args:
        process_data: dict with process attributes (from ORM or API)

    Returns:
        FeatureVector with named features ready for ML model
    """

    # --- Raw extractions ---
    annual_volume = max(process_data.get("annual_volume", 0), 1)
    duration_min = max(process_data.get("duration_minutes", 0), 0.1)
    people = max(process_data.get("people_involved", 1), 1)
    hourly_cost = max(process_data.get("hourly_cost", 0), 1.0)
    frequency = process_data.get("frequency", "monthly")
    category = process_data.get("category", "operations")
    systems = _safe_json_list(process_data.get("systems_used"))
    pain_points = _safe_json_list(process_data.get("pain_points"))
    dependencies = _safe_json_list(process_data.get("dependencies"))
    stakeholders = _safe_json_list(process_data.get("stakeholders"))
    num_systems = len(systems)
    num_decision_points = process_data.get("num_decision_points", 0)
    num_exceptions = process_data.get("num_exceptions", 0)
    requires_judgment = 1.0 if process_data.get("requires_judgment", False) else 0.0
    structured_pct = process_data.get("structured_data_pct", 0.5)
    error_rate = process_data.get("error_rate_pct", 0.0)
    doc_quality = _doc_quality_score(process_data.get("documentation_quality", "basic"))
    sop_exists = 1.0 if process_data.get("sop_exists", False) else 0.0

    # --- Derived features ---
    # Annual labor cost
    annual_hours = (annual_volume * duration_min) / 60.0
    annual_labor_cost = annual_hours * hourly_cost

    # Cost per execution
    cost_per_execution = (duration_min / 60.0) * hourly_cost * people

    # Volume intensity (log-scaled)
    log_volume = math.log1p(annual_volume)

    # Complexity index (0-1 scale)
    system_complexity = min(num_systems / 8.0, 1.0)
    decision_complexity = min(num_decision_points / 10.0, 1.0)
    exception_complexity = min(num_exceptions / 15.0, 1.0)
    complexity_index = (
        0.25 * system_complexity
        + 0.25 * decision_complexity
        + 0.20 * exception_complexity
        + 0.20 * requires_judgment
        + 0.10 * (1.0 - structured_pct)
    )

    # Automation readiness (higher = easier to automate)
    automation_readiness = (
        0.30 * structured_pct
        + 0.20 * doc_quality
        + 0.15 * sop_exists
        + 0.15 * (1.0 - requires_judgment)
        + 0.10 * (1.0 - decision_complexity)
        + 0.10 * min(log_volume / 12.0, 1.0)  # high-volume processes are better candidates
    )

    # Value density (savings potential per unit effort)
    value_density = annual_labor_cost / max(people, 1)

    # Error impact (cost of errors)
    error_impact = error_rate * annual_labor_cost / 100.0

    # Stakeholder complexity
    stakeholder_complexity = min(len(stakeholders) / 6.0, 1.0)

    # Dependency risk
    dependency_risk = min(len(dependencies) / 5.0, 1.0)

    # Frequency score (how often it runs — higher frequency = more value from automation)
    freq_multiplier = FREQUENCY_MULTIPLIERS.get(frequency, 50)
    frequency_score = min(math.log1p(freq_multiplier) / math.log1p(365 * 24), 1.0)

    # Category risk prior
    category_risk = CATEGORY_RISK_PRIORS.get(category, 0.30)

    # Pain point intensity
    pain_intensity = min(len(pain_points) / 5.0, 1.0)

    # Implementation cost estimate (refined)
    base_cost = 15_000
    system_cost = num_systems * 5_000
    complexity_premium = complexity_index * 50_000
    scale_premium = max(0, (people - 5)) * 3_000
    estimated_impl_cost = base_cost + system_cost + complexity_premium + scale_premium

    # Estimated annual savings (% of labor cost that can be saved)
    savings_rate = automation_readiness * (1 - 0.3 * complexity_index)
    estimated_annual_savings = annual_labor_cost * savings_rate

    # ROI estimate
    if estimated_impl_cost > 0:
        estimated_roi = (estimated_annual_savings - estimated_impl_cost) / estimated_impl_cost
    else:
        estimated_roi = 0.0

    # Payback months
    if estimated_annual_savings > 0:
        payback_months = (estimated_impl_cost / estimated_annual_savings) * 12
    else:
        payback_months = 999.0

    # --- Assemble feature vector ---
    features = {
        # Operational (8)
        "annual_volume": annual_volume,
        "log_volume": log_volume,
        "duration_minutes": duration_min,
        "annual_hours": annual_hours,
        "annual_labor_cost": annual_labor_cost,
        "cost_per_execution": cost_per_execution,
        "people_involved": float(people),
        "frequency_score": frequency_score,
        # Complexity (7)
        "num_systems": float(num_systems),
        "system_complexity": system_complexity,
        "decision_complexity": decision_complexity,
        "exception_complexity": exception_complexity,
        "requires_judgment": requires_judgment,
        "structured_data_pct": structured_pct,
        "complexity_index": complexity_index,
        # Documentation (2)
        "doc_quality": doc_quality,
        "sop_exists": sop_exists,
        # Organizational (3)
        "stakeholder_complexity": stakeholder_complexity,
        "dependency_risk": dependency_risk,
        "pain_intensity": pain_intensity,
        # Derived (8)
        "automation_readiness": automation_readiness,
        "value_density": value_density,
        "error_impact": error_impact,
        "error_rate_pct": error_rate,
        "category_risk": category_risk,
        "estimated_impl_cost": estimated_impl_cost,
        "estimated_annual_savings": estimated_annual_savings,
        "estimated_roi": estimated_roi,
    }

    feature_names = sorted(features.keys())

    return FeatureVector(
        features=features,
        feature_names=feature_names,
    )


def extract_features_batch(processes: list[dict]) -> list[FeatureVector]:
    """Extract features for multiple processes."""
    return [extract_features(p) for p in processes]
