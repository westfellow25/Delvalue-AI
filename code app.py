"""
DelValue AI - Streamlit Web Application
AI-powered decision intelligence for automation opportunities
"""

import streamlit as st
import pandas as pd
from typing import List, Optional
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
from datetime import datetime

from src.models.process import Process, ProcessCategory
from src.agents.analysis_agent import AnalysisAgent
from src.utils.data_loader import load_synthetic_processes
from src.utils.database import Database

# Page config
st.set_page_config(
    page_title="DelValue AI - Automation Intelligence",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
@st.cache_resource
def get_database():
    """Initialize and cache database connection"""
    return Database("data/delvalue.db")


@st.cache_resource
def get_analysis_agent():
    """Initialize and cache the Analysis Agent"""
    try:
        return AnalysisAgent()
    except Exception:
        return AnalysisAgent()


# Session state initialization
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False


def save_uploaded_file(uploaded_file) -> str:
    """Save uploaded file to uploads directory"""
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / uploaded_file.name
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return str(file_path)


def extract_text_from_upload(file_path: str) -> str:
    """Extract text from uploaded file (simple version without LLM)"""
    from PyPDF2 import PdfReader
    import docx
    
    path = Path(file_path)
    ext = path.suffix.lower()
    
    try:
        if ext == '.pdf':
            reader = PdfReader(file_path)
            text = "\n".join([page.extract_text() for page in reader.pages])
            return text
        elif ext in ['.docx', '.doc']:
            doc = docx.Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs])
            return text
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return ""
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return ""


def manual_process_form():
    """Form for manually entering process information"""
    st.subheader("➕ Add Process Manually")
    
    with st.form("manual_process_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Process Name *", placeholder="e.g., Invoice Processing")
            
            description = st.text_area(
                "Process Description *",
                placeholder="Detailed description of the process...",
                height=100
            )
            
            category = st.selectbox(
                "Category *",
                options=[c.value for c in ProcessCategory],
                format_func=lambda x: x.replace("_", " ").title()
            )
            
            frequency = st.text_input(
                "Frequency *",
                placeholder="e.g., 'daily', '100x/day', 'weekly'"
            )
            
            duration_minutes = st.number_input(
                "Duration (minutes per execution) *",
                min_value=1,
                value=30
            )
        
        with col2:
            annual_volume = st.number_input(
                "Annual Volume *",
                min_value=1,
                value=1000,
                help="Number of times this process runs per year"
            )
            
            people_involved = st.number_input(
                "People Involved *",
                min_value=1,
                value=5
            )
            
            hourly_cost = st.number_input(
                "Hourly Cost (USD) *",
                min_value=1.0,
                value=50.0,
                step=5.0
            )
            
            systems_used = st.text_area(
                "Systems Used (one per line)",
                placeholder="SAP\nEmail\nExcel",
                height=80
            )
            
            pain_points = st.text_area(
                "Pain Points (one per line)",
                placeholder="Manual data entry\nFrequent errors",
                height=80
            )
        
        submitted = st.form_submit_button("➕ Add Process", use_container_width=True)
        
        if submitted:
            # Validate
            if not name or not description:
                st.error("Please fill in all required fields (*)")
                return None
            
            # Parse lists
            systems_list = [s.strip() for s in systems_used.split('\n') if s.strip()]
            pain_points_list = [p.strip() for p in pain_points.split('\n') if p.strip()]
            
            # Create process
            try:
                process = Process(
                    name=name,
                    description=description,
                    category=category,
                    frequency=frequency,
                    duration_minutes=duration_minutes,
                    annual_volume=annual_volume,
                    people_involved=people_involved,
                    hourly_cost=hourly_cost,
                    systems_used=systems_list,
                    pain_points=pain_points_list,
                    stakeholders=[],
                    source="manual_entry"
                )
                
                # Save to database
                db = get_database()
                if db.save_process(process):
                    return process
                else:
                    st.error("Failed to save process to database")
                    return None
                    
            except Exception as e:
                st.error(f"Error creating process: {e}")
                return None
    
    return None


