"""Tests for the benchmarking engine."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.engines.benchmark import BenchmarkEngine, BenchmarkComparison
from data.models.base import Base
from data.models.process import BenchmarkEntry, ProcessCategory
from data.seeds.benchmarks import seed_benchmarks


@pytest.fixture
def db_with_benchmarks():
    eng = create_engine("sqlite://", echo=False)
    Base.metadata.create_all(eng)
    session = sessionmaker(bind=eng)()
    seed_benchmarks(session)
    yield session
    session.close()


@pytest.fixture
def benchmark_engine(db_with_benchmarks):
    return BenchmarkEngine(db_with_benchmarks)


def test_benchmarks_seeded(db_with_benchmarks):
    count = db_with_benchmarks.query(BenchmarkEntry).count()
    assert count > 100  # 12 global + 120 industry-specific


def test_compare_returns_result(benchmark_engine):
    result = benchmark_engine.compare(
        category=ProcessCategory.FINANCE,
        process_roi=150.0,
        process_savings=200_000,
        process_payback_months=8.0,
    )
    assert isinstance(result, BenchmarkComparison)


def test_percentile_ranking(benchmark_engine):
    result = benchmark_engine.compare(
        category=ProcessCategory.FINANCE,
        process_roi=150.0,
        process_savings=200_000,
        process_payback_months=8.0,
    )
    assert 0 < result.roi_percentile < 100


def test_high_roi_ranks_higher(benchmark_engine):
    low = benchmark_engine.compare(
        category=ProcessCategory.FINANCE,
        process_roi=50.0, process_savings=100_000, process_payback_months=18.0,
    )
    high = benchmark_engine.compare(
        category=ProcessCategory.FINANCE,
        process_roi=300.0, process_savings=400_000, process_payback_months=4.0,
    )
    assert high.roi_percentile > low.roi_percentile


def test_positioning_classification(benchmark_engine):
    result = benchmark_engine.compare(
        category=ProcessCategory.FINANCE,
        process_roi=300.0, process_savings=500_000, process_payback_months=3.0,
    )
    assert result.positioning in {"leader", "above_average", "average", "below_average", "laggard"}


def test_industry_specific_benchmark(benchmark_engine):
    result = benchmark_engine.compare(
        category=ProcessCategory.FINANCE,
        process_roi=150.0, process_savings=200_000, process_payback_months=8.0,
        industry="financial_services",
    )
    assert result is not None
    assert result.industry == "financial_services"


def test_improvement_targets(benchmark_engine):
    result = benchmark_engine.compare(
        category=ProcessCategory.FINANCE,
        process_roi=50.0, process_savings=50_000, process_payback_months=20.0,
    )
    assert len(result.improvement_targets) > 0


def test_to_dict(benchmark_engine):
    result = benchmark_engine.compare(
        category=ProcessCategory.FINANCE,
        process_roi=150.0, process_savings=200_000, process_payback_months=8.0,
    )
    d = result.to_dict()
    assert "positioning" in d
    assert "industry_benchmarks" in d
    assert "improvement_targets" in d
