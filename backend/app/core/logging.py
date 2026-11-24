"""Structured logging configuration for HookForge."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.config import Settings

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "secret",
        "secret_key",
        "token",
        "authorization",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "credentials",
    }
)


def _sanitize_event_dict(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Redact known sensitive keys from log events."""
    sanitized: dict[str, Any] = {}
    for key, value in event_dict.items():
        if key.lower() in SENSITIVE_KEYS or any(
            s in key.lower() for s in ("password", "secret", "token", "authorization")
        ):
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = value
    return sanitized


def configure_logging(settings: Settings) -> None:
    """Configure structlog and stdlib logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        _sanitize_event_dict,
    ]

    if settings.DEBUG and not settings.is_production:
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    # Quieten noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
