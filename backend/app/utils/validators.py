"""Shared input validation helpers."""

from __future__ import annotations

import re
from urllib.parse import urlparse

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EVENT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$|^[a-z][a-z0-9_]*$")


def validate_organization_slug(slug: str) -> str:
    normalized = slug.strip().lower()
    if not (2 <= len(normalized) <= 100):
        raise ValueError("Slug must be between 2 and 100 characters")
    if not SLUG_PATTERN.match(normalized):
        raise ValueError("Slug must use lowercase letters, numbers, and single hyphens")
    return normalized


def validate_event_type_name(name: str) -> str:
    normalized = name.strip().lower()
    if not (2 <= len(normalized) <= 120):
        raise ValueError("Event type name must be between 2 and 120 characters")
    if not EVENT_TYPE_PATTERN.match(normalized):
        raise ValueError(
            "Event type name must be lowercase alphanumeric with optional dots "
            "(e.g. invoice.paid)"
        )
    return normalized


def validate_webhook_url(url: str, *, allow_localhost: bool = True) -> str:
    """Validate webhook destination URL without making outbound requests.

    Allows http/https. Localhost HTTP is permitted for local development.
    Strict SSRF protections for delivery are deferred to Prompt 3.
    """
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL scheme must be http or https")
    if not parsed.netloc:
        raise ValueError("URL must include a host")
    if parsed.username or parsed.password:
        raise ValueError("URL must not include credentials")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("URL must include a host")
    if parsed.scheme == "http" and not allow_localhost:
        raise ValueError("HTTPS is required")
    if parsed.scheme == "http" and host not in {"localhost", "127.0.0.1", "::1"}:
        # Soft guidance: non-localhost HTTP still allowed in development registration;
        # delivery-time SSRF policy will tighten this in Prompt 3.
        pass
    return cleaned


def validate_password_strength(password: str) -> str:
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters")
    if len(password) > 128:
        raise ValueError("Password must be at most 128 characters")
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_letter and has_digit):
        raise ValueError("Password must include at least one letter and one digit")
    return password
