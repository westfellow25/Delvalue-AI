"""
DelValue AI — SQLAlchemy Base & Mixins

Multi-tenant data model with audit trail, soft deletes, and versioning.
Every row is scoped to an organization — this is the foundation of data isolation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    event,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    declared_attr,
)


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class TimestampMixin:
    """Adds created_at / updated_at with automatic updates."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class SoftDeleteMixin:
    """Soft delete support — rows are never physically deleted."""

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    def soft_delete(self, user_id: str) -> None:
        self.is_deleted = True
        self.deleted_at = utcnow()
        self.deleted_by = user_id


class TenantMixin:
    """Multi-tenant isolation — every row belongs to an organization."""

    @declared_attr
    def organization_id(cls) -> Mapped[str]:
        return mapped_column(
            String(36),
            ForeignKey("organizations.id"),
            nullable=False,
            index=True,
        )


class AuditMixin:
    """Tracks who created/modified each row."""

    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class VersionMixin:
    """Optimistic locking via version counter."""

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
