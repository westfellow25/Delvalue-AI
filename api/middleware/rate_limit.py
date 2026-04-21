"""
DelValue AI — Rate Limiting Middleware

Simple sliding-window rate limiter. In-memory by default; swap for Redis in prod.
Applies per-tenant limits based on subscription tier.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

from data.models.organization import SubscriptionTier


TIER_LIMITS = {
    SubscriptionTier.FREE: {"per_minute": 10, "per_hour": 100},
    SubscriptionTier.STARTER: {"per_minute": 30, "per_hour": 500},
    SubscriptionTier.PROFESSIONAL: {"per_minute": 100, "per_hour": 2000},
    SubscriptionTier.ENTERPRISE: {"per_minute": 500, "per_hour": 10_000},
}


class SlidingWindowLimiter:
    """Thread-safe in-memory sliding-window rate limiter."""

    def __init__(self):
        self._requests: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """
        Check if request is within limits.
        Returns (allowed, retry_after_seconds).
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            history = self._requests[key]
            # Drop old entries
            while history and history[0] < cutoff:
                history.popleft()

            if len(history) >= limit:
                oldest = history[0]
                retry_after = int((oldest + window_seconds) - now) + 1
                return False, retry_after

            history.append(now)
            return True, 0


_limiter = SlidingWindowLimiter()


def rate_limit_check(
    request: Request,
    organization_id: str,
    tier: SubscriptionTier = SubscriptionTier.FREE,
    endpoint_multiplier: float = 1.0,
) -> None:
    """
    Enforce rate limits for a request. Raises 429 if exceeded.
    endpoint_multiplier: costly endpoints (LLM, simulation) can set this > 1.
    """
    limits = TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.FREE])
    per_minute = int(limits["per_minute"] / endpoint_multiplier)
    per_hour = int(limits["per_hour"] / endpoint_multiplier)

    minute_key = f"{organization_id}:min"
    hour_key = f"{organization_id}:hr"

    allowed_min, retry_min = _limiter.check(minute_key, per_minute, 60)
    if not allowed_min:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded (per-minute). Retry in {retry_min}s",
            headers={"Retry-After": str(retry_min)},
        )

    allowed_hr, retry_hr = _limiter.check(hour_key, per_hour, 3600)
    if not allowed_hr:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded (per-hour). Retry in {retry_hr}s",
            headers={"Retry-After": str(retry_hr)},
        )
