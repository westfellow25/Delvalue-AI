"""
Data models for DelValue AI
Defines core data structures for processes, opportunities, and decision traces
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class ProcessCategory(str, Enum):
    """Process category classifications"""
    FINANCE = "finance"
    OPERATIONS = "operations"
    SALES = "sales"
    CUSTOMER_SERVICE = "customer_service"
    HR = "hr"
    IT = "it"
    MARKETING = "marketing"
    LEGAL = "legal"
    OTHER = "other"


class AutomationFeasibility(str, Enum):
    """Automation feasibility assessment levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskLevel(str, Enum):
    """Risk level classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Process(BaseModel):
    """
    Core process data model
    Represents a business process that could be automated
    """
    
    # Identifiers
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique process ID")
    name: str = Field(..., min_length=1, max_length=200, description="Process name")
    description: str = Field(..., min_length=10, description="Detailed process description")
    category: ProcessCategory = Field(..., description="Process category")
    
    # Operational Metrics
    frequency: str = Field(..., description="How often process runs (e.g., 'daily', '100x/day', 'weekly')")
    duration_minutes: float = Field(..., gt=0, description="Average time per execution in minutes")
    annual_volume: int = Field(..., gt=0, description="Number of executions per year")
    people_involved: int = Field(..., gt=0, description="Number of people involved")
    
    # Financial
    hourly_cost: float = Field(default=50.0, gt=0, description="Blended hourly cost in USD")
    
    # Context
    systems_used: List[str] = Field(default_factory=list, description="Systems/tools used in process")
    pain_points: List[str] = Field(default_factory=list, description="Current pain points")
    stakeholders: List[str] = Field(default_factory=list, description="Key stakeholders")
    dependencies: List[str] = Field(default_factory=list, description="Process dependencies")
    
    # Documentation
    documentation_quality: Optional[str] = Field(default=None, description="Quality of existing documentation")
    sop_exists: bool = Field(default=False, description="Does SOP exist?")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    source: Optional[str] = Field(default=None, description="Data source (upload, API, manual)")
    
    class Config:
        use_enum_values = True


class OpportunityScore(BaseModel):
    """
    Automation opportunity scoring and analysis
    Output from Decision Engine
    """
    
    # Reference
    opportunity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    process_id: str
    process_name: str
    
    # Component Scores (0-100)
    feasibility_score: float = Field(..., ge=0, le=100, description="How feasible to automate")
    value_score: float = Field(..., ge=0, le=100, description="Potential business value")
    risk_score: float = Field(..., ge=0, le=100, description="Implementation risk (lower is better)")
    overall_score: float = Field(..., ge=0, le=100, description="Weighted overall score")
    
    # Financial Analysis
    estimated_annual_savings: float = Field(..., ge=0, description="Projected annual cost savings")
    implementation_cost: float = Field(..., ge=0, description="Estimated implementation cost")
    roi_percentage: float = Field(..., description="Return on investment %")
    payback_months: float = Field(..., ge=0, description="Months to break even")
    
    # Risk Assessment
    risk_level: RiskLevel
    risk_factors: List[str] = Field(default_factory=list, description="Identified risk factors")
    
    # Recommendation
    automation_feasibility: AutomationFeasibility
    recommendation: str = Field(..., description="Clear recommendation (STRONG RECOMMEND, CONSIDER, DEPRIORITIZE)")
    reasoning: str = Field(..., description="Detailed reasoning for recommendation")
    
    # Confidence
    confidence_level: float = Field(..., ge=0, le=1, description="Model confidence (0-1)")
    
    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


class DecisionTrace(BaseModel):
    """
    Track decision outcomes for learning loop
    Enables predicted vs actual comparison
    """
    
    # Identifiers
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    process_id: str
    opportunity_id: str
    
    # Decision
    decision: str = Field(..., description="GO, NO-GO, DEFER")
    decision_date: datetime = Field(default_factory=datetime.now)
    decision_maker: Optional[str] = None
    
    # Predictions (at time of decision)
    predicted_roi: float
    predicted_annual_savings: float
    predicted_implementation_cost: float
    predicted_payback_months: float
    
    # Actuals (filled in over time)
    actual_roi: Optional[float] = None
    actual_annual_savings: Optional[float] = None
    actual_implementation_cost: Optional[float] = None
    actual_payback_months: Optional[float] = None
    
    # Implementation tracking
    implementation_start_date: Optional[datetime] = None
    implementation_end_date: Optional[datetime] = None
    implementation_status: Optional[str] = None  # "planning", "in_progress", "completed", "failed"
    
    # Learning
    variance_roi: Optional[float] = None
    variance_savings: Optional[float] = None
    variance_cost: Optional[float] = None
    lessons_learned: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    def calculate_variance(self):
        """Calculate variance between predicted and actual"""
        if self.actual_roi is not None:
            self.variance_roi = ((self.actual_roi - self.predicted_roi) / self.predicted_roi) * 100
        
        if self.actual_annual_savings is not None:
            self.variance_savings = ((self.actual_annual_savings - self.predicted_annual_savings) / self.predicted_annual_savings) * 100
        
        if self.actual_implementation_cost is not None:
            self.variance_cost = ((self.actual_implementation_cost - self.predicted_implementation_cost) / self.predicted_implementation_cost) * 100


# Example usage and validation
if __name__ == "__main__":
    # Test creating a Process
    test_process = Process(
        name="Invoice Processing",
        description="Manual review and approval of vendor invoices in accounts payable",
        category=ProcessCategory.FINANCE,
        frequency="200x/day",
        duration_minutes=15,
        annual_volume=50000,
        people_involved=5,
        hourly_cost=45,
        systems_used=["SAP", "Email", "Excel"],
        pain_points=["Manual data entry", "Frequent errors", "Slow approval"],
        stakeholders=["CFO", "AP Manager", "Finance Team"]
    )
    
    print("✅ Process model created successfully!")
    print(f"Process ID: {test_process.id}")
    print(f"Process: {test_process.name}")
    print(test_process.model_dump_json(indent=2))