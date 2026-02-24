# Architecture Documentation

## System Overview

DelValue AI is a decision intelligence platform built with a modular, agent-based architecture.

## High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web UI                         │
│  (Multi-page app: Home, Dashboard, Library, Opportunities)  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                     Application Layer                        │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Analysis    │  │  Discovery   │  │  Monitoring  │      │
│  │  Agent       │  │  Agent       │  │  Agent       │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │              │
│         └─────────────────┴──────────────────┘              │
│                           │                                 │
│                  ┌────────┴────────┐                        │
│                  │ Decision Engine │                        │
│                  └────────┬────────┘                        │
└───────────────────────────┼──────────────────────────────────┘
                            │
┌───────────────────────────┴──────────────────────────────────┐
│                      Data Layer                               │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐  │
│  │   SQLite    │    │  Pydantic    │    │  File System   │  │
│  │   Database  │    │  Models      │    │  (uploads)     │  │
│  └─────────────┘    └──────────────┘    └────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Decision Engine
- Scoring algorithms (feasibility, value, risk)
- ROI calculation
- Ranking and prioritization

### 2. AI Agents
- **Analysis Agent:** Portfolio analysis with LLM reasoning
- **Discovery Agent:** Document parsing and extraction
- **Monitoring Agent:** Implementation tracking
- **Recommendation Agent:** Proactive opportunity discovery

### 3. Data Models
- Process
- OpportunityScore
- DecisionTrace

### 4. Database Layer
- SQLite for persistence
- CRUD operations
- Query optimization

### 5. Web Interface
- Multi-page Streamlit app
- Interactive visualizations
- Real-time updates

## Technology Stack

- **Backend:** Python 3.12+
- **Frontend:** Streamlit
- **Database:** SQLite
- **AI/ML:** Anthropic Claude, Pandas, NumPy
- **Visualization:** Plotly
- **Testing:** Pytest

## Data Flow

### Analysis Flow
```
User Input → Process Model → Database
    ↓
Decision Engine → OpportunityScore
    ↓
Analysis Agent → Enhanced Reasoning
    ↓
Database → UI Display
```

## Security
- Local SQLite database
- API keys in .env (not committed)
- No authentication (single-user v1.0)

## Performance
- Single process analysis: <100ms
- Portfolio (15 processes): <2s
- Database queries: <50ms

## Deployment
- Local: `streamlit run app.py`
- Production: Streamlit Cloud

See README.md for full details.
