"""
DelValue AI — Audit Logging

Write-only audit trail for compliance (SOC2, ISO 27001).
Logs every mutating operation with user, resource, and context.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from data.models.organization import AuditLog

logger = logging.getLogger(__name__)


def record_audit(
    db: Session,
    organization_id: str,
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """
    Write an audit log entry. Fire-and-forget pattern — failures don't block
    the main operation.
    """
    try:
        entry = AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.exception(f"Failed to record audit log: {e}")
        db.rollback()
