"""Retry classification and exponential backoff with jitter."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

RETRYABLE_STATUS_CODES = frozenset({408, 425, 429}) | frozenset(range(500, 600))
PERMANENT_STATUS_CODES = frozenset({400, 401, 403, 404, 405, 410, 422})


def is_retryable_http_status(status_code: int | None) -> bool:
    if status_code is None:
        return True
    if status_code in PERMANENT_STATUS_CODES:
        return False
    if status_code in RETRYABLE_STATUS_CODES:
        return True
    # Other 4xx are permanent by default
    if 400 <= status_code < 500:
        return False
    return status_code >= 500


def compute_backoff_seconds(
    attempt_number: int,
    *,
    base_delay: float,
    multiplier: float,
    max_delay: float,
    jitter_ratio: float = 0.2,
) -> float:
    """Exponential backoff with bounded random jitter.

    attempt_number is 1-based (first failure schedules attempt 2).
    """
    exp = max(attempt_number - 1, 0)
    delay = min(base_delay * (multiplier**exp), max_delay)
    jitter = delay * jitter_ratio * random.random()
    return min(delay + jitter, max_delay)


def next_attempt_time(
    attempt_number: int,
    *,
    base_delay: float,
    multiplier: float,
    max_delay: float,
    retry_after_seconds: float | None = None,
) -> datetime:
    if retry_after_seconds is not None:
        delay = min(max(retry_after_seconds, 0.0), max_delay)
    else:
        delay = compute_backoff_seconds(
            attempt_number,
            base_delay=base_delay,
            multiplier=multiplier,
            max_delay=max_delay,
        )
    return datetime.now(UTC) + timedelta(seconds=delay)


def parse_retry_after(header_value: str | None, *, max_delay: float) -> float | None:
    if not header_value:
        return None
    value = header_value.strip()
    try:
        seconds = float(value)
        return min(max(seconds, 0.0), max_delay)
    except ValueError:
        return None
