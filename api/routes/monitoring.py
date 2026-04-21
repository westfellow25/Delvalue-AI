"""Monitoring & learning loop routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_monitor_agent, get_scoring_engine
from api.middleware.auth import AuthContext, get_current_context
from core.agents.monitor import MonitorAgent
from core.engines.scoring import ScoringEngine
from data.database import get_db
from data.repositories.process_repository import TraceRepository

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/accuracy")
def model_accuracy(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    monitor: MonitorAgent = Depends(get_monitor_agent),
):
    repo = TraceRepository(db, ctx.organization_id)
    traces_orm = repo.get_completed_traces()
    traces = [_trace_to_dict(t) for t in traces_orm]

    metrics = monitor.compute_accuracy(traces)
    return {
        "metrics": metrics.to_dict() if metrics else None,
        "message": (
            f"Accuracy computed from {len(traces)} completed implementations"
            if metrics
            else "Insufficient data — need at least 5 completed implementations"
        ),
    }


@router.get("/insights")
def learning_insights(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    monitor: MonitorAgent = Depends(get_monitor_agent),
):
    repo = TraceRepository(db, ctx.organization_id)
    traces = [_trace_to_dict(t) for t in repo.get_completed_traces()]
    return {"insights": monitor.generate_learning_insights(traces)}


@router.get("/alerts")
def variance_alerts(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    monitor: MonitorAgent = Depends(get_monitor_agent),
):
    repo = TraceRepository(db, ctx.organization_id)
    traces = [_trace_to_dict(t) for t in repo.get_completed_traces()]
    alerts = monitor.check_variance_alerts(traces)
    return {
        "alerts": [
            {
                "process_name": a.process_name,
                "trace_id": a.trace_id,
                "metric": a.metric,
                "predicted": a.predicted,
                "actual": a.actual,
                "variance_pct": a.variance_pct,
                "severity": a.severity,
                "recommendation": a.recommendation,
            }
            for a in alerts
        ],
        "count": len(alerts),
    }


@router.get("/model-health")
def model_health(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    monitor: MonitorAgent = Depends(get_monitor_agent),
    scoring_engine: ScoringEngine = Depends(get_scoring_engine),
):
    repo = TraceRepository(db, ctx.organization_id)
    traces = [_trace_to_dict(t) for t in repo.get_completed_traces()]
    metrics = monitor.compute_accuracy(traces)
    insights = monitor.generate_learning_insights(traces)

    return {
        "model_version": scoring_engine.active_model_version,
        "accuracy": metrics.to_dict() if metrics else None,
        "insights": insights,
        "total_traces": len(traces),
    }


def _trace_to_dict(trace) -> dict:
    return {
        "id": trace.id,
        "process_name": trace.process.name if trace.process else "Unknown",
        "category": trace.process.category.value if trace.process else "unknown",
        "predicted_roi": trace.predicted_roi,
        "actual_roi": trace.actual_roi,
        "predicted_annual_savings": trace.predicted_annual_savings,
        "actual_annual_savings": trace.actual_annual_savings,
        "predicted_implementation_cost": trace.predicted_implementation_cost,
        "actual_implementation_cost": trace.actual_implementation_cost,
        "predicted_confidence": trace.predicted_confidence,
    }
