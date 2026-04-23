#!/bin/bash
# DelValue AI — Quick Start for GitHub Codespaces
# Run: bash scripts/start.sh

set -e

echo "=== DelValue AI v2.0 — Starting ==="

# Install dependencies
echo "[1/3] Installing dependencies..."
pip install -q fastapi uvicorn pydantic pydantic-settings sqlalchemy \
    scikit-learn numpy scipy xgboost joblib \
    anthropic httpx tenacity structlog orjson \
    python-multipart email-validator \
    streamlit plotly 2>&1 | tail -1

# Initialize database + seed benchmarks
echo "[2/3] Initializing database..."
python -c "
from data.database import init_db
init_db()
print('Database initialized with benchmark data')
"

# Start API
echo "[3/3] Starting API server..."
echo ""
echo "============================================"
echo "  DelValue AI v2.0"
echo "  API:  http://localhost:8000"
echo "  Docs: http://localhost:8000/docs"
echo "============================================"
echo ""
echo "Open /docs in browser for interactive API demo"
echo "Press Ctrl+C to stop"
echo ""

uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
