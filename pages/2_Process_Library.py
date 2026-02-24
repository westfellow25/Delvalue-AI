import streamlit as st
import pandas as pd
from src.models.process import Process, ProcessCategory
from src.agents.analysis_agent import AnalysisAgent
from src.utils.data_loader import load_synthetic_processes
from src.utils.database import Database

st.set_page_config(page_title="Process Library", page_icon="📁", layout="wide")

@st.cache_resource
def get_database():
    return Database("data/delvalue.db")

@st.cache_resource
def get_agent():
    return AnalysisAgent()

db = get_database()
agent = get_agent()

st.title("📁 Process Library")

tab1, tab2 = st.tabs(["📚 All Processes", "➕ Add Process"])

with tab1:
    all_processes = db.get_all_processes()
    
    if not all_processes:
        st.info("No processes yet.")
        
        if st.button("📚 Load Sample Data"):
            synthetic = load_synthetic_processes()
            for p in synthetic:
                db.save_process(p)
            st.success(f"✅ Loaded {len(synthetic)} processes!")
            st.rerun()
    else:
        st.subheader(f"📋 {len(all_processes)} Processes")
        
        df = pd.DataFrame([{
            'Name': p.name,
            'Category': p.category,
            'Volume': f"{p.annual_volume:,}",
            'People': p.people_involved,
        } for p in all_processes])
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear All"):
                for p in all_processes:
                    db.delete_process(p.id)
                st.rerun()
        with col2:
            if st.button("🔄 Re-analyze"):
                with st.spinner("Analyzing..."):
                    scores = agent.analyze_portfolio(all_processes)
                    for s in scores:
                        db.save_opportunity_score(s)
                st.success("✅ Done!")
                st.rerun()

with tab2:
    st.subheader("➕ Add Process")
    
    with st.form("add"):
        name = st.text_input("Name *")
        desc = st.text_area("Description *")
        cat = st.selectbox("Category", [c.value for c in ProcessCategory])
        vol = st.number_input("Annual Volume", value=1000)
        dur = st.number_input("Duration (min)", value=30)
        people = st.number_input("People", value=5)
        
        if st.form_submit_button("Add") and name and desc:
            p = Process(name=name, description=desc, category=cat, frequency="daily", duration_minutes=dur, annual_volume=vol, people_involved=people, hourly_cost=50, systems_used=[], pain_points=[], stakeholders=[], source="manual")
            db.save_process(p)
            st.success("✅ Added!")
            st.rerun()
