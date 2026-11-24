"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SECRET_DENYLIST = {
    "dev-only-insecure-secret-key-change-me",
    "change-me-to-a-long-random-string-in-production",
    "change-me",
    "changeme",
    "secret",
    "password",
}


class Settings(BaseSettings):
    """Central configuration for HookForge.

    Values are loaded from environment variables and an optional `.env` file.
    Production deployments must override SECRET_KEY and tighten CORS_ORIGINS.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "HookForge"
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    SECRET_KEY: str = Field(
        default="dev-only-insecure-secret-key-change-me",
        min_length=16,
    )
    # Dedicated pepper for API-key hashes; falls back to SECRET_KEY when empty.
    API_KEY_PEPPER: str = ""
    # Fernet key (url-safe base64 32-byte) for endpoint signing-secret encryption.
    # When empty, secrets remain plaintext (dev) or derived from SECRET_KEY in production helpers.
    ENDPOINT_SECRET_ENCRYPTION_KEY: str = ""
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://hookforge:hookforge@localhost:5432/hookforge"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    TRUSTED_HOSTS: str = "localhost,127.0.0.1"

    # JWT / auth
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_MINUTES: int = 60
    ALLOW_PUBLIC_REGISTRATION: bool = True

    # Request limits
    MAX_REQUEST_BODY_BYTES: int = 1_048_576  # 1 MiB
    API_KEY_LAST_USED_MIN_INTERVAL_SECONDS: int = 60
    RATE_LIMIT_ENABLED_IN_TEST: bool = False

    # Redis required for live delivery enqueue; tests may set false
    REDIS_REQUIRED: bool = False

    # Delivery engine
    DELIVERY_HTTP_TIMEOUT_SECONDS: float = 10.0
    DELIVERY_MAX_ATTEMPTS: int = 6
    DELIVERY_RETRY_BASE_DELAY_SECONDS: float = 5.0
    DELIVERY_RETRY_MAX_DELAY_SECONDS: float = 3600.0
    DELIVERY_RETRY_MULTIPLIER: float = 2.0
    DELIVERY_STALE_PROCESSING_SECONDS: int = 300
    DELIVERY_RECOVERY_BATCH_SIZE: int = 100
    DELIVERY_RECOVERY_INTERVAL_SECONDS: int = 30
    DELIVERY_MAX_PAYLOAD_BYTES: int = 262_144  # 256 KiB outbound JSON
    DELIVERY_ALLOW_HTTP_LOCALHOST: bool = True
    DELIVERY_SSRF_ALLOW_DEV_HTTP: bool = True

    # Connection pool tuning
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def jwt_algorithm_allowlist(cls, value: str) -> str:
        allowed = {"HS256"}
        if value not in allowed:
            raise ValueError(f"JWT_ALGORITHM must be one of {sorted(allowed)}")
        return value

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_not_placeholder_in_production(cls, value: str, info) -> str:
        env = (info.data or {}).get("APP_ENV", "development")
        if env == "production":
            lowered = value.strip().lower()
            if (
                value.startswith("dev-only")
                or lowered in _SECRET_DENYLIST
                or "change-me" in lowered
                or len(value) < 32
            ):
                raise ValueError(
                    "SECRET_KEY must be a strong random value (>=32 chars) in production"
                )
        return value

    @field_validator("CORS_ORIGINS")
    @classmethod
    def cors_not_wildcard_in_production(cls, value: str, info) -> str:
        env = (info.data or {}).get("APP_ENV", "development")
        origins = [o.strip() for o in value.split(",") if o.strip()]
        if env == "production" and ("*" in origins or not origins):
            raise ValueError("CORS_ORIGINS must be an explicit allow-list in production")
        return value

    @model_validator(mode="after")
    def production_fail_closed(self) -> Self:
        if self.APP_ENV != "production":
            return self
        if self.DEBUG:
            raise ValueError("DEBUG must be false in production")
        if not self.REDIS_REQUIRED:
            raise ValueError("REDIS_REQUIRED must be true in production")
        if self.DELIVERY_SSRF_ALLOW_DEV_HTTP or self.DELIVERY_ALLOW_HTTP_LOCALHOST:
            raise ValueError(
                "DELIVERY_ALLOW_HTTP_LOCALHOST and DELIVERY_SSRF_ALLOW_DEV_HTTP "
                "must be false in production"
            )
        if self.ALLOW_PUBLIC_REGISTRATION:
            raise ValueError(
                "ALLOW_PUBLIC_REGISTRATION must be false in production "
                "(use invite/provisioning flows)"
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [h.strip() for h in self.TRUSTED_HOSTS.split(",") if h.strip()]

    @property
    def api_key_pepper(self) -> str:
        return self.API_KEY_PEPPER or self.SECRET_KEY

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear the settings cache (useful in tests)."""
    get_settings.cache_clear()
