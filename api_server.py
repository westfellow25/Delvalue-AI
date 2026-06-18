"""DelValue dashboard API — opportunity ranking endpoint.

DelValue ships as a Streamlit app with no REST surface. This thin FastAPI
wrapper exposes the real DecisionEngine (src/core/decision_engine.py) over HTTP
so the unified web dashboard can call it. It seeds the banking AML/KYC/payments
processes, ranks them, and maps OpportunityScore -> the board shape the
/prioritize page consumes.

Run:
    .venv/Scripts/python.exe -m uvicorn api_server:app --port 8099
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Run from the delvalue root so the `src` package imports resolve.
sys.path.insert(0, str(Path(__file__).parent))

from src.core.decision_engine import DecisionEngine  # noqa: E402
from src.models.process import Process, ProcessCategory  # noqa: E402

app = FastAPI(title="DelValue Dashboard API", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# Banking AML/KYC/payments portfolio. processId values line up with the
# Map page so an opportunity ties back to its process across the dashboard.
_WEEKS = 52
_HOURLY = 65.0
_SEED = [
    dict(id="aml-alert-triage", name="AML alert briefing agent",
         description="Analysts triage AML alerts across case manager, core banking and sanctions data, gathering context and drafting a disposition narrative before human approval.",
         category=ProcessCategory.FINANCE, duration_minutes=45, vol_week=4200,
         people=38, systems=["Actimize", "Case Manager", "Core Banking"],
         pain=["Repetitive narrative review", "Manual context gathering", "High volume", "Slow prep"],
         sop=True),
    dict(id="kyc-doc-review", name="KYC document extraction",
         description="Onboarding analysts review KYC documents, extract entity data and run rule-based checks against policy before approving new clients.",
         category=ProcessCategory.FINANCE, duration_minutes=32, vol_week=2600,
         people=24, systems=["Fenergo", "DMS", "Sanctions API"],
         pain=["Document extraction", "Manual data entry", "Rule-based checks"],
         sop=True),
    dict(id="sanctions-screening", name="Sanctions false-positive triage",
         description="Sanctions desk dispositions watchlist matches, clearing false positives against name, geography and transaction context.",
         category=ProcessCategory.FINANCE, duration_minutes=18, vol_week=6800,
         people=17, systems=["Watchlist Engine", "Case Manager"],
         pain=["List matching", "False-positive disposition", "High volume"],
         sop=True),
    dict(id="payments-fraud-review", name="Payments fraud copilot",
         description="Fraud operations review flagged payments, judge edge cases and contact customers where needed before releasing or blocking.",
         category=ProcessCategory.FINANCE, duration_minutes=28, vol_week=3300,
         people=21, systems=["Falcon", "Case Manager", "Core Banking"],
         pain=["Judgement on edge cases", "Customer contact"],
         sop=False),
    dict(id="invoice-3way-match", name="Invoice match auto-clear",
         description="Accounts payable performs three-way match across ERP, OCR and vendor portal, handling exceptions and vendor disputes.",
         category=ProcessCategory.FINANCE, duration_minutes=12, vol_week=5100,
         people=14, systems=["ERP", "OCR", "Vendor Portal"],
         pain=["Exception handling", "Vendor disputes"],
         sop=True),
]


def _processes() -> list[Process]:
    out = []
    for s in _SEED:
        out.append(Process(
            id=s["id"], name=s["name"], description=s["description"],
            category=s["category"], frequency=f"{s['vol_week']}/week",
            duration_minutes=s["duration_minutes"],
            annual_volume=s["vol_week"] * _WEEKS, people_involved=s["people"],
            hourly_cost=_HOURLY, systems_used=s["systems"],
            pain_points=s["pain"], sop_exists=s["sop"],
        ))
    return out


def _decision(recommendation: str) -> str:
    r = recommendation.upper()
    if "STRONG RECOMMEND" in r or r == "RECOMMEND":
        return "GO"
    if "CONSIDER" in r:
        return "DEFER"
    return "NO-GO"


def _effort(score) -> str:
    lvl = str(getattr(score, "risk_level", "")).lower()
    if "critical" in lvl or "high" in lvl:
        return "High"
    if "medium" in lvl:
        return "Medium"
    return "Low"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "delvalue-dashboard"}


@app.get("/opportunities")
def opportunities() -> list[dict]:
    engine = DecisionEngine()
    ranked = engine.rank_opportunities(_processes())
    return [
        {
            "id": f"opp-{s.process_id}",
            "name": s.process_name,
            "processId": s.process_id,
            "decision": _decision(s.recommendation),
            "value": round(s.estimated_annual_savings),
            "roiPct": round(s.roi_percentage),
            "paybackMonths": round(s.payback_months, 1),
            "confidence": round(s.confidence_level, 2),
            "effort": _effort(s),
            "rationale": s.reasoning,
        }
        for s in ranked
    ]
