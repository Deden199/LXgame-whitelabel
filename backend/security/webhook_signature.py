"""Webhook signature verification using HMAC SHA256.

Signature formula: HMAC(secret, timestamp + raw_body)
Headers required:
- X-Signature: HMAC signature hex digest
- X-Timestamp: Unix timestamp (seconds)
"""

import hmac
import hashlib
import os
import time
from typing import Optional


class WebhookSignatureError(Exception):
    """Base exception for webhook signature errors."""
    pass


class WebhookTimestampExpired(WebhookSignatureError):
    """Timestamp is too old (replay attack prevention)."""
    pass


class WebhookSignatureMismatch(WebhookSignatureError):
    """Signature verification failed."""
    pass


WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes


def get_webhook_secret(provider: str) -> str:
    """Get webhook secret for a provider with fallback to default.
    
    Lookup order:
    1. WEBHOOK_SECRET_{PROVIDER} (uppercase)
    2. WEBHOOK_SECRET_DEFAULT
    
    Raises ValueError if no secret is configured.
    """
    provider_key = f"WEBHOOK_SECRET_{provider.upper()}"
    secret = os.environ.get(provider_key)
    
    if not secret:
        secret = os.environ.get("WEBHOOK_SECRET_DEFAULT")
    
    if not secret:
        raise ValueError(f"No webhook secret configured for provider '{provider}' and no default secret set")
    
    return secret


def generate_webhook_signature(secret: str, timestamp: int, raw_body: bytes) -> str:
    """Generate HMAC SHA256 signature for webhook payload.
    
    Args:
        secret: Webhook secret key
        timestamp: Unix timestamp in seconds
        raw_body: Raw request body bytes
    
    Returns:
        Hex-encoded HMAC SHA256 signature
    """
    message = f"{timestamp}".encode() + raw_body
    return hmac.new(
        secret.encode(),
        message,
        hashlib.sha256
    ).hexdigest()


def verify_webhook_signature(
    provider: str,
    raw_body: bytes,
    signature: Optional[str],
    timestamp: Optional[str],
    tolerance_seconds: int = WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS,
) -> bool:
    """Verify webhook signature.
    
    Args:
        provider: Payment provider name
        raw_body: Raw request body bytes
        signature: X-Signature header value
        timestamp: X-Timestamp header value (unix timestamp)
        tolerance_seconds: Maximum age of timestamp in seconds (default 5 min)
    
    Returns:
        True if signature is valid
    
    Raises:
        WebhookSignatureError: Base class for all signature errors
        WebhookTimestampExpired: If timestamp is too old
        WebhookSignatureMismatch: If signature doesn't match
    """
    if not signature:
        raise WebhookSignatureMismatch("Missing X-Signature header")
    
    if not timestamp:
        raise WebhookSignatureMismatch("Missing X-Timestamp header")
    
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        raise WebhookSignatureMismatch("Invalid X-Timestamp format")
    
    # Check timestamp freshness
    current_time = int(time.time())
    if abs(current_time - ts) > tolerance_seconds:
        raise WebhookTimestampExpired(
            f"Webhook timestamp expired. Current: {current_time}, Received: {ts}, "
            f"Tolerance: {tolerance_seconds}s"
        )
    
    # Get secret for provider
    secret = get_webhook_secret(provider)
    
    # Generate expected signature
    expected_signature = generate_webhook_signature(secret, ts, raw_body)
    
    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(signature, expected_signature):
        raise WebhookSignatureMismatch("Invalid webhook signature")
    
    return True
