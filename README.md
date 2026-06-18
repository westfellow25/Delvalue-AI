# DelValue AI

**Decision intelligence for transformation — which processes are actually worth automating with AI.**

> Cursor for AI value discovery: point it at a company's processes, get a ranked, ROI-scored automation backlog.

Every company wants to "use AI." Few know *where*. DelValue ingests a company's processes, scores each one on feasibility, business value, risk, ROI, and payback, and returns a prioritized backlog — so transformation leads and CTOs spend their budget on the workflows that pay, not the ones that demo well.

---

## The problem

The bottleneck in enterprise AI isn't models — it's deciding what to automate. Teams pick projects by hype, burn quarters on low-value pilots, and can't defend the roadmap to finance. There's no rigorous, repeatable way to go from "here are our processes" to "here's the value-ranked plan."

DelValue is that scoring layer.

---

## What you do with it

| Step | Example |
| --- | --- |
| 01 — Ingest | Drop in process docs (PDF / DOCX / TXT) or describe workflows. |
| 02 — Discover | The Discovery agent extracts structured processes from unstructured input. |
| 03 — Score | Each process is scored on feasibility, value, risk, ROI, and payback. |
| 04 — Decide | Get a ranked backlog + recommendations; track predicted vs. actual over time. |

---

## DelValue is for you if

- ✅ You're a CTO, transformation lead, or AI consultant deciding where to start
- ✅ You have a long list of "AI ideas" and no rigorous way to prioritize them
- ✅ You need an ROI/payback case finance will accept
- ✅ You want the roadmap to learn from what actually shipped

---

## Features

🔎 **Value Discovery Agent** — Parses PDF / DOCX / TXT via Claude and turns unstructured processes into structured, typed models.

🧮 **Multi-Factor Decision Engine** — Scores each process on feasibility, business value, risk, ROI, and payback period.

🤖 **Four-Agent Pipeline** — Analysis, Discovery, Monitoring, and Recommendation agents plus a judgment layer.

📈 **Ranked Backlog** — A prioritized, defensible list of what to automate first.

🔁 **Learning Loop** — Stores predictions and compares them to actual outcomes to improve future scoring.

🌐 **API + UI** — Streamlit app for exploration and an `api_server.py` for programmatic access.

🧪 **Tested** — 17 passing pytest cases lock the scoring logic.

---

## What's under the hood

```
┌───────────────────────────────────────────────────────────┐
│                       DELVALUE AI                          │
│                                                            │
│  Discovery Agent  ──►  structured processes (Pydantic)     │
│        │                                                   │
│        ▼                                                   │
│  Decision Engine  ──►  feasibility · value · risk          │
│        │                ROI · payback                      │
│        ▼                                                   │
│  Recommendation   ──►  ranked automation backlog           │
│        │                                                   │
│        ▼                                                   │
│  Monitoring  ◄──────►  predicted vs. actual (learning loop)│
│                                                            │
│  Persistence: SQLite        UI: Streamlit + Plotly         │
└───────────────────────────────────────────────────────────┘
```

**Discovery Agent** — document ingestion (PDF/DOCX/TXT) → Claude extraction → validated Pydantic models.

**Decision Engine** — multi-factor scoring that combines feasibility, value, risk into an opportunity score, with ROI and payback.

**Recommendation + Judgment** — turns scores into a ranked, explained backlog.

**Monitoring** — records predictions, ingests outcomes, and feeds the learning loop.

---

## Tech stack

- **Language:** Python
- **AI:** Anthropic Claude SDK
- **Modeling:** Pydantic
- **Storage:** SQLite
- **API:** FastAPI-style `api_server.py`
- **UI:** Streamlit + Plotly
- **Testing:** pytest (17 cases)

---

## Quickstart

```bash
git clone https://github.com/westfellow25/delvalue-ai.git
cd delvalue-ai
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY

# UI
streamlit run app.py
# or API
python api_server.py
```

Run the tests:

```bash
pytest -v
```

---

## What DelValue is not

- **Not a generic AI ideas list.** It scores *your* processes with ROI and risk.
- **Not a one-shot report.** It tracks predictions against outcomes and learns.
- **Not an automation tool.** It tells you what's worth automating — you build it (or use PRAXIS to deploy it).

---

## Roadmap

- [x] Four-agent pipeline (Analysis / Discovery / Monitoring / Recommendation)
- [x] Multi-factor decision engine (feasibility / value / risk / ROI / payback)
- [x] Document ingestion (PDF/DOCX/TXT) → structured models
- [x] SQLite persistence + predicted-vs-actual learning loop
- [x] API server
- [ ] Connectors (Jira / Linear / process-mining imports)
- [ ] Portfolio view across departments
- [ ] Hand-off to PRAXIS for deployment

---

Built by [@westfellow25](https://github.com/westfellow25).
