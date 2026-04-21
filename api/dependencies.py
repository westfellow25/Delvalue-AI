"""
DelValue AI — FastAPI Dependencies

Shared dependencies: engines, agents, repositories.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from api.config import get_settings
from data.database import get_db
from core.engines.benchmark import BenchmarkEngine
from core.engines.discovery import ProcessMiningEngine
from core.engines.nlp import NLPEngine
from core.engines.scoring import ScoringEngine
from core.engines.simulation import MonteCarloEngine
from core.ml.models import HeuristicScoringModel, MLScoringModel
from core.agents.analyst import AnalystAgent
from core.agents.advisor import AdvisorAgent
from core.agents.monitor import MonitorAgent
from core.agents.orchestrator import AgentOrchestrator
from data.repositories.process_repository import (
    ProcessRepository,
    ScoreRepository,
    TraceRepository,
)

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache
def _get_llm_client():
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=settings.anthropic_api_key)
    except ImportError:
        logger.warning("anthropic package not installed")
        return None


@lru_cache
def _get_ml_model() -> Optional[MLScoringModel]:
    """Load persisted ML model if available."""
    try:
        model = MLScoringModel(model_dir=settings.ml_model_dir)
        model.load()
        return model
    except Exception as e:
        logger.info(f"ML model not loaded (cold start): {e}")
        return None


def get_scoring_engine() -> ScoringEngine:
    return ScoringEngine(
        ml_model=_get_ml_model(),
        heuristic_model=HeuristicScoringModel(),
        simulation_engine=MonteCarloEngine(),
    )


def get_benchmark_engine(db: Session = Depends(get_db)) -> BenchmarkEngine:
    return BenchmarkEngine(session=db)


def get_discovery_engine(db: Session = Depends(get_db)) -> ProcessMiningEngine:
    return ProcessMiningEngine(session=db)


def get_nlp_engine() -> NLPEngine:
    return NLPEngine(llm_client=_get_llm_client(), default_model=settings.default_model)


def get_analyst_agent(
    scoring_engine: ScoringEngine = Depends(get_scoring_engine),
    benchmark_engine: BenchmarkEngine = Depends(get_benchmark_engine),
) -> AnalystAgent:
    return AnalystAgent(
        scoring_engine=scoring_engine,
        benchmark_engine=benchmark_engine,
        llm_client=_get_llm_client(),
        default_model=settings.default_model,
    )


def get_advisor_agent() -> AdvisorAgent:
    return AdvisorAgent(
        llm_client=_get_llm_client(),
        default_model=settings.default_model,
    )


def get_monitor_agent(db: Session = Depends(get_db)) -> MonitorAgent:
    # The monitor receives the repository later per-request
    return MonitorAgent(trace_repository=None)


def get_orchestrator(
    scoring_engine: ScoringEngine = Depends(get_scoring_engine),
    benchmark_engine: BenchmarkEngine = Depends(get_benchmark_engine),
    analyst_agent: AnalystAgent = Depends(get_analyst_agent),
    advisor_agent: AdvisorAgent = Depends(get_advisor_agent),
    monitor_agent: MonitorAgent = Depends(get_monitor_agent),
    discovery_engine: ProcessMiningEngine = Depends(get_discovery_engine),
    nlp_engine: NLPEngine = Depends(get_nlp_engine),
) -> AgentOrchestrator:
    return AgentOrchestrator(
        scoring_engine=scoring_engine,
        benchmark_engine=benchmark_engine,
        analyst_agent=analyst_agent,
        advisor_agent=advisor_agent,
        monitor_agent=monitor_agent,
        discovery_engine=discovery_engine,
        nlp_engine=nlp_engine,
    )
