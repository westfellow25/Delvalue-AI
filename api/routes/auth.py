"""Auth routes: signup, login, refresh, API keys."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.config import get_settings
from api.middleware.auth import AuthContext, get_current_context, require_admin
from api.middleware.audit import record_audit
from api.schemas.auth import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyResponse,
    LoginRequest,
    OrganizationResponse,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from data.database import get_db
from data.models.organization import (
    APIKey,
    Organization,
    SubscriptionTier,
    User,
    UserRole,
)
from infrastructure.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """Create a new organization + owner user. Returns tokens."""
    # Check slug availability
    existing = db.query(Organization).filter(Organization.slug == payload.organization_slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Organization slug already taken")

    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    org = Organization(
        name=payload.organization_name,
        slug=payload.organization_slug,
        industry=payload.industry,
        subscription_tier=SubscriptionTier.FREE,
    )
    db.add(org)
    db.flush()

    user = User(
        organization_id=org.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.OWNER,
        is_active=True,
    )
    db.add(user)
    db.commit()

    record_audit(
        db, org.id, user.id,
        action="signup", resource_type="organization", resource_id=org.id,
    )

    return _build_tokens(user, org.id)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email, User.is_active == True).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return _build_tokens(user, user.organization_id)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == data["sub"], User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return _build_tokens(user, user.organization_id)


@router.get("/me", response_model=UserResponse)
def me(ctx: AuthContext = Depends(get_current_context)):
    if not ctx.user:
        raise HTTPException(status_code=401, detail="Not authenticated as user")
    return ctx.user


@router.get("/organization", response_model=OrganizationResponse)
def get_organization(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    org = db.query(Organization).filter(Organization.id == ctx.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    payload: UserCreate,
    ctx: AuthContext = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        organization_id=ctx.organization_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole(payload.role),
        is_active=True,
    )
    db.add(user)
    db.commit()

    record_audit(
        db, ctx.organization_id, ctx.user.id if ctx.user else None,
        action="user_created", resource_type="user", resource_id=user.id,
    )
    return user


@router.post("/api-keys", response_model=APIKeyCreatedResponse, status_code=201)
def create_api_key(
    payload: APIKeyCreate,
    ctx: AuthContext = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    full_key, prefix, key_hash = generate_api_key()

    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)

    api_key = APIKey(
        organization_id=ctx.organization_id,
        name=payload.name,
        key_hash=key_hash,
        key_prefix=prefix,
        scopes=payload.scopes,
        expires_at=expires_at,
        created_by=ctx.user.id if ctx.user else "system",
    )
    db.add(api_key)
    db.commit()

    record_audit(
        db, ctx.organization_id, ctx.user.id if ctx.user else None,
        action="api_key_created", resource_type="api_key", resource_id=api_key.id,
    )

    response = APIKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        full_key=full_key,
    )
    return response


@router.get("/api-keys", response_model=list[APIKeyResponse])
def list_api_keys(
    ctx: AuthContext = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    keys = (
        db.query(APIKey)
        .filter(APIKey.organization_id == ctx.organization_id)
        .order_by(APIKey.created_at.desc())
        .all()
    )
    return keys


@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_api_key(
    key_id: str,
    ctx: AuthContext = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    api_key = (
        db.query(APIKey)
        .filter(APIKey.id == key_id, APIKey.organization_id == ctx.organization_id)
        .first()
    )
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.is_active = False
    db.commit()

    record_audit(
        db, ctx.organization_id, ctx.user.id if ctx.user else None,
        action="api_key_revoked", resource_type="api_key", resource_id=key_id,
    )


def _build_tokens(user: User, org_id: str) -> TokenResponse:
    claims = {
        "sub": user.id,
        "org": org_id,
        "role": user.role.value,
        "email": user.email,
    }
    access = create_access_token(claims)
    refresh_tok = create_refresh_token({"sub": user.id})
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_tok,
        expires_in=settings.access_token_expire_minutes * 60,
    )
