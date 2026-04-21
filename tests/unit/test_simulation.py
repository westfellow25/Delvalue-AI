"""Tests for the Monte Carlo simulation engine."""

import time
import pytest
from core.engines.simulation import MonteCarloEngine, SimulationConfig, SimulationResult


@pytest.fixture
def engine():
    config = SimulationConfig(iterations=5000, seed=42)
    return MonteCarloEngine(config=config)


def test_simulation_returns_result(engine):
    result = engine.simulate(
        base_savings=200_000, base_cost=80_000,
        base_duration_months=6, automation_rate=0.6,
    )
    assert isinstance(result, SimulationResult)


def test_result_has_all_fields(engine):
    r = engine.simulate(base_savings=200_000, base_cost=80_000, base_duration_months=6)
    assert r.roi_mean != 0
    assert r.savings_mean > 0
    assert r.cost_mean > 0
    assert r.num_iterations == 5000
    assert r.seed == 42


def test_probabilities_are_bounded(engine):
    r = engine.simulate(base_savings=200_000, base_cost=80_000, base_duration_months=6)
    for prob in [r.prob_positive_roi, r.prob_roi_above_50, r.prob_roi_above_100,
                 r.prob_roi_above_200, r.prob_payback_under_6mo,
                 r.prob_payback_under_12mo, r.prob_payback_under_24mo]:
        assert 0.0 <= prob <= 1.0


def test_percentile_ordering(engine):
    r = engine.simulate(base_savings=200_000, base_cost=80_000, base_duration_months=6)
    pcts = r.roi_percentiles
    keys = sorted(pcts.keys(), key=lambda k: int(k[1:]))
    values = [pcts[k] for k in keys]
    for i in range(len(values) - 1):
        assert values[i] <= values[i + 1] + 0.01  # small tolerance for sampling noise


def test_deterministic_with_seed():
    config = SimulationConfig(iterations=1000, seed=123)
    e1 = MonteCarloEngine(config)
    e2 = MonteCarloEngine(config)
    r1 = e1.simulate(base_savings=100_000, base_cost=50_000, base_duration_months=6)
    r2 = e2.simulate(base_savings=100_000, base_cost=50_000, base_duration_months=6)
    assert abs(r1.roi_mean - r2.roi_mean) < 0.01


def test_performance_10k_under_2_seconds():
    config = SimulationConfig(iterations=10_000, seed=42)
    e = MonteCarloEngine(config)
    start = time.perf_counter()
    e.simulate(base_savings=200_000, base_cost=80_000, base_duration_months=6)
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0


def test_high_confidence_narrow_distribution():
    config = SimulationConfig(iterations=5000, seed=42)
    e = MonteCarloEngine(config)
    r = e.simulate(
        base_savings=200_000, base_cost=80_000, base_duration_months=6,
        confidence_level=0.95, complexity_factor=0.1,
    )
    # High confidence + low complexity = narrow distribution
    assert r.roi_std < 500  # relative to the mean, should be reasonable


def test_low_confidence_wide_distribution():
    config = SimulationConfig(iterations=5000, seed=42)
    e = MonteCarloEngine(config)
    r_low = e.simulate(
        base_savings=200_000, base_cost=80_000, base_duration_months=6,
        confidence_level=0.3, complexity_factor=0.8,
    )
    r_high = e.simulate(
        base_savings=200_000, base_cost=80_000, base_duration_months=6,
        confidence_level=0.95, complexity_factor=0.1,
    )
    # Low confidence should give wider std
    assert r_low.roi_std > r_high.roi_std


def test_to_dict(engine):
    r = engine.simulate(base_savings=200_000, base_cost=80_000, base_duration_months=6)
    d = r.to_dict()
    assert "roi" in d
    assert "probabilities" in d
    assert "risk" in d
    assert "npv" in d
    assert "metadata" in d


def test_histogram_has_bins(engine):
    r = engine.simulate(base_savings=200_000, base_cost=80_000, base_duration_months=6)
    assert len(r.roi_histogram["counts"]) > 0
    assert len(r.roi_histogram["bin_edges"]) == len(r.roi_histogram["counts"]) + 1
