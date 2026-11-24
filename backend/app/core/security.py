"""Password hashing, JWT, and API-key crypto helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import Settings

# Argon2id via pwdlib
_password_hash = PasswordHash((Argon2Hasher(),))

API_KEY_PREFIX = "hfk"
API_KEY_DISPLAY_PREFIX_LEN = 8


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(password, password_hash)
    except Exception:
        return False


def create_access_token(
    *,
    settings: Settings,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    role: str,
) -> tuple[str, str, datetime]:
    """Return (token, jti, expires_at)."""
    jti = str(uuid.uuid4())
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_MINUTES)
    payload = {
        "sub": str(user_id),
        "org": str(organization_id),
        "role": role,
        "jti": jti,
        "typ": "access",
        "iat": datetime.now(UTC),
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_at


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "sub", "org", "role", "jti", "typ"]},
    )


def generate_api_key() -> tuple[str, str, str]:
    """Return (raw_key, key_prefix, key_hash_input_secret).

    Format: hfk_<8-char-prefix>_<43-char-secret>
    Only the hash of the full raw key is stored.
    """
    prefix = secrets.token_hex(API_KEY_DISPLAY_PREFIX_LEN // 2)
    secret = secrets.token_urlsafe(32)
    raw_key = f"{API_KEY_PREFIX}_{prefix}_{secret}"
    return raw_key, prefix, raw_key


def hash_api_key(raw_key: str, settings: Settings) -> str:
    """Peppered HMAC-SHA256 of the raw API key (uses API_KEY_PEPPER when set)."""
    digest = hmac.new(
        settings.api_key_pepper.encode("utf-8"),
        raw_key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


def lookalike_api_key_hash(raw_key: str, settings: Settings) -> str:
    """Alias used during verification — same as hash_api_key."""
    return hash_api_key(raw_key, settings)


# Constant Argon2 hash used to normalize login timing when the user row is missing.
_DUMMY_PASSWORD_HASH = hash_password("hookforge-timing-dummy-password-not-used")


def harden_login_password_check(password: str, password_hash: str | None) -> bool:
    """Verify password, always performing an Argon2 verify to reduce timing oracles."""
    if password_hash:
        return verify_password(password, password_hash)
    verify_password(password, _DUMMY_PASSWORD_HASH)
    return False


def parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def is_api_key_authorization(authorization: str | None) -> bool:
    token = parse_bearer_token(authorization)
    return bool(token and token.startswith(f"{API_KEY_PREFIX}_"))


def generate_public_event_id() -> str:
    return f"evt_{secrets.token_hex(16)}"
