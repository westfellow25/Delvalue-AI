"""Benchmark routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_benchmark_engine
from api.middleware.auth import AuthContext, get_current_context
from core.engines.benchmark import BenchmarkEngine
from data.database import get_db
from data.models.process import BenchmarkEntry, ProcessCategory

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("")
def list_benchmarks(
    category: str | None = None,
    industry: str | None = None,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    q = db.query(BenchmarkEntry)
    if category:
        q = q.filter(BenchmarkEntry.category == ProcessCategory(category))
    if industry:
        q = q.filter(BenchmarkEntry.industry == industry)
    entries = q.order_by(BenchmarkEntry.category).all()
    return [
        {
            "id": e.id,
            "category": e.category.value,
            "industry": e.industry,
            "company_size_bucket": e.company_size_bucket,
            "sample_size": e.sample_size,
            "avg_roi": e.avg_roi,
            "median_roi": e.median_roi,
            "p25_roi": e.p25_roi,
            "p75_roi": e.p75_roi,
            "avg_savings": e.avg_savings,
            "avg_implementation_cost": e.avg_implementation_cost,
            "avg_payback_months": e.avg_payback_months,
            "success_rate": e.success_rate,
            "last_aggregated_at": e.last_aggregated_at,
        }
        for e in entries
    ]


@router.get("/categories")
def list_categories():
    return {"categories": [c.value for c in ProcessCategory]}


@router.post("/compare")
def compare_custom(
    category: str,
    roi: float,
    savings: float,
    payback_months: float,
    industry: str | None = None,
    ctx: AuthContext = Depends(get_current_context),
    benchmark_engine: BenchmarkEngine = Depends(get_benchmark_engine),
):
    comparison = benchmark_engine.compare(
        category=ProcessCategory(category),
        process_roi=roi,
        process_savings=savings,
        process_payback_months=payback_months,
        industry=industry,
    )
    if not comparison:
        raise HTTPException(status_code=404, detail="Insufficient benchmark data")
    return comparison.to_dict()
