import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.utils.database import Database

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

@st.cache_resource
def get_database():
    return Database("data/delvalue.db")

db = get_database()

st.title("📊 Portfolio Dashboard")
st.markdown("Overview of automation opportunities")

st.markdown("---")

all_processes = db.get_all_processes()
all_scores = db.get_opportunity_scores()

if not all_scores:
    st.warning("No analysis available. Go to Process Library to add and analyze processes.")
    st.stop()

# Metrics
col1, col2, col3, col4 = st.columns(4)

total_savings = sum(s.estimated_annual_savings for s in all_scores)
total_investment = sum(s.implementation_cost for s in all_scores)
portfolio_roi = ((total_savings - total_investment) / total_investment * 100) if total_investment > 0 else 0

with col1:
    st.metric("Processes", len(all_processes))
with col2:
    st.metric("Annual Savings", f"${total_savings:,.0f}")
with col3:
    st.metric("Investment", f"${total_investment:,.0f}")
with col4:
    st.metric("ROI", f"{portfolio_roi:.0f}%")

st.markdown("---")

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Top 10 by Score")
    
    top_10 = all_scores[:10]
    df = pd.DataFrame([{'Process': s.process_name, 'Score': s.overall_score} for s in top_10])
    
    fig = px.bar(df, x='Score', y='Process', orientation='h', color='Score', color_continuous_scale='Blues')
    fig.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("💰 Savings vs Investment")
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Savings', x=[s.process_name for s in top_10], y=[s.estimated_annual_savings for s in top_10], marker_color='lightblue'))
    fig.add_trace(go.Bar(name='Cost', x=[s.process_name for s in top_10], y=[s.implementation_cost for s in top_10], marker_color='coral'))
    fig.update_layout(barmode='group', height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
