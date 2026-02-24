# 🤖 DelValue AI

**AI-Powered Decision Intelligence for Transformation**

DelValue AI helps companies make intelligent decisions about which business processes to automate with AI and automation.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-17%20passed-success)](tests/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🎯 What is DelValue AI?

DelValue AI is an intelligent decision platform that:

- 📊 **Analyzes processes** - Evaluates feasibility, value, and risk
- 💰 **Predicts ROI** - Calculates savings, investment, and payback
- 🎯 **Prioritizes opportunities** - Ranks processes by overall score
- 📈 **Tracks implementations** - Monitors predicted vs actual outcomes
- 📋 **Generates reports** - Creates quarterly reviews and action plans

---

## ✨ Key Features

### 🧠 4 AI Agents

1. **Analysis Agent** - Portfolio analysis and scoring
2. **Discovery Agent** - Document parsing and process extraction (requires API key)
3. **Monitoring Agent** - Implementation tracking and variance analysis
4. **Recommendation Agent** - Proactive opportunity discovery

### 📊 Decision Engine

- Multi-factor scoring (feasibility, value, risk)
- ROI calculation and financial modeling
- Risk assessment and mitigation strategies
- Portfolio optimization

### 💾 Data Persistence

- SQLite database for process and score storage
- Decision trace tracking for learning loop
- Historical data analysis

### 🖥️ Multi-Page Web Interface

- Home dashboard with quick stats
- Process library for management
- Portfolio analytics with charts
- Opportunities ranking
- Monitoring and reports

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- pip
- virtualenv (recommended)

### Installation
```bash
mkdir -p docs

cat > docs/ARCHITECTURE.md << 'EOF'
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
│                                                               │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐  │
│  │   SQLite    │    │ Pydantic     │    │  File System   │  │
│  │   Database  │    │ Models       │    │  (uploads)     │  │
│  └─────────────┘    └──────────────┘    └────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Decision Engine

**Purpose:** Core scoring and ranking logic

**Responsibilities:**
- Calculate feasibility scores (0-100)
- Calculate value scores (0-100)
- Calculate risk scores (0-100)
- Compute ROI metrics
- Rank opportunities

**Key Methods:**
- `calculate_feasibility_score()`: Process complexity, volume, documentation
- `calculate_value_score()`: Annual cost, scale, pain points
- `calculate_risk_score()`: Integration, change management, compliance
- `calculate_roi()`: Savings, cost, payback
- `score_opportunity()`: Combined scoring
- `rank_opportunities()`: Portfolio prioritization

### 2. AI Agents

#### Analysis Agent

**Purpose:** Portfolio analysis with LLM reasoning

**Capabilities:**
- Analyze individual processes
- Generate LLM-enhanced recommendations
- Portfolio-level analysis
- Executive summaries

**Dependencies:**
- Decision Engine (for quantitative scores)
- Anthropic Claude API (for qualitative reasoning)

#### Discovery Agent

**Purpose:** Extract processes from documents

**Capabilities:**
- Parse PDF, DOCX, TXT files
- LLM-powered process extraction
- Convert unstructured → structured data

**Status:** ⚠️ Requires API key

#### Monitoring Agent

**Purpose:** Track implementation outcomes

**Capabilities:**
- Record actual vs predicted results
- Calculate variance
- Generate alerts
- Learning loop

#### Recommendation Agent

**Purpose:** Proactive opportunity discovery

**Capabilities:**
- Scan for new opportunities
- Detect process changes
- Generate quarterly reports
- Strategic suggestions

### 3. Data Models

#### Process
```python
{
    "id": "uuid",
    "name": "string",
    "description": "string",
    "category": "enum",
    "frequency": "string",
    "duration_minutes": float,
    "annual_volume": int,
    "people_involved": int,
    "hourly_cost": float,
    "systems_used": ["string"],
    "pain_points": ["string"],
    "stakeholders": ["string"]
}
```

#### OpportunityScore
```python
{
    "process_id": "uuid",
    "feasibility_score": float,
    "value_score": float,
    "risk_score": float,
    "overall_score": float,
    "estimated_annual_savings": float,
    "implementation_cost": float,
    "roi_percentage": float,
    "payback_months": float,
    "recommendation": "string",
    "reasoning": "string"
}
```

#### DecisionTrace
```python
{
    "trace_id": "uuid",
    "process_id": "uuid",
    "decision": "GO|NO-GO|DEFER",
    "predicted_roi": float,
    "actual_roi": float,
    "variance_roi": float
}
```

### 4. Database Layer

**Technology:** SQLite

**Tables:**
- `processes`: Process definitions
- `opportunity_scores`: Analysis results
- `decision_traces`: Implementation tracking

**Operations:**
- CRUD for all entities
- Query optimization
- Transaction management

### 5. Web Interface

**Framework:** Streamlit

**Pages:**
- Home: Overview and quick actions
- Dashboard: Portfolio analytics
- Process Library: CRUD operations
- Opportunities: Ranked recommendations
- Monitoring: Implementation tracking
- Reports: Strategic outputs

## Data Flow

### 1. Process Addition Flow
```
User Input → Process Model → Database.save_process() → Confirmation
```

### 2. Analysis Flow
```
Database.get_all_processes()
    ↓
DecisionEngine.score_opportunity() (for each)
    ↓
AnalysisAgent.analyze_process() (LLM enhancement)
    ↓
Database.save_opportunity_score()
    ↓
Display in UI
```

### 3. Monitoring Flow
```
User records actuals
    ↓
DecisionTrace.calculate_variance()
    ↓
MonitoringAgent.check_for_alerts()
    ↓
Database.save_decision_trace()
    ↓
Learning loop update
```

## Scaling Considerations

### Current Limitations (v1.0)

- Single-user (no authentication)
- Local SQLite database
- No horizontal scaling
- Synchronous processing

### Future Scaling Path (v2.0+)

- Multi-user with auth
- PostgreSQL or cloud database
- Async processing
- API endpoints
- Microservices architecture

## Security

### Current Implementation

- Local SQLite (file-based)
- No authentication
- API keys in `.env` file (not committed)

### Production Recommendations

- Add user authentication
- Encrypt sensitive data
- Use environment variables for secrets
- Implement role-based access control
- Add rate limiting

## Performance

### Current Performance

- Single process analysis: <100ms
- Portfolio analysis (15 processes): <2s
- Database queries: <50ms
- UI rendering: <1s

### Optimization Opportunities

- Cache analysis results
- Batch processing
- Async LLM calls
- Database indexing
- Query optimization

## Dependencies

### Core

- Python 3.12+
- Streamlit 1.30+
- Pydantic 2.0+
- SQLite (built-in)

### AI/ML

- Anthropic SDK (optional)
- Pandas, NumPy

### Visualization

- Plotly

### Testing

- Pytest

## Development Workflow

1. Create feature branch
2. Write tests first (TDD)
3. Implement feature
4. Run tests (`pytest tests/ -v`)
5. Update docs
6. Create PR

## Deployment

### Local Development
```bash
streamlit run app.py
```

### Production (Streamlit Cloud)

1. Push to GitHub
2. Connect to Streamlit Cloud
3. Configure secrets
4. Deploy

See [DEPLOYMENT.md](DEPLOYMENT.md) for details.
