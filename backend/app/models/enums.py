"""Domain enumerations shared by ORM models and schemas."""

from __future__ import annotations

import enum


class OrganizationStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class APIKeyStatus(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class EndpointStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class EventStatus(str, enum.Enum):
    ACCEPTED = "accepted"
    # Accepted means persisted; outbound delivery is tracked on WebhookDelivery.


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class AttemptOutcome(str, enum.Enum):
    SUCCESS = "success"
    RETRYABLE_FAILURE = "retryable_failure"
    PERMANENT_FAILURE = "permanent_failure"
