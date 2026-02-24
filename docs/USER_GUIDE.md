# User Guide

Complete guide for using DelValue AI to make intelligent automation decisions.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Adding Processes](#adding-processes)
3. [Analyzing Opportunities](#analyzing-opportunities)
4. [Understanding Results](#understanding-results)
5. [Making Decisions](#making-decisions)
6. [Best Practices](#best-practices)

---

## Getting Started

### First Launch

1. **Start the application**
```bash
   streamlit run app.py
```

2. **Navigate to Process Library**
   - Click "Process Library" in sidebar

3. **Load sample data**
   - Click "📚 Load Sample Data"
   - Review 15 pre-loaded processes

### Understanding the Interface

**Sidebar Navigation:**
- 🏠 **app (Home):** Overview and quick actions
- 📊 **Dashboard:** Portfolio analytics
- 📁 **Process Library:** Manage processes
- 🎯 **Opportunities:** Ranked recommendations
- 📈 **Monitoring:** Track implementations
- 📋 **Reports:** Strategic reports

---

## Adding Processes

### Method 1: Load Sample Data

**When to use:** Learning the platform, testing

**Steps:**
1. Go to Process Library
2. Click "📚 Load Sample Data"
3. 15 sample processes loaded instantly

### Method 2: Manual Entry

**When to use:** Entering known processes

**Steps:**
1. Go to Process Library → "Add Process" tab
2. Fill in required fields:
   - **Name:** Clear, descriptive name
   - **Description:** Detailed explanation (50+ chars)
   - **Category:** Select from dropdown
   - **Annual Volume:** How many times per year
   - **Duration:** Minutes per execution
   - **People Involved:** Number of people
   - **Hourly Cost:** Blended hourly rate

3. Optional fields:
   - Systems Used
   - Pain Points
   - Stakeholders

4. Click "Add"

**Example:**
```
Name: Invoice Processing
Description: Manual review and approval of vendor invoices including data entry, validation, approval routing, and payment scheduling
Category: Finance
Annual Volume: 50,000
Duration: 15 minutes
People: 5
Hourly Cost: $45
```

### Method 3: Upload Documents

**When to use:** Extracting from SOPs, documentation

**Status:** ⚠️ Requires Anthropic API key

**Steps:**
1. Set up API key in `.env`
2. Go to Process Library → "Upload File" tab
3. Upload PDF, DOCX, or TXT
4. Discovery Agent extracts process info
5. Review and save

---

## Analyzing Opportunities

### Running Analysis

1. Go to Process Library
2. Click "🔄 Re-analyze All"
3. Wait for analysis to complete (~2-5 seconds)
4. View results in Dashboard or Opportunities

### What Analysis Does

**For each process, calculates:**

1. **Feasibility Score (0-100)**
   - Process repetitiveness
   - Documentation quality
   - System complexity

2. **Value Score (0-100)**
   - Annual cost savings
   - Number of people impacted
   - Pain points addressed

3. **Risk Score (0-100)** (lower is better)
   - Integration complexity
   - Change management needs
   - Compliance requirements

4. **Overall Score (0-100)**
   - Weighted combination
   - Default weights: Value 50%, Feasibility 30%, Risk 20%

5. **Financial Metrics**
   - Estimated annual savings
   - Implementation cost
   - ROI percentage
   - Payback period (months)

---

## Understanding Results

### Dashboard

**Key Metrics:**
- Total processes analyzed
- Annual savings potential
- Total investment required
- Portfolio ROI

**Charts:**
- Top 10 by score (bar chart)
- Savings vs Investment (grouped bar)
- Category distribution (pie chart)
- Savings by category (bar chart)

### Opportunities Page

**For each opportunity, shows:**

- Overall score
- Recommendation (STRONG RECOMMEND, RECOMMEND, CONSIDER, DEPRIORITIZE)
- Component scores (Feasibility, Value, Risk)
- Financial metrics
- Reasoning (why this score)
- Risk factors

**Example Output:**
```
Invoice Processing - Score: 84.5/100

Recommendation: STRONG RECOMMEND

Scores:
- Feasibility: 75/100
- Value: 100/100
- Risk: 40/100

Financials:
- Annual Savings: $393,750
- Investment: $24,000
- ROI: 1541%
- Payback: 0.7 months

Reasoning: High-value opportunity with 1541% ROI. Feasibility: 75/100, Value: 100/100. Payback in 0.7 months.

Risk Factors:
- Moderate integration complexity (3 systems)
- High regulatory/compliance risk (finance)
```

### Interpreting Recommendations

**STRONG RECOMMEND**
- Overall score ≥75
- ROI ≥150%
- Action: Implement immediately

**RECOMMEND**
- Overall score ≥60
- ROI ≥100%
- Action: Plan for next quarter

**CONSIDER**
- Overall score ≥45
- Action: Re-evaluate after higher priorities

**DEPRIORITIZE**
- Overall score <45
- Action: Focus on other opportunities first

---

## Making Decisions

### Decision Framework

1. **Review Top 5 Opportunities**
   - Sort by overall score
   - Check ROI and payback

2. **Consider Constraints**
   - Budget available
   - Team capacity
   - Strategic priorities

3. **Assess Risks**
   - Review risk factors
   - Plan mitigation strategies

4. **Plan Implementation**
   - Start with highest ROI
   - Group similar processes
   - Phase approach

### Example Decision Process

**Scenario:** $100k budget, 6-month timeline

**Analysis:**
- Top 5 opportunities identified
- Total investment: $99k
- Total savings: $1.26M/year
- Portfolio ROI: 1177%

**Decision:**
- **Month 1-2:** Implement #1 and #2 (payback <1 month)
- **Month 3-4:** Implement #3 (moderate complexity)
- **Month 5-6:** Implement #4 and #5

**Expected Outcome:**
- Year 1 net benefit: $1.16M
- All projects paid back within 6 months

---

## Best Practices

### Data Quality

✅ **DO:**
- Provide detailed descriptions (100+ words)
- Include accurate volume estimates
- List all systems used
- Document pain points
- Get input from process owners

❌ **DON'T:**
- Use vague descriptions
- Guess at numbers
- Omit important context
- Skip stakeholder input

### Analysis Accuracy

**To improve accuracy:**
1. Update processes regularly
2. Track actual outcomes
3. Refine estimates based on results
4. Document assumptions

### Decision Making

**Key principles:**
1. **Start with quick wins:** High ROI, low complexity
2. **Build momentum:** Early successes fund later projects
3. **Manage change:** Include people in the process
4. **Measure results:** Track predicted vs actual
5. **Iterate:** Learn and improve

### Common Mistakes

❌ **Mistake:** Implementing too many projects at once
✅ **Fix:** Start with top 3, then expand

❌ **Mistake:** Ignoring risk factors
✅ **Fix:** Plan mitigation for each identified risk

❌ **Mistake:** Not tracking outcomes
✅ **Fix:** Use Monitoring page to record actuals

❌ **Mistake:** Over-optimistic estimates
✅ **Fix:** Use conservative assumptions, add buffers

---

## FAQ

**Q: How accurate are the predictions?**
A: Initial accuracy ~70-80%. Improves with feedback loop (tracking actuals).

**Q: Can I change the scoring weights?**
A: Yes, modify `DecisionEngine()` initialization in code.

**Q: How do I export results?**
A: Coming in v1.1. Currently, take screenshots or copy data.

**Q: Can multiple users access this?**
A: v1.0 is single-user. Multi-user coming in v2.0.

**Q: What if I don't have an API key?**
A: Most features work without it. Only Discovery Agent requires API key.

---

## Getting Help

- **Documentation:** `/docs` folder
- **GitHub Issues:** Report bugs or request features
- **Email:** support@delvalue.ai (example)

---

**Happy automating! 🤖**
