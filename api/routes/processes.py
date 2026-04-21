"""Process CRUD + analysis endpoints."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from api.dependencies import (
    get_analyst_agent,
    get_benchmark_engine,
    get_nlp_engine,
    get_orchestrator,
    get_scoring_engine,
)
from api.middleware.auth import AuthContext, get_current_context, require_analyst
from api.middleware.audit import record_audit
from api.middleware.rate_limit import rate_limit_check
from api.schemas.common import PaginatedResponse
from api.schemas.process import (
    EventLogBatch,
    MiningRequest,
    OutcomeRecord,
    PortfolioRequest,
    PortfolioResponse,
    ProcessCreate,
    ProcessResponse,
    ProcessUpdate,
    ScoreRequest,
    ScoreResponse,
    SimulationRequest,
)
from core.agents.analyst import AnalystAgent
from core.agents.orchestrator import AgentOrchestrator
from core.engines.benchmark import BenchmarkEngine
from core.engines.nlp import NLPEngine
from core.engines.scoring import ScoringEngine
from core.engines.simulation import MonteCarloEngine, SimulationConfig
from data.database import get_db
from data.models.organization import Organization
from data.models.process import (
    DataSource,
    DocumentationQuality,
    OpportunityScore,
    Process,
    ProcessCategory,
    ProcessFrequency,
    ProcessMiningLog,
)
from data.repositories.process_repository import (
    ProcessRepository,
    ScoreRepository,
    TraceRepository,
)

router = APIRouter(prefix="/processes", tags=["processes"])


# -- CRUD --

@router.post("", response_model=ProcessResponse, status_code=201)
def create_process(
    payload: ProcessCreate,
    ctx: AuthContext = Depends(require_analyst()),
    db: Session = Depends(get_db),
):
    _enforce_rate_limit(ctx, db)

    process = Process(
        organization_id=ctx.organization_id,
        name=payload.name,
        description=payload.description,
        category=ProcessCategory(payload.category),
        subcategory=payload.subcategory,
        frequency=ProcessFrequency(payload.frequency),
        duration_minutes=payload.duration_minutes,
        annual_volume=payload.annual_volume,
        people_involved=payload.people_involved,
        hourly_cost=payload.hourly_cost,
        systems_used=json.dumps(payload.systems_used) if payload.systems_used else None,
        pain_points=json.dumps(payload.pain_points) if payload.pain_points else None,
        stakeholders=json.dumps(payload.stakeholders) if payload.stakeholders else None,
        dependencies=json.dumps(payload.dependencies) if payload.dependencies else None,
        tags=json.dumps(payload.tags) if payload.tags else None,
        num_decision_points=payload.num_decision_points,
        num_exceptions=payload.num_exceptions,
        requires_judgment=payload.requires_judgment,
        structured_data_pct=payload.structured_data_pct,
        error_rate_pct=payload.error_rate_pct,
        documentation_quality=DocumentationQuality(payload.documentation_quality),
        sop_exists=payload.sop_exists,
        source=DataSource(payload.source),
        external_id=payload.external_id,
        created_by=ctx.user.id if ctx.user else None,
    )
    db.add(process)
    db.commit()
    db.refresh(process)

    record_audit(db, ctx.organization_id, ctx.user.id if ctx.user else None,
                 "process_created", "process", process.id)
    return process


@router.get("", response_model=PaginatedResponse[ProcessResponse])
def list_processes(
    category: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    repo = ProcessRepository(db, ctx.organization_id)
    cat_enum = ProcessCategory(category) if category else None
    processes, total = repo.list_all(
        category=cat_enum,
        search=search,
        offset=(page - 1) * per_page,
        limit=per_page,
    )
    return PaginatedResponse(
        items=processes,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )


@router.get("/{process_id}", response_model=ProcessResponse)
def get_process(
    process_id: str,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    repo = ProcessRepository(db, ctx.organization_id)
    process = repo.get_by_id(process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    return process


@router.patch("/{process_id}", response_model=ProcessResponse)
def update_process(
    process_id: str,
    payload: ProcessUpdate,
    ctx: AuthContext = Depends(require_analyst()),
    db: Session = Depends(get_db),
):
    repo = ProcessRepository(db, ctx.organization_id)
    process = repo.get_by_id(process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        if field == "category":
            setattr(process, field, ProcessCategory(value))
        elif field == "frequency":
            setattr(process, field, ProcessFrequency(value))
        elif field == "documentation_quality":
            setattr(process, field, DocumentationQuality(value))
        elif field in ("systems_used", "pain_points"):
            setattr(process, field, json.dumps(value))
        else:
            setattr(process, field, value)

    process.updated_by = ctx.user.id if ctx.user else None
    process.version += 1
    db.commit()
    db.refresh(process)

    record_audit(db, ctx.organization_id, ctx.user.id if ctx.user else None,
                 "process_updated", "process", process.id)
    return process


@router.delete("/{process_id}", status_code=204)
def delete_process(
    process_id: str,
    ctx: AuthContext = Depends(require_analyst()),
    db: Session = Depends(get_db),
):
    repo = ProcessRepository(db, ctx.organization_id)
    deleted = repo.soft_delete(process_id, ctx.user.id if ctx.user else "system")
    if not deleted:
        raise HTTPException(status_code=404, detail="Process not found")
    db.commit()

    record_audit(db, ctx.organization_id, ctx.user.id if ctx.user else None,
                 "process_deleted", "process", process_id)


# -- Analysis --

@router.post("/{process_id}/analyze", response_model=ScoreResponse)
def analyze_process(
    process_id: str,
    payload: ScoreRequest,
    ctx: AuthContext = Depends(require_analyst()),
    db: Session = Depends(get_db),
    analyst: AnalystAgent = Depends(get_analyst_agent),
):
    _enforce_rate_limit(ctx, db, endpoint_multiplier=3.0)  # analysis is expensive

    process_repo = ProcessRepository(db, ctx.organization_id)
    process = process_repo.get_by_id(process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")

    process_data = _process_to_dict(process)
    result = analyst.analyze(
        process_data,
        run_simulation=payload.run_simulation,
        run_benchmark=payload.run_benchmark,
        industry=payload.industry,
        simulation_iterations=payload.simulation_iterations,
        include_llm_narrative=payload.include_narrative,
    )

    # Persist the score
    pred = result.prediction
    sim = result.simulation or {}
    score = OpportunityScore(
        organization_id=ctx.organization_id,
        process_id=process.id,
        feasibility_score=pred["feasibility_score"],
        value_score=pred["value_score"],
        risk_score=pred["risk_score"],
        complexity_score=pred["complexity_score"],
        strategic_alignment_score=0.5,
        overall_score=pred["overall_score"],
        estimated_annual_savings=pred["estimated_annual_savings"],
        implementation_cost=pred["estimated_implementation_cost"],
        roi_percentage=pred["estimated_roi"],
        payback_months=pred["estimated_payback_months"],
        confidence_level=pred["confidence"],
        roi_p10=sim.get("roi", {}).get("percentiles", {}).get("p10"),
        roi_p50=sim.get("roi", {}).get("percentiles", {}).get("p50"),
        roi_p90=sim.get("roi", {}).get("percentiles", {}).get("p90"),
        savings_p10=sim.get("savings", {}).get("percentiles", {}).get("p10"),
        savings_p90=sim.get("savings", {}).get("percentiles", {}).get("p90"),
        npv_3yr=sim.get("npv", {}).get("mean"),
        automation_feasibility=pred["automation_feasibility"],
        risk_level=pred["risk_level"],
        recommendation=pred["recommendation"],
        scoring_model_version=result.model_version,
        reasoning=result.detailed_reasoning,
        analyzed_at=datetime.now(timezone.utc),
        analyzed_by=ctx.user.id if ctx.user else None,
        industry_percentile=result.benchmark["positioning"]["roi_percentile"] if result.benchmark else None,
    )
    db.add(score)
    db.commit()

    record_audit(db, ctx.organization_id, ctx.user.id if ctx.user else None,
                 "process_analyzed", "process", process.id)

    return ScoreResponse(
        process_id=process.id,
        prediction=result.prediction,
        simulation=result.simulation,
        benchmark=result.benchmark,
        executive_summary=result.executive_summary,
        detailed_reasoning=result.detailed_reasoning,
        implementation_plan=result.implementation_plan,
        risk_analysis=result.risk_analysis,
        success_factors=result.success_factors,
        model_version=result.model_version,
    )


@router.post("/{process_id}/simulate")
def simulate_process(
    process_id: str,
    payload: SimulationRequest,
    ctx: AuthContext = Depends(require_analyst()),
    db: Session = Depends(get_db),
):
    _enforce_rate_limit(ctx, db, endpoint_multiplier=2.0)

    repo = ProcessRepository(db, ctx.organization_id)
    process = repo.get_by_id(process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")

    # Use latest score as basis for simulation
    score_repo = ScoreRepository(db, ctx.organization_id)
    latest = score_repo.get_latest_for_process(process_id)
    if not latest:
        raise HTTPException(
            status_code=400,
            detail="No score available — analyze the process first",
        )

    config = SimulationConfig(
        iterations=payload.iterations,
        discount_rate=payload.discount_rate,
        time_horizon_years=payload.time_horizon_years,
    )
    engine = MonteCarloEngine(config=config)
    result = engine.simulate(
        base_savings=latest.estimated_annual_savings,
        base_cost=latest.implementation_cost,
        base_duration_months=latest.payback_months,
        automation_rate=latest.feasibility_score,
        complexity_factor=latest.complexity_score,
        confidence_level=latest.confidence_level,
        overrides=payload.parameter_overrides,
    )
    return result.to_dict()


@router.post("/{process_id}/benchmark")
def benchmark_process(
    process_id: str,
    industry: str | None = None,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    benchmark_engine: BenchmarkEngine = Depends(get_benchmark_engine),
):
    repo = ProcessRepository(db, ctx.organization_id)
    process = repo.get_by_id(process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")

    score_repo = ScoreRepository(db, ctx.organization_id)
    latest = score_repo.get_latest_for_process(process_id)
    if not latest:
        raise HTTPException(status_code=400, detail="No score available — analyze first")

    comparison = benchmark_engine.compare(
        category=process.category,
        process_roi=latest.roi_percentage,
        process_savings=latest.estimated_annual_savings,
        process_payback_months=latest.payback_months,
        industry=industry,
    )
    if not comparison:
        raise HTTPException(status_code=404, detail="No benchmark data available for this category/industry")
    return comparison.to_dict()


@router.get("/{process_id}/scores")
def process_score_history(
    process_id: str,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    repo = ProcessRepository(db, ctx.organization_id)
    process = repo.get_by_id(process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")

    scores = (
        db.query(OpportunityScore)
        .filter(
            OpportunityScore.organization_id == ctx.organization_id,
            OpportunityScore.process_id == process_id,
        )
        .order_by(OpportunityScore.analyzed_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "overall_score": s.overall_score,
            "roi_percentage": s.roi_percentage,
            "confidence_level": s.confidence_level,
            "recommendation": s.recommendation.value,
            "analyzed_at": s.analyzed_at,
            "model_version": s.scoring_model_version,
        }
        for s in scores
    ]


# -- Bulk & portfolio --

@router.post("/portfolio/analyze", response_model=PortfolioResponse)
def analyze_portfolio(
    payload: PortfolioRequest,
    ctx: AuthContext = Depends(require_analyst()),
    db: Session = Depends(get_db),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    _enforce_rate_limit(ctx, db, endpoint_multiplier=10.0)  # very expensive

    repo = ProcessRepository(db, ctx.organization_id)
    if payload.process_ids:
        processes = [p for pid in payload.process_ids if (p := repo.get_by_id(pid))]
    else:
        processes, _ = repo.list_all(limit=500)

    if not processes:
        raise HTTPException(status_code=400, detail="No processes to analyze")

    process_dicts = [_process_to_dict(p) for p in processes]
    result = orchestrator.portfolio_analysis(
        process_dicts,
        industry=payload.industry,
        budget=payload.budget,
        risk_tolerance=payload.risk_tolerance,
    )

    record_audit(db, ctx.organization_id, ctx.user.id if ctx.user else None,
                 "portfolio_analyzed", "portfolio",
                 details={"process_count": len(processes)})

    return PortfolioResponse(**{
        "scoring": result["portfolio_scoring"],
        "quick_wins": result.get("quick_wins", []),
        "strategic_themes": result.get("strategic_themes", []),
        "recommended_portfolio": result.get("recommended_portfolio"),
        "roadmap": result.get("roadmap"),
    })


@router.post("/bulk-import", status_code=201)
def bulk_import_processes(
    processes: list[ProcessCreate],
    ctx: AuthContext = Depends(require_analyst()),
    db: Session = Depends(get_db),
):
    created_count = 0
    for payload in processes:
        try:
            process = Process(
                organization_id=ctx.organization_id,
                name=payload.name,
                description=payload.description,
                category=ProcessCategory(payload.category),
                frequency=ProcessFrequency(payload.frequency),
                duration_minutes=payload.duration_minutes,
                annual_volume=payload.annual_volume,
                people_involved=payload.people_involved,
                hourly_cost=payload.hourly_cost,
                systems_used=json.dumps(payload.systems_used) if payload.systems_used else None,
                pain_points=json.dumps(payload.pain_points) if payload.pain_points else None,
                stakeholders=json.dumps(payload.stakeholders) if payload.stakeholders else None,
                documentation_quality=DocumentationQuality(payload.documentation_quality),
                sop_exists=payload.sop_exists,
                source=DataSource(payload.source),
                created_by=ctx.user.id if ctx.user else None,
            )
            db.add(process)
            created_count += 1
        except Exception:
            continue
    db.commit()

    record_audit(db, ctx.organization_id, ctx.user.id if ctx.user else None,
                 "bulk_import", "process", details={"count": created_count})

    return {"imported": created_count, "submitted": len(processes)}


# -- Outcome recording (learning loop) --

@router.post("/{process_id}/outcomes/{trace_id}")
def record_outcome(
    process_id: str,
    trace_id: str,
    payload: OutcomeRecord,
    ctx: AuthContext = Depends(require_analyst()),
    db: Session = Depends(get_db),
):
    repo = TraceRepository(db, ctx.organization_id)
    trace = repo.record_outcome(
        trace_id,
        actual_roi=payload.actual_roi,
        actual_savings=payload.actual_annual_savings,
        actual_cost=payload.actual_implementation_cost,
        actual_payback=payload.actual_payback_months,
        lessons=payload.lessons_learned,
    )
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    db.commit()

    record_audit(db, ctx.organization_id, ctx.user.id if ctx.user else None,
                 "outcome_recorded", "decision_trace", trace_id)

    return {
        "trace_id": trace.id,
        "variance_roi": trace.variance_roi,
        "variance_savings": trace.variance_savings,
        "variance_cost": trace.variance_cost,
    }


# -- Helpers --

def _process_to_dict(process: Process) -> dict:
    """Convert ORM Process to the dict format expected by engines."""
    return {
        "id": process.id,
        "name": process.name,
        "description": process.description,
        "category": process.category.value,
        "frequency": process.frequency.value,
        "duration_minutes": process.duration_minutes,
        "annual_volume": process.annual_volume,
        "people_involved": process.people_involved,
        "hourly_cost": process.hourly_cost,
        "systems_used": process.systems_used,
        "pain_points": process.pain_points,
        "stakeholders": process.stakeholders,
        "dependencies": process.dependencies,
        "num_decision_points": process.num_decision_points,
        "num_exceptions": process.num_exceptions,
        "requires_judgment": process.requires_judgment,
        "structured_data_pct": process.structured_data_pct,
        "error_rate_pct": process.error_rate_pct,
        "documentation_quality": process.documentation_quality.value,
        "sop_exists": process.sop_exists,
    }


def _enforce_rate_limit(ctx: AuthContext, db: Session, endpoint_multiplier: float = 1.0) -> None:
    from api.middleware.rate_limit import rate_limit_check
    org = db.query(Organization).filter(Organization.id == ctx.organization_id).first()
    if org is None:
        return
    # Rate limiter needs the Request object; use a stub approach for now
    from fastapi import Request
    rate_limit_check(
        request=Request(scope={"type": "http"}),
        organization_id=ctx.organization_id,
        tier=org.subscription_tier,
        endpoint_multiplier=endpoint_multiplier,
    )
