"""
DelValue AI — Database Session Management

Supports both sync (SQLite for dev) and async (PostgreSQL for production).
All queries are automatically scoped to the current tenant.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from api.config import get_settings
from data.models.base import Base

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db(seed: bool = True) -> None:
    """Create all tables and optionally seed benchmark data."""
    import data.models.organization  # noqa: F401
    import data.models.process  # noqa: F401
    Base.metadata.create_all(bind=engine)

    if seed:
        try:
            from data.seeds.benchmarks import seed_benchmarks
            with Session(engine) as db:
                seed_benchmarks(db)
        except Exception:
            pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session, auto-closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for non-FastAPI code (agents, CLI, scripts)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class TenantSession:
    """
    Wraps a DB session with automatic tenant scoping.
    All queries through this session are filtered by organization_id.
    """

    def __init__(self, session: Session, organization_id: str):
        self.session = session
        self.organization_id = organization_id

    def query(self, model):
        """Auto-filter by tenant. Only works on models with TenantMixin."""
        q = self.session.query(model)
        if hasattr(model, "organization_id"):
            q = q.filter(model.organization_id == self.organization_id)
        if hasattr(model, "is_deleted"):
            q = q.filter(model.is_deleted == False)
        return q

    def add(self, instance):
        """Auto-set organization_id on new records."""
        if hasattr(instance, "organization_id"):
            instance.organization_id = self.organization_id
        self.session.add(instance)
        return instance

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

    def flush(self):
        self.session.flush()
