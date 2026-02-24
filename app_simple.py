"""
DelValue AI - Streamlit Web Application
AI-powered decision intelligence for automation opportunities
"""

import streamlit as st
import pandas as pd
from typing import List
import plotly.express as px
import plotly.graph_objects as go

from src.models.process import Process, OpportunityScore
from src.agents.analysis_agent import AnalysisAgent
from src.utils.data_loader import load_synthetic_processes

# Page config
st.set_page_config(
    page_title="DelValue AI - Automation Intelligence",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("🤖 DelValue AI")
    st.subheader("AI-Powered Decision Intelligence for Transformation")
    
    # Load data
    processes = load_synthetic_processes()
    
    st.success(f"✅ Loaded {len(processes)} processes")
    
    # Simple table view
    st.header("Processes")
    
    df = pd.DataFrame([{
        'Name': p.name,
        'Category': p.category,
        'Annual Volume': p.annual_volume,
        'People': p.people_involved
    } for p in processes])
    
    st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
