import streamlit as st
import pandas as pd
from src.utils.database import Database

st.set_page_config(page_title="Opportunities", page_icon="🎯", layout="wide")

@st.cache_resource
def get_database():
    return Database("data/delvalue.db")

db = get_database()

st.title("🎯 Top Opportunities")

all_scores = db.get_opportunity_scores()

if not all_scores:
    st.warning("No opportunities yet. Go to Process Library to analyze processes.")
else:
    for i, score in enumerate(all_scores[:10], 1):
        with st.expander(f"**{i}. {score.process_name}** - Score: {score.overall_score:.1f}/100"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Recommendation:** {score.recommendation}")
                st.markdown(f"**Reasoning:** {score.reasoning}")
            
            with col2:
                st.metric("Feasibility", f"{score.feasibility_score:.0f}/100")
                st.metric("Value", f"{score.value_score:.0f}/100")
                st.metric("Risk", f"{score.risk_score:.0f}/100")
                st.metric("ROI", f"{score.roi_percentage:.0f}%")
