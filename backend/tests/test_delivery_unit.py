"""Unit tests for delivery signing, retry, SSRF, sanitization."""

from __future__ import annotations

import uuid

import pytest

from app.core.config import Settings
from app.core.exceptions import ForbiddenError
from app.services.delivery_dispatch import build_idempotency_key
from app.services.delivery_retry import (
    compute_backoff_seconds,
    is_retryable_http_status,
)
from app.services.delivery_sanitize import sanitize_text, summarize_response_body
from app.services.delivery_signing import sign_webhook_body, verify_webhook_signature
from app.services.delivery_ssrf import validate_webhook_destination


def test_hmac_signature_roundtrip() -> None:
    body = b'{"hello":"world"}'
    ts = "1710000000"
    secret = "whsec_test_secret"
    sig = sign_webhook_body(secret=secret, timestamp=ts, body=body)
    assert sig.startswith("sha256=")
    assert verify_webhook_signature(secret=secret, timestamp=ts, body=body, signature_header=sig)
    assert not verify_webhook_signature(
        secret="other", timestamp=ts, body=body, signature_header=sig
    )


def test_retryable_status_classification() -> None:
    assert is_retryable_http_status(500)
    assert is_retryable_http_status(429)
    assert is_retryable_http_status(408)
    assert is_retryable_http_status(None)
    assert not is_retryable_http_status(400)
    assert not is_retryable_http_status(401)
    assert not is_retryable_http_status(404)
    assert not is_retryable_http_status(422)


def test_backoff_increases_and_caps() -> None:
    d1 = compute_backoff_seconds(1, base_delay=5, multiplier=2, max_delay=3600, jitter_ratio=0)
    d2 = compute_backoff_seconds(2, base_delay=5, multiplier=2, max_delay=3600, jitter_ratio=0)
    d3 = compute_backoff_seconds(20, base_delay=5, multiplier=2, max_delay=100, jitter_ratio=0)
    assert d1 == 5
    assert d2 == 10
    assert d3 == 100


def test_idempotency_key_stable() -> None:
    e = uuid.uuid4()
    p = uuid.uuid4()
    assert build_idempotency_key(e, p) == build_idempotency_key(e, p)


def test_ssrf_blocks_private_and_allows_localhost_http_in_dev() -> None:
    settings = Settings(
        APP_ENV="development",
        SECRET_KEY="test-secret-key-16chars-min",
        DELIVERY_SSRF_ALLOW_DEV_HTTP=True,
    )
    validate_webhook_destination("http://127.0.0.1:9999/hook", settings)
    with pytest.raises(ForbiddenError):
        validate_webhook_destination("http://192.168.1.10/hook", settings)
    with pytest.raises(ForbiddenError):
        validate_webhook_destination("http://169.254.169.254/latest", settings)


def test_sanitize_redacts_secrets() -> None:
    text = sanitize_text("authorization: Bearer abcdef password=supersecret")
    assert text is not None
    assert "supersecret" not in text
    assert "***REDACTED***" in text
    assert summarize_response_body(b'{"ok":true}') == '{"ok":true}'
