"""
DelValue AI — Process Repository

Data access layer for processes and scores. Encapsulates all DB queries.
Supports filtering, pagination, and bulk operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session

from data.models.process import (
    Process,
    OpportunityScore,
    DecisionTrace,
    SimulationRun,
    ProcessCategory,
    ImplementationStatus,
    Recommendation,
)


class ProcessRepository:
    """Repository for Process CRUD and queries."""

    def __init__(self, session: Session, organization_id: str):
        self.session = session
        self.org_id = organization_id

    def _base_query(self):
        return self.session.query(Process).filter(
            Process.organization_id == self.org_id,
            Process.is_deleted == False,
        )

    def get_by_id(self, process_id: str) -> Optional[Process]:
        return self._base_query().filter(Process.id == process_id).first()

    def list_all(
        self,
        category: Optional[ProcessCategory] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Process], int]:
        q = self._base_query()
        if category:
            q = q.filter(Process.category == category)
        if search:
            q = q.filter(Process.name.ilike(f"%{search}%"))
        total = q.count()
        processes = q.order_by(desc(Process.updated_at)).offset(offset).limit(limit).all()
        return processes, total

    def create(self, process: Process) -> Process:
        process.organization_id = self.org_id
        self.session.add(process)
        self.session.flush()
        return process

    def bulk_create(self, processes: list[Process]) -> list[Process]:
        for p in processes:
            p.organization_id = self.org_id
        self.session.add_all(processes)
        self.session.flush()
        return processes

    def update(self, process: Process) -> Process:
        process.version += 1
        self.session.flush()
        return process

    def soft_delete(self, process_id: str, user_id: str) -> bool:
        process = self.get_by_id(process_id)
        if not process:
            return False
        process.soft_delete(user_id)
        self.session.flush()
        return True

    def count_by_category(self) -> dict[str, int]:
        results = (
            self._base_query()
            .with_entities(Process.category, func.count(Process.id))
            .group_by(Process.category)
            .all()
        )
        return {str(cat.value): count for cat, count in results}

    def get_unscored(self) -> list[Process]:
        """Processes that have never been scored."""
        scored_ids = (
            self.session.query(OpportunityScore.process_id)
            .filter(OpportunityScore.organization_id == self.org_id)
            .subquery()
        )
        return (
            self._base_query()
            .filter(~Process.id.in_(scored_ids))
            .all()
        )


class ScoreRepository:
    """Repository for OpportunityScore queries."""

    def __init__(self, session: Session, organization_id: str):
        self.session = session
        self.org_id = organization_id

    def _base_query(self):
        return self.session.query(OpportunityScore).filter(
            OpportunityScore.organization_id == self.org_id
        )

    def get_latest_for_process(self, process_id: str) -> Optional[OpportunityScore]:
        return (
            self._base_query()
            .filter(OpportunityScore.process_id == process_id)
            .order_by(desc(OpportunityScore.analyzed_at))
            .first()
        )

    def create(self, score: OpportunityScore) -> OpportunityScore:
        score.organization_id = self.org_id
        self.session.add(score)
        self.session.flush()
        return score

    def get_top_opportunities(
        self,
        limit: int = 20,
        min_score: float = 0.0,
        recommendation: Optional[Recommendation] = None,
    ) -> list[OpportunityScore]:
        q = self._base_query().filter(OpportunityScore.overall_score >= min_score)
        if recommendation:
            q = q.filter(OpportunityScore.recommendation == recommendation)
        return q.order_by(desc(OpportunityScore.overall_score)).limit(limit).all()

    def get_portfolio_summary(self) -> dict:
        """Aggregate portfolio statistics."""
        scores = self._base_query().all()
        if not scores:
            return {
                "total_processes_scored": 0,
                "total_potential_savings": 0,
                "total_implementation_cost": 0,
                "avg_roi": 0,
                "avg_confidence": 0,
            }
        return {
            "total_processes_scored": len(scores),
            "total_potential_savings": sum(s.estimated_annual_savings for s in scores),
            "total_implementation_cost": sum(s.implementation_cost for s in scores),
            "avg_roi": sum(s.roi_percentage for s in scores) / len(scores),
            "avg_confidence": sum(s.confidence_level for s in scores) / len(scores),
            "avg_payback_months": sum(s.payback_months for s in scores) / len(scores),
        }


class TraceRepository:
    """Repository for DecisionTrace — the learning loop data."""

    def __init__(self, session: Session, organization_id: str):
        self.session = session
        self.org_id = organization_id

    def _base_query(self):
        return self.session.query(DecisionTrace).filter(
            DecisionTrace.organization_id == self.org_id
        )

    def create(self, trace: DecisionTrace) -> DecisionTrace:
        trace.organization_id = self.org_id
        self.session.add(trace)
        self.session.flush()
        return trace

    def record_outcome(
        self,
        trace_id: str,
        actual_roi: float,
        actual_savings: float,
        actual_cost: float,
        actual_payback: float,
        lessons: Optional[str] = None,
    ) -> Optional[DecisionTrace]:
        trace = self._base_query().filter(DecisionTrace.id == trace_id).first()
        if not trace:
            return None
        trace.actual_roi = actual_roi
        trace.actual_annual_savings = actual_savings
        trace.actual_implementation_cost = actual_cost
        trace.actual_payback_months = actual_payback
        trace.variance_roi = actual_roi - trace.predicted_roi
        trace.variance_savings = actual_savings - trace.predicted_annual_savings
        trace.variance_cost = actual_cost - trace.predicted_implementation_cost
        trace.variance_timeline = actual_payback - trace.predicted_payback_months
        trace.lessons_learned = lessons
        self.session.flush()
        return trace

    def get_completed_traces(self, min_count: int = 0) -> list[DecisionTrace]:
        """Get traces with actual outcomes — training data for ML."""
        traces = (
            self._base_query()
            .filter(
                DecisionTrace.actual_roi.isnot(None),
                DecisionTrace.implementation_status.in_([
                    ImplementationStatus.COMPLETE,
                    ImplementationStatus.SCALING,
                ]),
            )
            .all()
        )
        return traces

    def get_training_data(self) -> list[DecisionTrace]:
        """Get traces not yet used for training."""
        return (
            self._base_query()
            .filter(
                DecisionTrace.actual_roi.isnot(None),
                DecisionTrace.used_for_training == False,
            )
            .all()
        )

    def get_calibration_data(self) -> list[dict]:
        """Get predicted vs actual pairs for confidence calibration."""
        traces = self.get_completed_traces()
        return [
            {
                "predicted_roi": t.predicted_roi,
                "actual_roi": t.actual_roi,
                "predicted_savings": t.predicted_annual_savings,
                "actual_savings": t.actual_annual_savings,
                "predicted_cost": t.predicted_implementation_cost,
                "actual_cost": t.actual_implementation_cost,
                "predicted_confidence": t.predicted_confidence,
            }
            for t in traces
        ]
