"""SSRF protections for untrusted webhook destination URLs."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.config import Settings
from app.core.exceptions import ForbiddenError

BLOCKED_HOSTNAMES = frozenset(
    {
        "metadata.google.internal",
        "metadata.google.com",
        "169.254.169.254",
    }
)
ALLOWED_PORTS = frozenset({80, 443, 8080, 8443})


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_webhook_destination(url: str, settings: Settings) -> str:
    """Validate URL before outbound delivery. Raises ForbiddenError if unsafe."""
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    if not host:
        raise ForbiddenError("Webhook URL host is required", code="unsafe_webhook_url")

    allow_dev = settings.DELIVERY_SSRF_ALLOW_DEV_HTTP and (
        settings.is_development or settings.APP_ENV == "test"
    )
    localhost = host in {"localhost", "127.0.0.1", "::1"}

    if scheme == "https":
        pass
    elif scheme == "http" and allow_dev and localhost:
        pass
    else:
        raise ForbiddenError(
            "Webhook URL must use HTTPS (HTTP localhost only in development/test)",
            code="unsafe_webhook_url",
        )

    if host in BLOCKED_HOSTNAMES:
        raise ForbiddenError("Webhook URL host is not allowed", code="unsafe_webhook_url")

    port = parsed.port
    if port is not None:
        if allow_dev and localhost and 1024 <= port <= 65535:
            pass
        elif port not in ALLOWED_PORTS:
            raise ForbiddenError("Webhook URL port is not allowed", code="unsafe_webhook_url")

    try:
        infos = socket.getaddrinfo(host, port or (443 if scheme == "https" else 80))
    except socket.gaierror as exc:
        raise ForbiddenError(
            "Webhook URL host could not be resolved", code="unsafe_webhook_url"
        ) from exc

    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if allow_dev and localhost and ip.is_loopback:
            continue
        if _is_blocked_ip(ip):
            raise ForbiddenError(
                "Webhook URL resolves to a blocked network address",
                code="unsafe_webhook_url",
            )

    return url.strip()
