"""Process Library — CRUD, search, bulk import."""

from __future__ import annotations

import json

import streamlit as st
from sqlalchemy.orm import Session

from data.database import engine
from data.models.process import (
    DataSource,
    DocumentationQuality,
    Process,
    ProcessCategory,
    ProcessFrequency,
)
from data.repositories.process_repository import ProcessRepository

DEMO_ORG = "demo-org"


def render():
    st.title("Process Library")
    st.caption("Manage your business processes")

    tab1, tab2, tab3 = st.tabs(["Browse", "Add Process", "Bulk Import"])

    with tab1:
        _render_browse()

    with tab2:
        _render_add_form()

    with tab3:
        _render_bulk_import()


def _render_browse():
    with Session(engine) as db:
        repo = ProcessRepository(db, DEMO_ORG)

        col1, col2 = st.columns([2, 1])
        with col1:
            search = st.text_input("Search processes", placeholder="Type to search...")
        with col2:
            categories = ["All"] + [c.value for c in ProcessCategory]
            cat_filter = st.selectbox("Category", categories)

        cat_enum = ProcessCategory(cat_filter) if cat_filter != "All" else None
        processes, total = repo.list_all(
            category=cat_enum,
            search=search if search else None,
            limit=100,
        )

        st.caption(f"Showing {len(processes)} of {total} processes")

        if not processes:
            st.info("No processes found. Add one using the 'Add Process' tab.")
            return

        for p in processes:
            with st.expander(f"**{p.name}** — {p.category.value} | {p.frequency.value}"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Annual Volume", f"{p.annual_volume:,}")
                c2.metric("People", p.people_involved)
                c3.metric("Duration", f"{p.duration_minutes} min")
                c4.metric("Hourly Cost", f"${p.hourly_cost:.0f}")

                if p.description:
                    st.markdown(p.description[:300])

                systems = json.loads(p.systems_used) if p.systems_used else []
                if systems:
                    st.markdown(f"**Systems:** {', '.join(systems)}")

                if p.scores:
                    latest = p.scores[0]
                    st.success(
                        f"Latest score: **{latest.overall_score:.2f}** | "
                        f"ROI: {latest.roi_percentage:.0f}% | "
                        f"Rec: {latest.recommendation.value}"
                    )

                col_del, _ = st.columns([1, 5])
                with col_del:
                    if st.button("Delete", key=f"del_{p.id}", type="secondary"):
                        repo.soft_delete(p.id, "ui-user")
                        db.commit()
                        st.rerun()


def _render_add_form():
    with st.form("add_process"):
        st.subheader("Add New Process")

        name = st.text_input("Process Name*", placeholder="e.g., Invoice Processing")
        description = st.text_area("Description", placeholder="Describe the process...")

        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox("Category*", [c.value for c in ProcessCategory])
            frequency = st.selectbox("Frequency*", [f.value for f in ProcessFrequency])
        with col2:
            annual_volume = st.number_input("Annual Volume*", min_value=1, value=1000)
            duration = st.number_input("Duration (min)*", min_value=0.1, value=30.0)
        with col3:
            people = st.number_input("People Involved*", min_value=1, value=3)
            hourly_cost = st.number_input("Hourly Cost ($)*", min_value=1.0, value=50.0)

        col4, col5 = st.columns(2)
        with col4:
            systems = st.text_input("Systems Used (comma-separated)", placeholder="SAP, Salesforce")
            pain_points = st.text_input("Pain Points (comma-separated)")
        with col5:
            doc_quality = st.selectbox("Documentation Quality", [d.value for d in DocumentationQuality])
            sop_exists = st.checkbox("SOP Exists")

        col6, col7, col8 = st.columns(3)
        with col6:
            decision_points = st.number_input("Decision Points", min_value=0, value=2)
        with col7:
            exceptions = st.number_input("Exceptions", min_value=0, value=1)
        with col8:
            requires_judgment = st.checkbox("Requires Human Judgment")

        submitted = st.form_submit_button("Add Process", type="primary")

        if submitted and name:
            with Session(engine) as db:
                process = Process(
                    organization_id=DEMO_ORG,
                    name=name,
                    description=description,
                    category=ProcessCategory(category),
                    frequency=ProcessFrequency(frequency),
                    annual_volume=annual_volume,
                    duration_minutes=duration,
                    people_involved=people,
                    hourly_cost=hourly_cost,
                    systems_used=json.dumps([s.strip() for s in systems.split(",") if s.strip()]) if systems else None,
                    pain_points=json.dumps([p.strip() for p in pain_points.split(",") if p.strip()]) if pain_points else None,
                    documentation_quality=DocumentationQuality(doc_quality),
                    sop_exists=sop_exists,
                    num_decision_points=decision_points,
                    num_exceptions=exceptions,
                    requires_judgment=requires_judgment,
                    source=DataSource.MANUAL,
                    created_by="ui-user",
                )
                db.add(process)
                db.commit()
            st.success(f"Process '{name}' added successfully!")
            st.rerun()


def _render_bulk_import():
    st.subheader("Bulk Import")
    st.markdown("Upload a JSON file with an array of process objects.")

    uploaded = st.file_uploader("Upload JSON", type=["json"])
    if uploaded:
        try:
            data = json.loads(uploaded.read())
            processes = data if isinstance(data, list) else data.get("processes", [])
            st.info(f"Found {len(processes)} processes in file")

            if st.button("Import All", type="primary"):
                count = 0
                with Session(engine) as db:
                    for p in processes:
                        try:
                            proc = Process(
                                organization_id=DEMO_ORG,
                                name=p["name"],
                                description=p.get("description"),
                                category=ProcessCategory(p.get("category", "operations")),
                                frequency=ProcessFrequency(p.get("frequency", "monthly")),
                                annual_volume=p.get("annual_volume", 100),
                                duration_minutes=p.get("duration_minutes", 30),
                                people_involved=p.get("people_involved", 2),
                                hourly_cost=p.get("hourly_cost", 50),
                                systems_used=json.dumps(p.get("systems_used", [])),
                                pain_points=json.dumps(p.get("pain_points", [])),
                                documentation_quality=DocumentationQuality(p.get("documentation_quality", "basic")),
                                sop_exists=p.get("sop_exists", False),
                                source=DataSource.MANUAL,
                                created_by="bulk-import",
                            )
                            db.add(proc)
                            count += 1
                        except Exception:
                            continue
                    db.commit()
                st.success(f"Imported {count} processes!")
        except json.JSONDecodeError:
            st.error("Invalid JSON file")
