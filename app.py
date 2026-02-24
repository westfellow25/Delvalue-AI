"""
DelValue AI - Main Application
Home page and navigation
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from src.utils.database import Database

st.set_page_config(
    page_title="DelValue AI - Home",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def get_database():
    return Database("data/delvalue.db")

def main():
    st.title("🤖 DelValue AI")
    st.markdown("### AI-Powered Decision Intelligence for Transformation")
    
    st.markdown("---")
    
    db = get_database()
    all_processes = db.get_all_processes()
    all_scores = db.get_opportunity_scores()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("## Welcome to DelValue AI")
        
        st.markdown("""
        DelValue AI helps you make **intelligent decisions** about which business processes 
        to automate with AI and automation.
        
        **Key Features:**
        - 📊 Data-driven scoring
        - 💰 ROI predictions
        - 🎯 Smart prioritization
        - 📈 Implementation tracking
        - 📋 Strategic reports
        """)
    
    with col2:
        st.markdown("## 📈 Quick Stats")
        
        st.metric("Total Processes", len(all_processes))
        st.metric("Opportunities Analyzed", len(all_scores))
        
        if all_scores:
            total_savings = sum(s.estimated_annual_savings for s in all_scores)
            st.metric("Potential Annual Savings", f"${total_savings:,.0f}")
    
    st.markdown("---")
    
    if all_processes:
        st.markdown("## 🕐 Recent Activity")
        
        recent = sorted(all_processes, key=lambda p: p.created_at, reverse=True)[:5]
        
        df = pd.DataFrame([{
            'Process': p.name,
            'Category': p.category,
            'Volume': f"{p.annual_volume:,}/year",
            'Added': p.created_at.strftime('%Y-%m-%d %H:%M')
        } for p in recent])
        
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p><strong>DelValue AI</strong> - Make smarter automation decisions</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
