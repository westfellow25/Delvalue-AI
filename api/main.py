"""
DelValue AI — FastAPI Application

Enterprise API for automation decision intelligence.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import get_settings
from api.schemas.common import HealthResponse
from data.database import engine, init_db
from data.models.base import Base

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup + shutdown."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version} in {settings.environment}")

    # Ensure schema exists
    init_db()

    # Seed benchmarks if empty
    try:
        from sqlalchemy.orm import Session
        from data.seeds.benchmarks import seed_benchmarks
        from data.models.process import BenchmarkEntry
        with Session(engine) as db:
            if db.query(BenchmarkEntry).count() == 0:
                count = seed_benchmarks(db)
                logger.info(f"Seeded {count} benchmark entries")
    except Exception as e:
        logger.warning(f"Benchmark seeding skipped: {e}")

    yield

    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "DelValue AI — Enterprise decision intelligence for automation investments. "
        "ML-powered scoring, Monte Carlo simulation, industry benchmarking, and "
        "process mining in a single unified API."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health():
    ml_loaded = False
    try:
        from api.dependencies import _get_ml_model
        ml_loaded = _get_ml_model() is not None
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.environment.value,
        database="connected",
        ml_model_loaded=ml_loaded,
    )


# Mount routes
from api.routes import auth, benchmarks, discovery, monitoring, processes  # noqa: E402

app.include_router(auth.router, prefix="/api/v1")
app.include_router(processes.router, prefix="/api/v1")
app.include_router(benchmarks.router, prefix="/api/v1")
app.include_router(discovery.router, prefix="/api/v1")
app.include_router(monitoring.router, prefix="/api/v1")


@app.get("/", tags=["system"])
def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
