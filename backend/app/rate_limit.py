from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.settings import get_settings


_settings = get_settings()


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[_settings.rate_limit_default] if _settings.rate_limit_enabled else [],
    enabled=_settings.rate_limit_enabled,
    headers_enabled=True,
)


def rate(value: str):
    """Wrapper used by routers so per-route limits live next to the endpoint they protect."""
    return limiter.limit(value)
