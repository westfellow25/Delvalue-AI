"""
Tests for Decision Engine
"""

import pytest
from src.core.decision_engine import DecisionEngine
from src.models.process import Process, ProcessCategory

class TestDecisionEngine:
    """Test Decision Engine"""
    
    @pytest.fixture
    def engine(self):
        """Create engine instance"""
        return DecisionEngine()
    
    @pytest.fixture
    def sample_process(self):
        """Create sample process"""
        return Process(
            name="Invoice Processing",
            description="Manual invoice processing with multiple steps and approvals",
            category=ProcessCategory.FINANCE,
            frequency="daily",
            duration_minutes=15,
            annual_volume=10000,
            people_involved=5,
            hourly_cost=50.0,
            systems_used=["SAP", "Email"],
            pain_points=["Manual entry", "Errors"],
            stakeholders=["CFO", "Finance Team"],
            sop_exists=True
        )
    
    def test_calculate_feasibility_score(self, engine, sample_process):
        """Test feasibility calculation"""
        score, factors = engine.calculate_feasibility_score(sample_process)
        
        assert 0 <= score <= 100
        assert isinstance(factors, list)
        assert len(factors) > 0
    
    def test_calculate_value_score(self, engine, sample_process):
        """Test value calculation"""
        score, factors = engine.calculate_value_score(sample_process)
        
        assert 0 <= score <= 100
        assert isinstance(factors, list)
    
    def test_calculate_risk_score(self, engine, sample_process):
        """Test risk calculation"""
        score, risk_factors = engine.calculate_risk_score(sample_process)
        
        assert 0 <= score <= 100
        assert isinstance(risk_factors, list)
    
    def test_calculate_roi(self, engine, sample_process):
        """Test ROI calculation"""
        roi = engine.calculate_roi(sample_process)
        
        assert 'annual_savings' in roi
        assert 'implementation_cost' in roi
        assert 'roi_percentage' in roi
        assert roi['annual_savings'] > 0
    
    def test_score_opportunity(self, engine, sample_process):
        """Test full opportunity scoring"""
        score = engine.score_opportunity(sample_process)
        
        assert score.process_id == sample_process.id
        assert 0 <= score.overall_score <= 100
        assert score.recommendation in ["STRONG RECOMMEND", "RECOMMEND", "CONSIDER", "DEPRIORITIZE"]
    
    def test_rank_opportunities(self, engine):
        """Test ranking multiple processes"""
        processes = [
            Process(
                name=f"Process {i}",
                description="Test process for ranking",
                category=ProcessCategory.OPERATIONS,
                frequency="daily",
                duration_minutes=30,
                annual_volume=1000 * i,
                people_involved=5,
                hourly_cost=50.0
            )
            for i in range(1, 4)
        ]
        
        scores = engine.rank_opportunities(processes)
        
        assert len(scores) == 3
        # Verify sorted by overall_score
        for i in range(len(scores) - 1):
            assert scores[i].overall_score >= scores[i + 1].overall_score
