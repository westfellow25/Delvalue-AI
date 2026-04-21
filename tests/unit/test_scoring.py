"""Tests for the scoring engine and heuristic model."""

import pytest
from core.ml.features import extract_features
from core.ml.models import HeuristicScoringModel, PredictionResult
from core.engines.scoring import ScoringEngine


@pytest.fixture
def model():
    return HeuristicScoringModel()


@pytest.fixture
def scoring_engine():
    return ScoringEngine()


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
        "pain_points": '["manual data entry"]',
        "num_decision_points": 3,
        "num_exceptions": 2,
        "requires_judgment": False,
        "structured_data_pct": 0.7,
        "documentation_quality": "good",
        "sop_exists": True,
    }


def test_heuristic_model_returns_prediction(model, process_data):
    fv = extract_features(process_data)
    result = model.predict(fv)
    assert isinstance(result, PredictionResult)


def test_scores_in_valid_range(model, process_data):
    fv = extract_features(process_data)
    r = model.predict(fv)
    assert 0.0 <= r.overall_score <= 1.0
    assert 0.0 <= r.feasibility_score <= 1.0
    assert 0.0 <= r.value_score <= 1.0
    assert 0.0 <= r.risk_score <= 1.0
    assert 0.0 <= r.complexity_score <= 1.0
    assert 0.0 <= r.confidence <= 1.0


def test_recommendation_is_valid(model, process_data):
    fv = extract_features(process_data)
    r = model.predict(fv)
    valid = {"automate_now", "strong_candidate", "investigate_further", "defer", "not_recommended"}
    assert r.recommendation in valid


def test_risk_level_is_valid(model, process_data):
    fv = extract_features(process_data)
    r = model.predict(fv)
    valid = {"critical", "high", "medium", "low", "negligible"}
    assert r.risk_level in valid


def test_financial_estimates_are_positive(model, process_data):
    fv = extract_features(process_data)
    r = model.predict(fv)
    assert r.estimated_annual_savings >= 0
    assert r.estimated_implementation_cost >= 0
    assert r.estimated_payback_months >= 0


def test_high_volume_simple_process_scores_well(model):
    fv = extract_features({
        "category": "finance", "frequency": "hourly",
        "duration_minutes": 5, "annual_volume": 100_000,
        "people_involved": 2, "hourly_cost": 50,
        "structured_data_pct": 0.95, "sop_exists": True,
        "documentation_quality": "excellent",
        "num_decision_points": 0, "num_exceptions": 0,
        "requires_judgment": False,
    })
    r = model.predict(fv)
    assert r.overall_score > 0.6
    assert r.recommendation in ("automate_now", "strong_candidate")


def test_complex_judgment_process_scores_lower(model):
    fv = extract_features({
        "category": "legal", "frequency": "monthly",
        "duration_minutes": 120, "annual_volume": 50,
        "people_involved": 5, "hourly_cost": 150,
        "systems_used": '["System1","System2","System3","System4","System5"]',
        "structured_data_pct": 0.2, "sop_exists": False,
        "documentation_quality": "poor",
        "num_decision_points": 8, "num_exceptions": 10,
        "requires_judgment": True,
    })
    r = model.predict(fv)
    assert r.complexity_score > 0.5
    assert r.risk_score > 0.3


def test_scoring_engine_full_pipeline(scoring_engine, process_data):
    result = scoring_engine.score_process(process_data, run_simulation=True)
    assert "prediction" in result
    assert "simulation" in result
    assert "model" in result
    assert result["prediction"]["overall_score"] > 0


def test_scoring_engine_without_simulation(scoring_engine, process_data):
    result = scoring_engine.score_process(process_data, run_simulation=False)
    assert "prediction" in result
    assert result.get("simulation") is None


def test_portfolio_scoring(scoring_engine, process_data):
    processes = [process_data, {**process_data, "name": "Process 2", "annual_volume": 100}]
    result = scoring_engine.score_portfolio(processes, run_simulation=False)
    assert result["summary"]["total_processes"] == 2
    assert len(result["results"]) == 2
