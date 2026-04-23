"""About — product vision, AI capabilities, competitive advantage."""

from __future__ import annotations

import streamlit as st


def render():
    st.title("DelValue AI")
    st.markdown("### AI-Powered Decision Intelligence for Automation Investments")

    st.markdown("""
---

## The Problem

Every Fortune 500 company has **hundreds of repetitive business processes**: invoice processing,
employee onboarding, IT ticket triage, procurement, compliance reporting.

The question every CFO and COO faces:

> **"Which processes should we automate first — and how do we avoid wasting millions on the wrong ones?"**

Today this is solved by **management consultants: $500K+ and 6 months** for a one-time report
based on interviews and opinions. No data. No calibration. No learning.

---

## Our Solution

DelValue AI replaces 6 months of consulting with **30 seconds of AI-powered analysis.**

""")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Analysis Time", "30 sec", delta="-6 months vs consultants")
    col2.metric("Factors Analyzed", "28", delta="+24 vs human judgment")
    col3.metric("Industry Benchmarks", "132", delta="12 categories x 10 industries")
    col4.metric("Simulation Iterations", "10,000+", delta="per process")

    st.markdown("""
---

## What Makes This AI — Not Just a Spreadsheet

### 1. ML Scoring Engine (28-factor model)
A human analyst considers 3-4 factors. Our model evaluates **28 simultaneously**:
volume, complexity, number of systems, decision points, error rates, documentation quality,
stakeholder count, data structure, judgment requirements — and produces a calibrated score.

When enough outcome data accumulates (50+ implementations), the model **automatically retrains**
using gradient-boosted trees on real predicted-vs-actual data.

### 2. Monte Carlo Simulation (uncertainty quantification)
We don't say _"ROI will be 150%"_. We say:
- **92% probability** of positive ROI
- **22% probability** ROI exceeds 100%
- **In the worst 5% of scenarios**, maximum loss is 8%
- **NPV over 3 years**: $76K with full confidence intervals

This is **Goldman Sachs-level risk modeling** applied to automation investments.

### 3. Learning Loop (the moat)
Every customer records actual outcomes after implementation. The model compares
its predictions with reality and **recalibrates**. More customers = more accurate model for everyone.

**This is a network effect — like Waze for navigation.** A competitor cannot replicate this
without the outcomes database. It compounds over time.

### 4. Process Mining (zero manual work)
Upload event logs from SAP, Salesforce, or ServiceNow — the AI **automatically discovers
processes**, finds bottlenecks, identifies variants, and ranks automation candidates.
No interviews. No consultants. No 6-month discovery phase.

---

## The Competitive Landscape

""")

    comp_data = {
        "Capability": [
            "Process Discovery",
            "Automation Scoring",
            "Monte Carlo Simulation",
            "Industry Benchmarks",
            "ML Learning Loop",
            "Decision Intelligence",
            "Portfolio Optimization",
        ],
        "McKinsey / Consultants": ["Manual (6mo)", "Opinion-based", "No", "Limited", "No", "No", "No"],
        "Celonis": ["Yes", "No", "No", "No", "No", "No", "No"],
        "UiPath / AA": ["Partial", "Basic", "No", "No", "No", "No", "No"],
        "DelValue AI": ["Automated", "ML (28 factors)", "10K iterations", "132 benchmarks", "Yes (retrains)", "Yes (core)", "Budget-constrained"],
    }
    import pandas as pd
    df = pd.DataFrame(comp_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("""
---

## Unit Economics

| Metric | Value |
|--------|-------|
| **TAM** | $15B (automation consulting + process mining) |
| **Target ACV** | $50K-200K / year per enterprise |
| **Replacement cost** | $500K-2M in consulting fees |
| **Time to value** | 30 seconds (first analysis) to 1 day (full portfolio) |
| **Gross margin** | 85%+ (SaaS, no consultants needed) |
| **Moat** | Data flywheel — each customer's outcomes improve the model for everyone |

---

## How to Use This Demo

1. **Process Library** — Browse or add business processes
2. **Analyze Process** — Deep analysis with ML scoring, Monte Carlo, and benchmarks
3. **Portfolio** — Optimize which processes to automate under a budget constraint
4. **Simulation Lab** — Interactive Monte Carlo with parameter sliders
5. **Process Mining** — Upload event logs, discover processes automatically
6. **Benchmarks** — Compare against 132 industry benchmarks
7. **Monitoring** — Track prediction accuracy as outcomes are recorded

""")
