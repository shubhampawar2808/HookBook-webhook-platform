"""HMAC-SHA256 webhook request signing and verification helpers."""

from __future__ import annotations

import hashlib
import hmac


def build_signing_payload(timestamp: str, body: bytes) -> bytes:
    """Canonical signing input: timestamp + '.' + raw body bytes."""
    return timestamp.encode("utf-8") + b"." + body


def sign_webhook_body(*, secret: str, timestamp: str, body: bytes) -> str:
    """Return signature header value: sha256=<hex>."""
    digest = hmac.new(
        secret.encode("utf-8"),
        build_signing_payload(timestamp, body),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def verify_webhook_signature(
    *,
    secret: str,
    timestamp: str,
    body: bytes,
    signature_header: str,
) -> bool:
    """Constant-time comparison of an incoming HookForge signature header."""
    expected = sign_webhook_body(secret=secret, timestamp=timestamp, body=body)
    return hmac.compare_digest(expected, signature_header.strip())
