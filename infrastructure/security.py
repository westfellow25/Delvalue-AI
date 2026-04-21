"""
DelValue AI — Security utilities

Password hashing, JWT token management, API key generation.
Uses pure-Python HMAC-based JWT when python-jose[cryptography] is unavailable.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from api.config import get_settings

settings = get_settings()

# --- JWT (pure-Python HMAC-SHA256 fallback) ---

_HAS_JOSE = False
try:
    import importlib
    # Guard against pyo3 panics from broken cryptography backend
    _jose_mod = importlib.import_module("jose.jwt")
    _jose_jwt = _jose_mod
    _HAS_JOSE = True
except (ImportError, ModuleNotFoundError):
    pass
except BaseException:
    # pyo3_runtime.PanicException inherits BaseException
    pass


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def _jwt_encode_fallback(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    # Convert datetime to timestamp
    p = payload.copy()
    for k, v in p.items():
        if isinstance(v, datetime):
            p[k] = int(v.timestamp())
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    b = _b64url_encode(json.dumps(p, separators=(",", ":"), default=str).encode())
    sig_input = f"{h}.{b}".encode()
    sig = hmac.new(secret.encode(), sig_input, hashlib.sha256).digest()
    return f"{h}.{b}.{_b64url_encode(sig)}"


def _jwt_decode_fallback(token: str, secret: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h, b, s = parts
        sig_input = f"{h}.{b}".encode()
        expected_sig = hmac.new(secret.encode(), sig_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(s)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(_b64url_decode(b))
        if "exp" in payload and payload["exp"] < time.time():
            return None
        return payload
    except Exception:
        return None


# --- Password hashing ---

try:
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(password: str) -> str:
        return _pwd_context.hash(password)

    def verify_password(plain: str, hashed: str) -> bool:
        return _pwd_context.verify(plain, hashed)

except Exception:
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        h = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
        return f"sha256:{salt}:{h}"

    def verify_password(plain: str, hashed: str) -> bool:
        if not hashed.startswith("sha256:"):
            return False
        _, salt, expected = hashed.split(":", 2)
        actual = hashlib.sha256(f"{salt}:{plain}".encode()).hexdigest()
        return secrets.compare_digest(actual, expected)


# --- JWT public API ---

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    if _HAS_JOSE:
        return _jose_jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    return _jwt_encode_fallback(to_encode, settings.secret_key)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    if _HAS_JOSE:
        return _jose_jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    return _jwt_encode_fallback(to_encode, settings.secret_key)


def decode_token(token: str) -> Optional[dict]:
    if _HAS_JOSE:
        try:
            return _jose_jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        except Exception:
            return None
    return _jwt_decode_fallback(token, settings.secret_key)


# --- API keys ---

def generate_api_key() -> tuple[str, str, str]:
    raw = secrets.token_urlsafe(32)
    full_key = f"{settings.api_key_prefix}{raw}"
    prefix = full_key[:12]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash


def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
    return secrets.compare_digest(provided_hash, stored_hash)
