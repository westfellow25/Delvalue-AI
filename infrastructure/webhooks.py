"""
DelValue AI — Webhook dispatch

Notify external systems of key events (score computed, outcome recorded, alert fired).
Uses HMAC-SHA256 signatures for authenticity.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class WebhookEvent:
    # Enum-like constants for event types
    PROCESS_CREATED = "process.created"
    PROCESS_ANALYZED = "process.analyzed"
    SCORE_COMPUTED = "score.computed"
    OUTCOME_RECORDED = "outcome.recorded"
    VARIANCE_ALERT = "alert.variance"
    DRIFT_DETECTED = "alert.drift"
    MINING_COMPLETED = "mining.completed"


class WebhookDispatcher:
    """Dispatch events to registered webhooks with retry logic."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=False,
    )
    def dispatch(
        self,
        webhook_url: str,
        event_type: str,
        payload: dict,
        signing_secret: Optional[str] = None,
    ) -> bool:
        """
        Send a webhook notification. Returns True on success.
        Signs the payload with HMAC-SHA256 if a secret is provided.
        """
        body = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        }
        body_json = json.dumps(body, sort_keys=True, default=str)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "DelValue-AI-Webhooks/1.0",
            "X-DelValue-Event": event_type,
        }
        if signing_secret:
            signature = hmac.new(
                signing_secret.encode(),
                body_json.encode(),
                hashlib.sha256,
            ).hexdigest()
            headers["X-DelValue-Signature"] = f"sha256={signature}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(webhook_url, content=body_json, headers=headers)
                if response.status_code >= 400:
                    logger.warning(
                        f"Webhook {webhook_url} returned {response.status_code}"
                    )
                    return False
                return True
        except httpx.RequestError as e:
            logger.error(f"Webhook delivery failed: {e}")
            raise


def verify_signature(body: bytes, signature_header: str, secret: str) -> bool:
    """Verify an incoming webhook signature (for bidirectional integration)."""
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    provided = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)
