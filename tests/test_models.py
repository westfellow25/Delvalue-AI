"""
Tests for data models
"""

import pytest
from datetime import datetime
from src.models.process import Process, OpportunityScore, DecisionTrace, ProcessCategory

class TestProcess:
    """Test Process model"""
    
    def test_create_process(self):
        """Test creating a valid process"""
        process = Process(
            name="Test Process",
            description="This is a test process for validation",
            category=ProcessCategory.FINANCE,
            frequency="daily",
            duration_minutes=30,
            annual_volume=1000,
            people_involved=5,
            hourly_cost=50.0,
            systems_used=["System A"],
            pain_points=["Pain 1"],
            stakeholders=["Person 1"]
        )
        
        assert process.name == "Test Process"
        assert process.category == "finance"
        assert process.annual_volume == 1000
        assert len(process.id) > 0  # UUID generated
    
    def test_process_validation(self):
        """Test process validation"""
        with pytest.raises(Exception):
            # Missing required fields
            Process(
                name="",
                description="Too short",
                category=ProcessCategory.FINANCE,
                frequency="daily",
                duration_minutes=30,
                annual_volume=1000,
                people_involved=5
            )
    
    def test_process_timestamps(self):
        """Test automatic timestamps"""
        process = Process(
            name="Test",
            description="Test process with timestamps",
            category=ProcessCategory.IT,
            frequency="weekly",
            duration_minutes=60,
            annual_volume=52,
            people_involved=3,
            hourly_cost=45.0
        )
        
        assert isinstance(process.created_at, datetime)
        assert process.updated_at is None

class TestOpportunityScore:
    """Test OpportunityScore model"""
    
    def test_create_score(self):
        """Test creating a score"""
        score = OpportunityScore(
            process_id="test-123",
            process_name="Test Process",
            feasibility_score=75.0,
            value_score=80.0,
            risk_score=30.0,
            overall_score=70.0,
            estimated_annual_savings=100000.0,
            implementation_cost=20000.0,
            roi_percentage=400.0,
            payback_months=2.4,
            risk_level="medium",
            risk_factors=["Risk 1"],
            automation_feasibility="high",
            recommendation="RECOMMEND",
            reasoning="Good opportunity",
            confidence_level=0.8
        )
        
        assert score.overall_score == 70.0
        assert score.roi_percentage == 400.0

class TestDecisionTrace:
    """Test DecisionTrace model"""
    
    def test_create_trace(self):
        """Test creating a decision trace"""
        trace = DecisionTrace(
            process_id="proc-1",
            opportunity_id="opp-1",
            decision="GO",
            predicted_roi=150.0,
            predicted_annual_savings=200000.0,
            predicted_implementation_cost=30000.0,
            predicted_payback_months=1.8
        )
        
        assert trace.decision == "GO"
        assert trace.actual_roi is None
    
    def test_calculate_variance(self):
        """Test variance calculation"""
        trace = DecisionTrace(
            process_id="proc-1",
            opportunity_id="opp-1",
            decision="GO",
            predicted_roi=150.0,
            predicted_annual_savings=200000.0,
            predicted_implementation_cost=30000.0,
            predicted_payback_months=1.8,
            actual_roi=135.0,
            actual_annual_savings=180000.0,
            actual_implementation_cost=33000.0
        )
        
        trace.calculate_variance()
        
        assert trace.variance_roi == -10.0
        assert trace.variance_savings == -10.0
        assert trace.variance_cost == 10.0
