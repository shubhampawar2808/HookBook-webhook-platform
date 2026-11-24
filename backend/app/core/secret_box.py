"""Encrypt endpoint signing secrets at rest (Fernet) with plaintext dual-read."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings

_PREFIX = "enc:v1:"


def _fernet(settings: Settings) -> Fernet | None:
    raw = (settings.ENDPOINT_SECRET_ENCRYPTION_KEY or "").strip()
    if raw:
        try:
            return Fernet(raw.encode("utf-8"))
        except Exception:
            # Allow passing raw 32+ char secret — derive Fernet key
            digest = hashlib.sha256(raw.encode("utf-8")).digest()
            return Fernet(base64.urlsafe_b64encode(digest))
    if settings.is_production:
        digest = hashlib.sha256(
            f"hookforge-endpoint-secret:{settings.SECRET_KEY}".encode()
        ).digest()
        return Fernet(base64.urlsafe_b64encode(digest))
    return None


def seal_endpoint_secret(plaintext: str, settings: Settings) -> str:
    box = _fernet(settings)
    if box is None:
        return plaintext
    token = box.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return f"{_PREFIX}{token}"


def open_endpoint_secret(stored: str, settings: Settings) -> str:
    if not stored.startswith(_PREFIX):
        return stored
    box = _fernet(settings)
    if box is None:
        raise ValueError("Encrypted endpoint secret present but encryption key unavailable")
    token = stored[len(_PREFIX) :]
    try:
        return box.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt endpoint signing secret") from exc
