"""Windows Redis 3.0-compatible Celery worker launcher for local development.

Disables remote control / mingle / gossip / heartbeat to avoid Lua script errors
on the portable Microsoft Redis 3.0 build. Does not change Celery app task code.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.workers.celery_app import celery_app  # noqa: E402

celery_app.conf.worker_enable_remote_control = False

if __name__ == "__main__":
    celery_app.worker_main(
        [
            "worker",
            "--loglevel=INFO",
            "--pool=solo",
            "--without-mingle",
            "--without-gossip",
            "--without-heartbeat",
        ]
    )
