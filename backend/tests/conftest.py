"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import settings as settings_module  # noqa: E402
from app.rate_limit import limiter  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch):
    """Reset cached settings + disable rate limiting for the duration of each test."""
    settings_module.reload_settings()
    original_enabled = limiter.enabled
    limiter.enabled = False
    try:
        yield
    finally:
        limiter.enabled = original_enabled
        limiter.reset()
        settings_module.reload_settings()


@pytest.fixture
def anyio_backend():
    return "asyncio"
