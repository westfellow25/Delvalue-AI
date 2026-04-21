"""Tests for the ML feature engineering pipeline."""

import pytest
from core.ml.features import extract_features, FeatureVector, FEATURE_VERSION


@pytest.fixture
def process_data():
    return {
        "name": "Invoice Processing",
        "category": "finance",
        "frequency": "daily",
        "duration_minutes": 30,
        "annual_volume": 5000,
        "people_involved": 3,
        "hourly_cost": 45.0,
        "systems_used": '["SAP", "Excel"]',
        "pain_points": '["manual data entry", "errors"]',
        "num_decision_points": 3,
        "num_exceptions": 2,
        "requires_judgment": False,
        "structured_data_pct": 0.7,
        "error_rate_pct": 5.0,
        "documentation_quality": "good",
        "sop_exists": True,
        "stakeholders": '["Finance Team", "IT"]',
        "dependencies": '["SAP"]',
    }


def test_extract_features_returns_feature_vector(process_data):
    fv = extract_features(process_data)
    assert isinstance(fv, FeatureVector)
    assert fv.version == FEATURE_VERSION


def test_feature_vector_has_expected_features(process_data):
    fv = extract_features(process_data)
    expected = {
        "annual_volume", "log_volume", "duration_minutes",
        "annual_hours", "annual_labor_cost", "cost_per_execution",
        "people_involved", "frequency_score",
        "num_systems", "system_complexity", "decision_complexity",
        "exception_complexity", "requires_judgment", "structured_data_pct",
        "complexity_index",
        "doc_quality", "sop_exists",
        "stakeholder_complexity", "dependency_risk", "pain_intensity",
        "automation_readiness", "value_density", "error_impact",
        "error_rate_pct", "category_risk",
        "estimated_impl_cost", "estimated_annual_savings", "estimated_roi",
    }
    assert expected == set(fv.features.keys())


def test_feature_vector_to_array(process_data):
    fv = extract_features(process_data)
    arr = fv.to_array()
    assert len(arr) == len(fv.feature_names)
    assert arr.shape == (len(fv.feature_names),)


def test_feature_vector_round_trip(process_data):
    fv = extract_features(process_data)
    d = fv.to_dict()
    restored = FeatureVector.from_dict(d)
    assert restored.features == fv.features
    assert restored.feature_names == fv.feature_names


def test_features_are_bounded(process_data):
    fv = extract_features(process_data)
    for name in ["automation_readiness", "complexity_index", "system_complexity",
                 "decision_complexity", "frequency_score", "pain_intensity",
                 "stakeholder_complexity", "dependency_risk"]:
        assert 0.0 <= fv.features[name] <= 1.0, f"{name} out of [0,1] range"


def test_higher_volume_increases_log_volume():
    low = extract_features({"annual_volume": 100, "duration_minutes": 10, "people_involved": 1, "hourly_cost": 30})
    high = extract_features({"annual_volume": 100_000, "duration_minutes": 10, "people_involved": 1, "hourly_cost": 30})
    assert high.features["log_volume"] > low.features["log_volume"]


def test_sop_exists_is_binary():
    with_sop = extract_features({"sop_exists": True, "annual_volume": 100, "duration_minutes": 10, "people_involved": 1, "hourly_cost": 30})
    without_sop = extract_features({"sop_exists": False, "annual_volume": 100, "duration_minutes": 10, "people_involved": 1, "hourly_cost": 30})
    assert with_sop.features["sop_exists"] == 1.0
    assert without_sop.features["sop_exists"] == 0.0
