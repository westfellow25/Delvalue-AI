"""Shared test fixtures."""

from __future__ import annotations

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Override DB URL before any imports that read config
os.environ["DATABASE_URL"] = "sqlite://"  # in-memory

from data.models.base import Base
from data.models.organization import Organization, User, SubscriptionTier, UserRole
from data.models.process import (
    BenchmarkEntry,
    Process,
    ProcessCategory,
    ProcessFrequency,
    DocumentationQuality,
    DataSource,
)
def hash_password(p: str) -> str:
    return f"hashed:{p}"


@pytest.fixture
def db_engine():
    eng = create_engine("sqlite://", echo=False)
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db(db_engine):
    session = sessionmaker(bind=db_engine)()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def org(db) -> Organization:
    org = Organization(
        name="Test Corp",
        slug="test-corp",
        industry="technology",
        subscription_tier=SubscriptionTier.PROFESSIONAL,
    )
    db.add(org)
    db.flush()
    return org


@pytest.fixture
def user(db, org) -> User:
    u = User(
        organization_id=org.id,
        email="test@testcorp.com",
        hashed_password=hash_password("testpass123"),
        full_name="Test User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


@pytest.fixture
def sample_process(db, org) -> Process:
    p = Process(
        organization_id=org.id,
        name="Invoice Processing",
        description="Process incoming invoices for payment",
        category=ProcessCategory.FINANCE,
        frequency=ProcessFrequency.DAILY,
        duration_minutes=30,
        annual_volume=5000,
        people_involved=3,
        hourly_cost=45.0,
        systems_used='["SAP", "Excel"]',
        pain_points='["manual data entry", "frequent errors"]',
        num_decision_points=3,
        num_exceptions=2,
        requires_judgment=False,
        structured_data_pct=0.7,
        error_rate_pct=5.0,
        documentation_quality=DocumentationQuality.GOOD,
        sop_exists=True,
        source=DataSource.MANUAL,
        created_by="test",
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def sample_process_data() -> dict:
    return {
        "name": "Invoice Processing",
        "description": "Process incoming invoices for payment",
        "category": "finance",
        "frequency": "daily",
        "duration_minutes": 30,
        "annual_volume": 5000,
        "people_involved": 3,
        "hourly_cost": 45.0,
        "systems_used": '["SAP", "Excel"]',
        "pain_points": '["manual data entry", "frequent errors"]',
        "num_decision_points": 3,
        "num_exceptions": 2,
        "requires_judgment": False,
        "structured_data_pct": 0.7,
        "error_rate_pct": 5.0,
        "documentation_quality": "good",
        "sop_exists": True,
    }
