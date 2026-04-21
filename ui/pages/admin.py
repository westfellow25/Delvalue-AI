"""Admin — system status, model health, cache stats."""

from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from api.config import get_settings
from data.database import engine
from data.models.organization import AuditLog, Organization, User
from data.models.process import (
    BenchmarkEntry,
    DecisionTrace,
    OpportunityScore,
    Process,
    ProcessMiningLog,
    SimulationRun,
)
from infrastructure.cache import get_cache

settings = get_settings()


def render():
    st.title("Admin")
    st.caption("System status, model health, and diagnostics")

    tab1, tab2, tab3 = st.tabs(["System Status", "Data Stats", "Cache & Performance"])

    with tab1:
        st.subheader("System Configuration")
        st.markdown(f"**App:** {settings.app_name} v{settings.app_version}")
        st.markdown(f"**Environment:** {settings.environment.value}")
        st.markdown(f"**Database:** {settings.database_url[:50]}...")
        st.markdown(f"**ML Model Dir:** {settings.ml_model_dir}")
        st.markdown(f"**Anthropic API:** {'Configured' if settings.anthropic_api_key else 'Not configured'}")

        st.subheader("Model Status")
        try:
            from api.dependencies import _get_ml_model
            ml = _get_ml_model()
            if ml and ml.is_trained:
                st.success(f"ML Model loaded: {ml.version}")
                st.json(ml.training_metrics)
            else:
                st.info("ML Model: Not trained (using heuristic fallback)")
                st.markdown(
                    "The ML model activates once 50+ completed implementations "
                    "with actual outcomes are recorded."
                )
        except Exception as e:
            st.info(f"ML Model: Heuristic mode ({e})")

        st.subheader("API Endpoints")
        st.markdown("""
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/signup` | POST | Create org + user |
| `/api/v1/auth/login` | POST | Get JWT token |
| `/api/v1/processes` | GET/POST | List / create processes |
| `/api/v1/processes/{id}/analyze` | POST | Full analysis |
| `/api/v1/processes/{id}/simulate` | POST | Monte Carlo |
| `/api/v1/processes/{id}/benchmark` | POST | Industry comparison |
| `/api/v1/processes/portfolio/analyze` | POST | Portfolio optimization |
| `/api/v1/discovery/document` | POST | Extract from document |
| `/api/v1/discovery/mine` | POST | Process mining |
| `/api/v1/monitoring/accuracy` | GET | Model accuracy |
| `/api/v1/benchmarks` | GET | List benchmarks |
| `/health` | GET | Health check |
| `/docs` | GET | OpenAPI docs |
""")

    with tab2:
        st.subheader("Database Statistics")
        with Session(engine) as db:
            stats = {
                "Organizations": db.query(Organization).count(),
                "Users": db.query(User).count(),
                "Processes": db.query(Process).filter(Process.is_deleted == False).count(),
                "Opportunity Scores": db.query(OpportunityScore).count(),
                "Decision Traces": db.query(DecisionTrace).count(),
                "Simulation Runs": db.query(SimulationRun).count(),
                "Benchmark Entries": db.query(BenchmarkEntry).count(),
                "Mining Events": db.query(ProcessMiningLog).count(),
                "Audit Logs": db.query(AuditLog).count(),
            }

        for name, count in stats.items():
            st.metric(name, count)

    with tab3:
        st.subheader("Cache Statistics")
        cache = get_cache()
        cache_stats = cache.stats()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cache Size", cache_stats["size"])
        c2.metric("Hits", cache_stats["hits"])
        c3.metric("Misses", cache_stats["misses"])
        c4.metric("Hit Rate", f"{cache_stats['hit_rate']:.0%}")

        if st.button("Clear Cache"):
            cache.clear()
            st.success("Cache cleared!")
            st.rerun()

        st.subheader("Integration Connectors")
        from integrations.connectors import list_connectors
        connectors = list_connectors()
        for c in connectors:
            st.markdown(f"**{c.name}** ({c.vendor}) — {c.description}")
            st.caption(f"Type: {c.type.value} | Capabilities: {', '.join(c.capabilities)}")
