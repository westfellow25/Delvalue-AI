"""
DelValue AI — Application Configuration

Centralized settings with environment variable overrides.
Multi-environment support (dev/staging/production).
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    # --- Application ---
    app_name: str = "DelValue AI"
    app_version: str = "2.0.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    secret_key: str = Field(default="change-me-in-production-use-openssl-rand-hex-32")
    base_dir: Path = BASE_DIR

    # --- Database ---
    database_url: str = Field(
        default=f"sqlite:///{BASE_DIR / 'data' / 'delvalue.db'}",
        description="SQLAlchemy database URL. Use postgresql:// in production.",
    )
    db_echo: bool = False
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # --- Auth ---
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    api_key_prefix: str = "dvai_"

    # --- AI / LLM ---
    anthropic_api_key: str = ""
    default_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    llm_temperature: float = 0.3
    llm_timeout: int = 60
    llm_max_retries: int = 3

    # --- ML Engine ---
    ml_model_dir: Path = Field(default_factory=lambda: BASE_DIR / "data" / "ml_models")
    scoring_model_version: str = "v1"
    min_training_samples: int = 50
    retrain_threshold: float = 0.05  # retrain when calibration drift > 5%

    # --- Simulation ---
    monte_carlo_iterations: int = 10_000
    simulation_confidence_levels: list[float] = [0.10, 0.25, 0.50, 0.75, 0.90]

    # --- Benchmarking ---
    benchmark_anonymization_threshold: int = 5  # min companies per bucket
    benchmark_refresh_interval_hours: int = 24

    # --- Rate Limiting ---
    rate_limit_requests_per_minute: int = 60
    rate_limit_analysis_per_hour: int = 100

    # --- Telemetry ---
    enable_telemetry: bool = True
    log_level: str = "INFO"

    # --- Multi-tenant ---
    max_organizations: int = 1000
    max_users_per_org: int = 500
    max_processes_per_org: int = 50_000

    @field_validator("secret_key")
    @classmethod
    def warn_default_secret(cls, v: str) -> str:
        if v == "change-me-in-production-use-openssl-rand-hex-32":
            import warnings
            warnings.warn(
                "Using default secret key — set SECRET_KEY env var in production",
                stacklevel=2,
            )
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
