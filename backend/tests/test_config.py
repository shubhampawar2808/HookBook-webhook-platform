"""Tests for settings validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings, clear_settings_cache


def test_default_development_settings() -> None:
    clear_settings_cache()
    settings = Settings(
        APP_ENV="development",
        SECRET_KEY="dev-only-insecure-secret-key-change-me",
        CORS_ORIGINS="http://localhost:5173",
    )
    assert settings.APP_NAME == "HookForge"
    assert settings.cors_origin_list == ["http://localhost:5173"]
    assert settings.is_development is True


def test_production_rejects_dev_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            SECRET_KEY="dev-only-insecure-secret-key-change-me",
            CORS_ORIGINS="https://app.example.com",
            DEBUG=False,
            REDIS_REQUIRED=True,
            DELIVERY_ALLOW_HTTP_LOCALHOST=False,
            DELIVERY_SSRF_ALLOW_DEV_HTTP=False,
            ALLOW_PUBLIC_REGISTRATION=False,
        )


def test_production_rejects_placeholder_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            SECRET_KEY="change-me-to-a-long-random-string-in-production",
            CORS_ORIGINS="https://app.example.com",
            DEBUG=False,
            REDIS_REQUIRED=True,
            DELIVERY_ALLOW_HTTP_LOCALHOST=False,
            DELIVERY_SSRF_ALLOW_DEV_HTTP=False,
            ALLOW_PUBLIC_REGISTRATION=False,
        )


def test_production_rejects_debug_true() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            SECRET_KEY="a-very-strong-production-secret-key-32b",
            CORS_ORIGINS="https://app.example.com",
            DEBUG=True,
            REDIS_REQUIRED=True,
            DELIVERY_ALLOW_HTTP_LOCALHOST=False,
            DELIVERY_SSRF_ALLOW_DEV_HTTP=False,
            ALLOW_PUBLIC_REGISTRATION=False,
        )


def test_production_rejects_optional_redis() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            SECRET_KEY="a-very-strong-production-secret-key-32b",
            CORS_ORIGINS="https://app.example.com",
            DEBUG=False,
            REDIS_REQUIRED=False,
            DELIVERY_ALLOW_HTTP_LOCALHOST=False,
            DELIVERY_SSRF_ALLOW_DEV_HTTP=False,
            ALLOW_PUBLIC_REGISTRATION=False,
        )


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            SECRET_KEY="a-very-strong-production-secret-key-32b",
            CORS_ORIGINS="*",
            DEBUG=False,
            REDIS_REQUIRED=True,
            DELIVERY_ALLOW_HTTP_LOCALHOST=False,
            DELIVERY_SSRF_ALLOW_DEV_HTTP=False,
            ALLOW_PUBLIC_REGISTRATION=False,
        )


def test_production_accepts_explicit_config() -> None:
    settings = Settings(
        APP_ENV="production",
        SECRET_KEY="a-very-strong-production-secret-key-32b",
        CORS_ORIGINS="https://app.example.com",
        DEBUG=False,
        REDIS_REQUIRED=True,
        DELIVERY_ALLOW_HTTP_LOCALHOST=False,
        DELIVERY_SSRF_ALLOW_DEV_HTTP=False,
        ALLOW_PUBLIC_REGISTRATION=False,
    )
    assert settings.is_production is True
    assert settings.cors_origin_list == ["https://app.example.com"]


def test_jwt_algorithm_allowlist() -> None:
    with pytest.raises(ValidationError):
        Settings(APP_ENV="development", JWT_ALGORITHM="none")
