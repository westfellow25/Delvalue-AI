"""
DelValue AI — Professional Streamlit Application

Enterprise-grade UI for automation decision intelligence.
Talks to the FastAPI backend for all operations.
"""

from __future__ import annotations

import streamlit as st

# -- Page Config (must be first Streamlit call) --
st.set_page_config(
    page_title="DelValue AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -- Initialize session state --
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.access_token = None
    st.session_state.user = None
    st.session_state.organization = None

# -- Initialize backend --
# For the UI, we import engines directly (same-process) for simplicity.
# In production, the UI would call the FastAPI API via httpx.
from data.database import init_db, engine
from data.models.base import Base
from data.seeds.benchmarks import seed_benchmarks
from sqlalchemy.orm import Session

@st.cache_resource
def _init_backend():
    init_db()
    with Session(engine) as db:
        from data.models.process import BenchmarkEntry
        if db.query(BenchmarkEntry).count() == 0:
            seed_benchmarks(db)
    return True

_init_backend()


# -- Sidebar --
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=48)
    st.title("DelValue AI")
    st.caption("Decision Intelligence for Automation")
    st.divider()

    st.markdown("### Navigation")
    page = st.radio(
        "Go to",
        [
            "About",
            "Dashboard",
            "Process Library",
            "Analyze Process",
            "Portfolio",
            "Simulation Lab",
            "Process Mining",
            "Benchmarks",
            "Monitoring",
            "Admin",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption("v2.0 | ML Scoring + Monte Carlo")
    st.caption("© 2025 DelValue AI")


# -- Page routing --
if page == "About":
    from ui.pages.about import render
    render()
elif page == "Dashboard":
    from ui.pages.dashboard import render
    render()
elif page == "Process Library":
    from ui.pages.process_library import render
    render()
elif page == "Analyze Process":
    from ui.pages.analyze import render
    render()
elif page == "Portfolio":
    from ui.pages.portfolio import render
    render()
elif page == "Simulation Lab":
    from ui.pages.simulation import render
    render()
elif page == "Process Mining":
    from ui.pages.mining import render
    render()
elif page == "Benchmarks":
    from ui.pages.benchmarks_page import render
    render()
elif page == "Monitoring":
    from ui.pages.monitoring_page import render
    render()
elif page == "Admin":
    from ui.pages.admin import render
    render()
