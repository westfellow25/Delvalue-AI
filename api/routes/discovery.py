"""Process discovery routes: document upload + event log mining."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.dependencies import get_discovery_engine, get_nlp_engine, get_orchestrator
from api.middleware.auth import AuthContext, require_analyst
from api.middleware.audit import record_audit
from api.schemas.process import EventLogBatch, MiningRequest
from core.agents.orchestrator import AgentOrchestrator
from core.engines.discovery import ProcessMiningEngine
from core.engines.nlp import NLPEngine
from data.database import get_db
from data.models.process import ProcessMiningLog

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post("/document")
async def extract_from_document(
    file: UploadFile = File(...),
    max_processes: int = Form(10),
    ctx: AuthContext = Depends(require_analyst()),
    db: Session = Depends(get_db),
    nlp: NLPEngine = Depends(get_nlp_engine),
):
    content = await file.read()
    text = nlp.extract_text(file.filename or "document.txt", content=content)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from document")

    processes = nlp.extract_processes_from_text(text, max_processes=max_processes)

    record_audit(db, ctx.organization_id, ctx.user.id if ctx.user else None,
                 "document_processed", "discovery",
                 details={"filename": file.filename, "extracted_count": len(processes)})

    return {
        "source_filename": file.filename,
        "extracted_processes": processes,
        "count": len(processes),
    }


@router.post("/event-logs/upload")
async def upload_event_log(
    file: UploadFile = File(...),
    source_system: str = Form("unknown"),
    ctx: AuthContext = Depends(require_analyst()),
    db: Session = Depends(get_db),
    discovery_engine: ProcessMiningEngine = Depends(get_discovery_engine),
):
    if not file.filename.endswith((".csv",)):
        raise HTTPException(status_code=400, detail="Only CSV event logs supported")

    content = (await file.read()).decode("utf-8", errors="ignore")
    count = discovery_engine.ingest_csv(
        csv_content=content,
        organization_id=ctx.organization_id,
        source_system=source_system,
    )
    db.commit()

    record_audit(db, ctx.organization_id, ctx.user.id if ctx.user else None,
                 "event_log_uploaded", "event_log", details={"events": count})

    return {"events_ingested": count, "source_system": source_system}


@router.post("/event-logs/batch")
def ingest_event_batch(
    payload: EventLogBatch,
    ctx: AuthContext = Depends(require_analyst()),
    db: Session = Depends(get_db),
):
    logs = [
        ProcessMiningLog(
            organization_id=ctx.organization_id,
            case_id=e.case_id,
            activity=e.activity,
            timestamp=e.timestamp,
            resource=e.resource,
            lifecycle=e.lifecycle,
            cost=e.cost,
            source_system=payload.source_system,
        )
        for e in payload.events
    ]
    db.add_all(logs)
    db.commit()

    record_audit(db, ctx.organization_id, ctx.user.id if ctx.user else None,
                 "event_log_uploaded", "event_log", details={"events": len(logs)})

    return {"events_ingested": len(logs)}


@router.post("/mine")
def run_mining(
    payload: MiningRequest,
    ctx: AuthContext = Depends(require_analyst()),
    db: Session = Depends(get_db),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    # Load events from DB
    logs = (
        db.query(ProcessMiningLog)
        .filter(ProcessMiningLog.organization_id == ctx.organization_id)
        .order_by(ProcessMiningLog.case_id, ProcessMiningLog.timestamp)
        .all()
    )
    if not logs:
        raise HTTPException(status_code=400, detail="No event log data available")

    events = [
        {
            "case_id": l.case_id,
            "activity": l.activity,
            "timestamp": l.timestamp,
            "resource": l.resource,
        }
        for l in logs
    ]
    result = orchestrator.discover_from_event_log(
        events=events, hourly_cost=payload.hourly_cost,
    )

    record_audit(db, ctx.organization_id, ctx.user.id if ctx.user else None,
                 "process_mining_run", "mining_analysis",
                 details={"events": len(events), "cases": result["summary"]["total_cases"]})

    return result
