"""Process Mining — upload event logs, discover processes, find automation candidates."""

from __future__ import annotations

import io

import streamlit as st

from core.engines.discovery import ProcessMiningEngine


def render():
    st.title("Process Mining")
    st.caption("Discover processes from event log data — no manual documentation needed")

    tab1, tab2 = st.tabs(["Upload & Mine", "Sample Data"])

    with tab1:
        st.markdown(
            "Upload a CSV event log with columns: `case_id`, `activity`, `timestamp` "
            "(and optionally `resource`)."
        )
        uploaded = st.file_uploader("Upload Event Log (CSV)", type=["csv"])

        hourly_cost = st.number_input("Avg Hourly Cost ($)", min_value=1.0, value=75.0)

        if uploaded and st.button("Run Process Mining", type="primary"):
            _mine_file(uploaded, hourly_cost)

    with tab2:
        st.markdown("Try with sample event log data:")
        if st.button("Generate & Mine Sample Data"):
            _mine_sample(hourly_cost=75.0)


def _mine_file(uploaded, hourly_cost):
    content = uploaded.read().decode("utf-8", errors="ignore")
    import csv

    reader = csv.DictReader(io.StringIO(content))
    events = []
    for row in reader:
        try:
            from core.engines.discovery import ProcessMiningEngine
            ts = ProcessMiningEngine._parse_timestamp(row.get("timestamp", ""))
            events.append({
                "case_id": row["case_id"],
                "activity": row["activity"],
                "timestamp": ts,
                "resource": row.get("resource"),
            })
        except Exception:
            continue

    if not events:
        st.error("No valid events found in the file.")
        return

    _run_mining(events, hourly_cost)


def _mine_sample(hourly_cost):
    from datetime import datetime, timedelta
    import random

    activities = [
        "Receive Request", "Validate Data", "Check Inventory",
        "Approve Request", "Process Order", "Generate Invoice",
        "Send Confirmation", "Close Case",
    ]
    events = []
    for case_num in range(1, 201):
        case_id = f"CASE-{case_num:04d}"
        ts = datetime(2024, 1, 1) + timedelta(hours=random.randint(0, 8760))
        for i, act in enumerate(activities):
            if random.random() < 0.05 and i > 2:
                break  # occasional early termination
            events.append({
                "case_id": case_id,
                "activity": act,
                "timestamp": ts,
                "resource": f"User-{random.randint(1, 10)}",
            })
            ts += timedelta(minutes=random.randint(5, 480))

    _run_mining(events, hourly_cost)


def _run_mining(events, hourly_cost):
    engine = ProcessMiningEngine()

    with st.spinner(f"Mining {len(events)} events..."):
        result = engine.mine(events=events, hourly_cost=hourly_cost)

    data = result.to_dict()
    summary = data["summary"]

    st.divider()
    st.subheader("Mining Results")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Cases", summary["total_cases"])
    c2.metric("Total Events", summary["total_events"])
    c3.metric("Avg Duration", f"{summary['avg_case_duration_hours']:.1f} hrs")
    c4.metric("Conformance", f"{data['conformance']['fitness']:.0%}")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Activities", "Process Variants", "Bottlenecks", "Automation Candidates",
    ])

    with tab1:
        st.markdown("**Activity Statistics:**")
        for a in data["activities"][:15]:
            st.markdown(
                f"- **{a['activity']}** — "
                f"{a['frequency']} times, "
                f"avg {a['avg_duration_minutes']:.1f} min, "
                f"automation score: {a['automation_score']:.2f}"
            )

    with tab2:
        st.markdown(f"**{len(data['variants'])} distinct variants discovered:**")
        for i, v in enumerate(data["variants"][:10], 1):
            seq = " → ".join(v["sequence"][:6])
            if len(v["sequence"]) > 6:
                seq += " → ..."
            st.markdown(
                f"**{i}. [{v['pct_of_total']:.1f}%]** {seq} "
                f"({v['frequency']} cases, {v['avg_duration_hours']:.1f} hrs avg)"
            )

    with tab3:
        if data["bottlenecks"]:
            for b in data["bottlenecks"]:
                severity = "🔴" if b["avg_waiting_time_hours"] > 8 else "🟡" if b["avg_waiting_time_hours"] > 2 else "🟢"
                st.markdown(f"{severity} **{b['activity']}** — {b['description']}")
        else:
            st.info("No significant bottlenecks detected.")

    with tab4:
        if data["automation_candidates"]:
            for i, c in enumerate(data["automation_candidates"], 1):
                st.success(
                    f"**{i}. {c['name']}** (score: {c['automation_score']:.2f})\n\n"
                    f"{c['rationale']}\n\n"
                    f"Estimated hours saved: **{c['estimated_hours_saved']:.0f}/year**"
                )
        else:
            st.info("No automation candidates identified.")
