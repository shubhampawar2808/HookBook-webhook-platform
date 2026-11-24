"""Sanitize delivery logs and stored response excerpts."""

from __future__ import annotations

import re

_SECRET_PATTERNS = re.compile(
    r"(password|secret|token|authorization|api[_-]?key)\s*[:=]\s*\S+",
    re.IGNORECASE,
)


def sanitize_text(value: str | None, *, max_length: int = 1024) -> str | None:
    if value is None:
        return None
    cleaned = _SECRET_PATTERNS.sub(r"\1=***REDACTED***", value)
    cleaned = cleaned.replace("\x00", "")
    if len(cleaned) > max_length:
        return cleaned[: max_length - 3] + "..."
    return cleaned


def summarize_response_body(body: bytes | str | None, *, max_length: int = 512) -> str | None:
    if body is None:
        return None
    if isinstance(body, bytes):
        try:
            text = body.decode("utf-8", errors="replace")
        except Exception:
            text = repr(body[:max_length])
    else:
        text = body
    return sanitize_text(text, max_length=max_length)
