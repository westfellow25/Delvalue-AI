"""
DelValue AI — Auth Middleware & Dependencies

JWT and API key authentication with tenant-aware context.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from data.database import get_db
from data.models.organization import APIKey, User, UserRole
from infrastructure.security import decode_token, verify_api_key

security = HTTPBearer(auto_error=False)


class AuthContext:
    """Current authenticated user + tenant context."""

    def __init__(
        self,
        user: Optional[User] = None,
        organization_id: str = "",
        role: UserRole = UserRole.VIEWER,
        api_key_id: Optional[str] = None,
    ):
        self.user = user
        self.organization_id = organization_id
        self.role = role
        self.api_key_id = api_key_id

    @property
    def is_authenticated(self) -> bool:
        return bool(self.organization_id)


async def get_current_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> AuthContext:
    """
    Extract auth context from Bearer token (JWT) or API key.
    Raises 401 if invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Try API key first (starts with configured prefix)
    from api.config import get_settings
    settings = get_settings()
    if token.startswith(settings.api_key_prefix):
        return await _authenticate_api_key(token, db)

    # Otherwise treat as JWT
    return await _authenticate_jwt(token, db)


async def _authenticate_jwt(token: str, db: Session) -> AuthContext:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    org_id = payload.get("org")
    role = payload.get("role", "viewer")

    if not user_id or not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return AuthContext(
        user=user,
        organization_id=org_id,
        role=UserRole(role),
    )


async def _authenticate_api_key(key: str, db: Session) -> AuthContext:
    prefix = key[:12]
    candidates = (
        db.query(APIKey)
        .filter(APIKey.key_prefix == prefix, APIKey.is_active == True)
        .all()
    )
    for api_key in candidates:
        if verify_api_key(key, api_key.key_hash):
            # Check expiry
            if api_key.expires_at:
                from datetime import datetime, timezone
                if api_key.expires_at < datetime.now(timezone.utc):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="API key expired",
                    )
            # Determine role from scopes
            scopes = (api_key.scopes or "read").split(",")
            role = UserRole.ADMIN if "admin" in scopes else UserRole.ANALYST if "write" in scopes else UserRole.API_ONLY
            return AuthContext(
                organization_id=api_key.organization_id,
                role=role,
                api_key_id=api_key.id,
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


def require_role(*allowed_roles: UserRole):
    """Dependency factory for role-based access control."""

    def _check(ctx: AuthContext = Depends(get_current_context)) -> AuthContext:
        if ctx.role not in allowed_roles and ctx.role != UserRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {[r.value for r in allowed_roles]}",
            )
        return ctx

    return _check


def require_admin():
    return require_role(UserRole.ADMIN, UserRole.OWNER)


def require_analyst():
    return require_role(UserRole.ANALYST, UserRole.ADMIN, UserRole.OWNER)
