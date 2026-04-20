"""
DelValue AI — Process & Analysis Data Models

Core domain models for business process analysis, scoring, and outcome tracking.
All models are tenant-scoped and support the full analysis lifecycle.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import (
    Base,
    TimestampMixin,
    SoftDeleteMixin,
    TenantMixin,
    AuditMixin,
    VersionMixin,
    generate_uuid,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProcessCategory(str, enum.Enum):
    FINANCE = "finance"
    HR = "hr"
    OPERATIONS = "operations"
    SALES = "sales"
    MARKETING = "marketing"
    IT = "it"
    LEGAL = "legal"
    PROCUREMENT = "procurement"
    SUPPLY_CHAIN = "supply_chain"
    CUSTOMER_SERVICE = "customer_service"
    COMPLIANCE = "compliance"
    R_AND_D = "r_and_d"


class ProcessFrequency(str, enum.Enum):
    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    AD_HOC = "ad_hoc"


class DocumentationQuality(str, enum.Enum):
    NONE = "none"
    POOR = "poor"
    BASIC = "basic"
    GOOD = "good"
    EXCELLENT = "excellent"


class AutomationFeasibility(str, enum.Enum):
    NOT_FEASIBLE = "not_feasible"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    FULLY_AUTOMATABLE = "fully_automatable"


class RiskLevel(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class Recommendation(str, enum.Enum):
    AUTOMATE_NOW = "automate_now"
    STRONG_CANDIDATE = "strong_candidate"
    INVESTIGATE_FURTHER = "investigate_further"
    DEFER = "defer"
    NOT_RECOMMENDED = "not_recommended"


class ImplementationStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    PILOT = "pilot"
    SCALING = "scaling"
    COMPLETE = "complete"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class DataSource(str, enum.Enum):
    MANUAL = "manual"
    DOCUMENT_UPLOAD = "document_upload"
    PROCESS_MINING = "process_mining"
    API_IMPORT = "api_import"
    ERP_CONNECTOR = "erp_connector"
    CRM_CONNECTOR = "crm_connector"


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------

class Process(Base, TimestampMixin, SoftDeleteMixin, TenantMixin, AuditMixin, VersionMixin):
    """
    A business process that can be evaluated for automation/AI transformation.
    Central entity in the DelValue domain model.
    """

    __tablename__ = "processes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[ProcessCategory] = mapped_column(Enum(ProcessCategory), nullable=False, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Operational characteristics
    frequency: Mapped[ProcessFrequency] = mapped_column(Enum(ProcessFrequency), nullable=False)
    duration_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    annual_volume: Mapped[int] = mapped_column(Integer, nullable=False)
    people_involved: Mapped[int] = mapped_column(Integer, nullable=False)
    hourly_cost: Mapped[float] = mapped_column(Float, nullable=False)

    # Complexity indicators
    systems_used: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    num_decision_points: Mapped[int] = mapped_column(Integer, default=0)
    num_exceptions: Mapped[int] = mapped_column(Integer, default=0)
    requires_judgment: Mapped[bool] = mapped_column(Boolean, default=False)
    structured_data_pct: Mapped[float] = mapped_column(Float, default=0.5)
    error_rate_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Documentation
    documentation_quality: Mapped[DocumentationQuality] = mapped_column(
        Enum(DocumentationQuality), default=DocumentationQuality.BASIC
    )
    sop_exists: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    pain_points: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    stakeholders: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    dependencies: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    source: Mapped[DataSource] = mapped_column(
        Enum(DataSource), default=DataSource.MANUAL, nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    scores: Mapped[list[OpportunityScore]] = relationship(
        back_populates="process", lazy="selectin", order_by="OpportunityScore.analyzed_at.desc()"
    )
    traces: Mapped[list[DecisionTrace]] = relationship(
        back_populates="process", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_processes_org_category", "organization_id", "category"),
        Index("ix_processes_org_source", "organization_id", "source"),
    )


# ---------------------------------------------------------------------------
# Opportunity Score
# ---------------------------------------------------------------------------

class OpportunityScore(Base, TimestampMixin, TenantMixin):
    """
    Result of analyzing a process for automation potential.
    Immutable — each analysis creates a new score, preserving history.
    """

    __tablename__ = "opportunity_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    process_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("processes.id"), nullable=False, index=True
    )

    # Multi-factor scores (0.0 — 1.0)
    feasibility_score: Mapped[float] = mapped_column(Float, nullable=False)
    value_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    complexity_score: Mapped[float] = mapped_column(Float, nullable=False)
    strategic_alignment_score: Mapped[float] = mapped_column(Float, default=0.5)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)

    # Financial projections
    estimated_annual_savings: Mapped[float] = mapped_column(Float, nullable=False)
    implementation_cost: Mapped[float] = mapped_column(Float, nullable=False)
    roi_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    payback_months: Mapped[float] = mapped_column(Float, nullable=False)
    npv_3yr: Mapped[float | None] = mapped_column(Float, nullable=True)
    irr: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Confidence & uncertainty (from Monte Carlo)
    confidence_level: Mapped[float] = mapped_column(Float, nullable=False)
    roi_p10: Mapped[float | None] = mapped_column(Float, nullable=True)
    roi_p50: Mapped[float | None] = mapped_column(Float, nullable=True)
    roi_p90: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_p10: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_p90: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Classification
    automation_feasibility: Mapped[AutomationFeasibility] = mapped_column(
        Enum(AutomationFeasibility), nullable=False
    )
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), nullable=False)
    recommendation: Mapped[Recommendation] = mapped_column(Enum(Recommendation), nullable=False)
    risk_factors: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    # Scoring metadata
    scoring_model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    feature_vector: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON — for ML auditability
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    analyzed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Benchmark comparison
    industry_percentile: Mapped[float | None] = mapped_column(Float, nullable=True)
    category_percentile: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    process: Mapped[Process] = relationship(back_populates="scores")

    __table_args__ = (
        Index("ix_scores_org_overall", "organization_id", "overall_score"),
        Index("ix_scores_process_analyzed", "process_id", "analyzed_at"),
    )


# ---------------------------------------------------------------------------
# Decision Trace — predicted vs actual outcomes for ML learning loop
# ---------------------------------------------------------------------------

class DecisionTrace(Base, TimestampMixin, TenantMixin, AuditMixin):
    """
    Tracks the full lifecycle: prediction -> decision -> implementation -> outcome.
    This is the data that feeds the ML learning loop and calibrates confidence.
    """

    __tablename__ = "decision_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    process_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("processes.id"), nullable=False, index=True
    )
    score_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("opportunity_scores.id"), nullable=False
    )

    # Decision
    decision: Mapped[str] = mapped_column(String(50), nullable=False)  # approve/reject/defer
    decision_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision_maker: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decision_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Predictions (snapshot from score at decision time)
    predicted_roi: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_annual_savings: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_implementation_cost: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_payback_months: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Actual outcomes (filled in over time)
    actual_roi: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_annual_savings: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_implementation_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_payback_months: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Implementation tracking
    implementation_status: Mapped[ImplementationStatus] = mapped_column(
        Enum(ImplementationStatus), default=ImplementationStatus.NOT_STARTED
    )
    implementation_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    implementation_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    implementation_vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    implementation_technology: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Variance analysis (computed)
    variance_roi: Mapped[float | None] = mapped_column(Float, nullable=True)
    variance_savings: Mapped[float | None] = mapped_column(Float, nullable=True)
    variance_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    variance_timeline: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Learning metadata
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    success_factors: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    used_for_training: Mapped[bool] = mapped_column(Boolean, default=False)
    training_batch_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    process: Mapped[Process] = relationship(back_populates="traces")

    __table_args__ = (
        Index("ix_traces_org_status", "organization_id", "implementation_status"),
        Index("ix_traces_training", "used_for_training", "implementation_status"),
    )


# ---------------------------------------------------------------------------
# Simulation Run
# ---------------------------------------------------------------------------

class SimulationRun(Base, TimestampMixin, TenantMixin):
    """
    Records of Monte Carlo simulation runs for auditability.
    Each run generates a distribution of outcomes.
    """

    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    process_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("processes.id"), nullable=False, index=True
    )
    score_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("opportunity_scores.id"), nullable=True
    )

    # Configuration
    num_iterations: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(50), default="base")  # base/optimistic/pessimistic/custom

    # Input distributions (JSON — parameter distributions used)
    input_parameters: Mapped[str] = mapped_column(Text, nullable=False)

    # Output summary statistics
    roi_mean: Mapped[float] = mapped_column(Float, nullable=False)
    roi_std: Mapped[float] = mapped_column(Float, nullable=False)
    roi_p10: Mapped[float] = mapped_column(Float, nullable=False)
    roi_p50: Mapped[float] = mapped_column(Float, nullable=False)
    roi_p90: Mapped[float] = mapped_column(Float, nullable=False)
    savings_mean: Mapped[float] = mapped_column(Float, nullable=False)
    savings_std: Mapped[float] = mapped_column(Float, nullable=False)
    cost_mean: Mapped[float] = mapped_column(Float, nullable=False)
    cost_std: Mapped[float] = mapped_column(Float, nullable=False)
    payback_mean: Mapped[float] = mapped_column(Float, nullable=False)
    prob_positive_roi: Mapped[float] = mapped_column(Float, nullable=False)
    prob_payback_under_12mo: Mapped[float] = mapped_column(Float, nullable=False)
    value_at_risk_5pct: Mapped[float] = mapped_column(Float, nullable=False)

    # Full distribution (compressed JSON — for charts)
    roi_distribution: Mapped[str | None] = mapped_column(Text, nullable=True)

    run_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    triggered_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


# ---------------------------------------------------------------------------
# Benchmark Data
# ---------------------------------------------------------------------------

class BenchmarkEntry(Base, TimestampMixin):
    """
    Anonymized, aggregated benchmark data across organizations.
    Never contains individual org data — always aggregated above anonymization threshold.
    """

    __tablename__ = "benchmark_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    category: Mapped[ProcessCategory] = mapped_column(Enum(ProcessCategory), nullable=False, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(200), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    company_size_bucket: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Aggregated statistics
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_roi: Mapped[float] = mapped_column(Float, nullable=False)
    median_roi: Mapped[float] = mapped_column(Float, nullable=False)
    p25_roi: Mapped[float] = mapped_column(Float, nullable=False)
    p75_roi: Mapped[float] = mapped_column(Float, nullable=False)
    avg_savings: Mapped[float] = mapped_column(Float, nullable=False)
    avg_implementation_cost: Mapped[float] = mapped_column(Float, nullable=False)
    avg_payback_months: Mapped[float] = mapped_column(Float, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False)  # % with positive ROI
    avg_time_to_implement_months: Mapped[float] = mapped_column(Float, nullable=False)

    # Distribution shape
    roi_std: Mapped[float] = mapped_column(Float, nullable=False)
    savings_std: Mapped[float] = mapped_column(Float, nullable=False)

    # Metadata
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_aggregated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_benchmark_category_industry", "category", "industry"),
    )


# ---------------------------------------------------------------------------
# Process Mining Event Log
# ---------------------------------------------------------------------------

class ProcessMiningLog(Base, TimestampMixin, TenantMixin):
    """
    Event logs imported from enterprise systems for process mining.
    Each row is a single event in a process execution trace.
    """

    __tablename__ = "process_mining_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    case_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    activity: Mapped[str] = mapped_column(String(500), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    resource: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lifecycle: Mapped[str | None] = mapped_column(String(50), nullable=True)  # start/complete/suspend
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    attributes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    source_system: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_mining_org_case", "organization_id", "case_id"),
        Index("ix_mining_activity", "organization_id", "activity"),
    )