def analyze_processes(processes: List[Process]):
    """Analyze processes and save to database"""
    agent = get_analysis_agent()
    db = get_database()
    
    with st.spinner("🤖 Analyzing processes..."):
        scores = agent.analyze_portfolio(processes, top_n=None)
    
    # Save scores to database
    for score in scores:
        db.save_opportunity_score(score)
    
    st.session_state.analysis_done = True
    return scores


def main():
    """Main application"""
    
    # Header
    st.title("🤖 DelValue AI")
    st.subheader("AI-Powered Decision Intelligence for Transformation")
    
    # Sidebar
    st.sidebar.title("⚙️ Navigation")
    
    page = st.sidebar.radio(
        "Select Page",
        ["🏠 Home", "📁 Manage Processes", "📊 Analysis Dashboard"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 Quick Stats")
    
    db = get_database()
    all_processes = db.get_all_processes()
    st.sidebar.metric("Total Processes", len(all_processes))
    if st.session_state.analysis_done:
        scores = db.get_opportunity_scores()
        st.sidebar.metric("Analyzed", len(scores))
    
    # HOME PAGE
    if page == "🏠 Home":
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🎯 What is DelValue AI?")
            st.info("""
            **DelValue AI** helps companies make **intelligent decisions** about which processes to automate with AI.
            
            Instead of guessing, get:
            - 📊 **Data-driven scores** (feasibility, value, risk)
            - 💰 **ROI predictions** (savings, payback, investment)
            - 🎯 **Prioritized recommendations** (what to do first)
            - 📋 **Action plans** (how to implement)
            """)
        
        with col2:
            st.markdown("### 🚀 Quick Start")
            st.success("""
            **3 Simple Steps:**
            
            1️⃣ **Add Processes**
               - Load sample data
               - Upload documents
               - Enter manually
            
            2️⃣ **Analyze**
               - AI scores each process
               - Calculates ROI
               - Identifies risks
            
            3️⃣ **Review Results**
               - See top opportunities
               - Export reports
               - Make decisions
            """)
        
        st.markdown("---")
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📚 Load Sample Data", use_container_width=True):
                db = get_database()
                synthetic_processes = load_synthetic_processes()
                
                # Save all to database
                for process in synthetic_processes:
                    db.save_process(process)
                
                st.session_state.analysis_done = False
                st.success(f"✅ Loaded {len(synthetic_processes)} sample processes!")
                st.rerun()
        
        with col2:
            st.button("➕ Add Process Manually", use_container_width=True, key="goto_manual")
        
        with col3:
            if st.button("📊 View Analysis", use_container_width=True, disabled=len(all_processes) == 0):
                if not st.session_state.analysis_done:
                    analyze_processes(all_processes)
                st.rerun()
    
    # MANAGE PROCESSES PAGE
    elif page == "📁 Manage Processes":
        st.markdown("---")
        
        tab1, tab2, tab3 = st.tabs(["📚 Current Processes", "➕ Add Manually", "📤 Upload File"])
        
        # Tab 1: Current Processes
        with tab1:
            db = get_database()
            all_processes = db.get_all_processes()
            
            if len(all_processes) == 0:
                st.info("No processes yet. Add some using the tabs above or load sample data.")
            else:
                st.subheader(f"📋 {len(all_processes)} Processes")
                
                # Display as table
                df = pd.DataFrame([{
                    'Name': p.name,
                    'Category': p.category,
                    'Annual Volume': f"{p.annual_volume:,}",
                    'Duration (min)': p.duration_minutes,
                    'People': p.people_involved,
                    'Source': p.source or 'unknown'
                } for p in all_processes])
                
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Actions
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🗑️ Clear All Processes"):
                        db = get_database()
                        # Delete all processes
                        for p in all_processes:
                            db.delete_process(p.id)
                        st.session_state.analysis_done = False
                        st.rerun()
                
                with col2:
                    if st.button("🔄 Re-analyze All"):
                        analyze_processes(all_processes)
                        st.rerun()
        
        # Tab 2: Manual Entry
        with tab2:
            new_process = manual_process_form()
            
            if new_process:
                st.session_state.analysis_done = False
                st.success(f"✅ Added process: {new_process.name}")
                st.rerun()
        
        # Tab 3: File Upload
        with tab3:
            st.subheader("📤 Upload Document")
            
            uploaded_file = st.file_uploader(
                "Choose a file (PDF, DOCX, TXT)",
                type=['pdf', 'docx', 'txt'],
                help="Upload process documentation. Text will be extracted for review."
            )
            
            if uploaded_file:
                st.info(f"📄 File: {uploaded_file.name} ({uploaded_file.size} bytes)")
                
                if st.button("💾 Save & Extract Text"):
                    # Save file
                    file_path = save_uploaded_file(uploaded_file)
                    st.success(f"✅ File saved: {file_path}")
                    
                    # Extract text
                    with st.spinner("Extracting text..."):
                        text = extract_text_from_upload(file_path)
                    
                    if text:
                        st.success(f"✅ Extracted {len(text)} characters")
                        
                        # Show preview
                        with st.expander("📝 Preview extracted text"):
                            st.text_area("Content", text[:2000], height=300, disabled=True)
                            if len(text) > 2000:
                                st.info(f"Showing first 2000 of {len(text)} characters")
                        
                        st.warning("""
                        ⚠️ **LLM Processing Not Available**
                        
                        Discovery Agent requires Anthropic API key to automatically extract process information.
                        
                        For now, you can:
                        - Review the extracted text above
                        - Manually enter the process using the "Add Manually" tab
                        """)
                    else:
                        st.error("Failed to extract text from file")
    
    # ANALYSIS DASHBOARD PAGE
    elif page == "📊 Analysis Dashboard":
        st.markdown("---")
        
        db = get_database()
        all_processes = db.get_all_processes()
        
        if len(all_processes) == 0:
            st.warning("No processes to analyze. Go to 'Manage Processes' to add some.")
            return
        
        # Get existing scores or analyze
        scores = db.get_opportunity_scores()
        
        if len(scores) == 0 or not st.session_state.analysis_done:
            scores = analyze_processes(all_processes)
        
        # Metrics
        st.subheader("📊 Portfolio Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_savings = sum(s.estimated_annual_savings for s in scores)
        total_investment = sum(s.implementation_cost for s in scores)
        portfolio_roi = ((total_savings - total_investment) / total_investment * 100) if total_investment > 0 else 0
        strong_count = len([s for s in scores if "STRONG" in s.recommendation])
        
        with col1:
            st.metric("Processes Analyzed", len(scores))
        with col2:
            st.metric("Annual Savings Potential", f"${total_savings:,.0f}")
        with col3:
            st.metric("Total Investment", f"${total_investment:,.0f}")
        with col4:
            st.metric("Portfolio ROI", f"{portfolio_roi:.0f}%")
        
        st.markdown("---")
        
        # Top opportunities
        st.subheader("🎯 Top 10 Opportunities")
        
        top_10 = scores[:10]
        
        for i, score in enumerate(top_10, 1):
            with st.expander(f"**{i}. {score.process_name}** - Score: {score.overall_score:.1f}/100"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Recommendation:** {score.recommendation}")
                    st.markdown(f"**Reasoning:** {score.reasoning}")
                    
                    if score.risk_factors:
                        st.markdown("**Risk Factors:**")
                        for rf in score.risk_factors:
                            st.markdown(f"- {rf}")
                
                with col2:
                    st.metric("Feasibility", f"{score.feasibility_score:.0f}/100")
                    st.metric("Value", f"{score.value_score:.0f}/100")
                    st.metric("Risk", f"{score.risk_score:.0f}/100")
                    st.metric("Annual Savings", f"${score.estimated_annual_savings:,.0f}")
                    st.metric("ROI", f"{score.roi_percentage:.0f}%")
                    st.metric("Payback", f"{score.payback_months:.1f} mo")


if __name__ == "__main__":
    main()