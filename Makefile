.PHONY: install dev api ui test lint docker-up docker-down seed clean

install:
	pip install -r requirements.txt

dev:
	@echo "Starting API + UI..."
	uvicorn api.main:app --reload --port 8000 &
	streamlit run ui/app.py --server.port 8501

api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

ui:
	streamlit run ui/app.py --server.port 8501

test:
	python -m pytest tests/ -v --tb=short

test-coverage:
	python -m pytest tests/ -v --cov=core --cov=api --cov=data --cov-report=term-missing

lint:
	ruff check .
	mypy core/ api/ data/ --ignore-missing-imports

seed:
	python -c "from data.database import init_db; init_db(); from data.seeds.benchmarks import seed_benchmarks; from sqlalchemy.orm import Session; from data.database import engine; s=Session(engine); print(f'Seeded {seed_benchmarks(s)} benchmarks')"

docker-up:
	docker compose -f docker/docker-compose.yml up --build -d

docker-down:
	docker compose -f docker/docker-compose.yml down

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage
