"""Process and scoring schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProcessCreate(BaseModel):
    name: str = Field(..., max_length=500)
    description: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    frequency: str
    duration_minutes: float = Field(..., gt=0)
    annual_volume: int = Field(..., ge=0)
    people_involved: int = Field(..., ge=1)
    hourly_cost: float = Field(..., gt=0)

    systems_used: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    stakeholders: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    num_decision_points: int = 0
    num_exceptions: int = 0
    requires_judgment: bool = False
    structured_data_pct: float = Field(0.5, ge=0, le=1)
    error_rate_pct: float = Field(0.0, ge=0, le=100)

    documentation_quality: str = "basic"
    sop_exists: bool = False
    source: str = "manual"
    external_id: Optional[str] = None


class ProcessUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    frequency: Optional[str] = None
    duration_minutes: Optional[float] = None
    annual_volume: Optional[int] = None
    people_involved: Optional[int] = None
    hourly_cost: Optional[float] = None
    systems_used: Optional[list[str]] = None
    pain_points: Optional[list[str]] = None
    documentation_quality: Optional[str] = None
    sop_exists: Optional[bool] = None


class ProcessResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    category: str
    subcategory: Optional[str]
    frequency: str
    duration_minutes: float
    annual_volume: int
    people_involved: int
    hourly_cost: float
    documentation_quality: str
    sop_exists: bool
    source: str
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = {"from_attributes": True}


class ScoreRequest(BaseModel):
    run_simulation: bool = True
    run_benchmark: bool = True
    industry: Optional[str] = None
    simulation_iterations: int = Field(10_000, ge=1000, le=100_000)
    include_narrative: bool = True


class ScoringPrediction(BaseModel):
    overall_score: float
    feasibility_score: float
    value_score: float
    risk_score: float
    complexity_score: float
    estimated_annual_savings: float
    estimated_implementation_cost: float
    estimated_roi: float
    estimated_payback_months: float
    confidence: float
    recommendation: str
    automation_feasibility: str
    risk_level: str


class ScoreResponse(BaseModel):
    process_id: str
    prediction: dict
    simulation: Optional[dict] = None
    benchmark: Optional[dict] = None
    executive_summary: Optional[str] = None
    detailed_reasoning: Optional[str] = None
    implementation_plan: Optional[list[str]] = None
    risk_analysis: Optional[list[str]] = None
    success_factors: Optional[list[str]] = None
    model_version: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class PortfolioRequest(BaseModel):
    process_ids: Optional[list[str]] = None
    budget: Optional[float] = None
    industry: Optional[str] = None
    risk_tolerance: str = "balanced"
    min_confidence: float = 0.5


class PortfolioResponse(BaseModel):
    scoring: dict
    quick_wins: list[dict] = Field(default_factory=list)
    strategic_themes: list[dict] = Field(default_factory=list)
    recommended_portfolio: Optional[dict] = None
    roadmap: Optional[dict] = None


class SimulationRequest(BaseModel):
    iterations: int = Field(10_000, ge=1000, le=100_000)
    discount_rate: float = Field(0.10, ge=0, le=1)
    time_horizon_years: int = Field(3, ge=1, le=10)
    parameter_overrides: Optional[dict] = None


class EventLogEntry(BaseModel):
    case_id: str
    activity: str
    timestamp: datetime
    resource: Optional[str] = None
    lifecycle: Optional[str] = None
    cost: Optional[float] = None


class EventLogBatch(BaseModel):
    events: list[EventLogEntry]
    source_system: Optional[str] = None


class MiningRequest(BaseModel):
    hourly_cost: float = 75.0


class OutcomeRecord(BaseModel):
    actual_roi: float
    actual_annual_savings: float
    actual_implementation_cost: float
    actual_payback_months: float
    implementation_status: str = "complete"
    lessons_learned: Optional[str] = None
