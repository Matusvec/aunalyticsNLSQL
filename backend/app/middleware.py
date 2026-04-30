from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


logger = logging.getLogger("app.access")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a request_id to every request and emit one structured access log line."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request.state.request_id = rid
        start = time.perf_counter()

        response: Response | None = None
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["x-request-id"] = rid
            return response
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            logger.info(
                "%s %s %s %.1fms",
                request.method,
                request.url.path,
                status,
                elapsed_ms,
                extra={
                    "request_id": rid,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "client": request.client.host if request.client else None,
                },
            )


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject non-upload requests whose body exceeds max_bytes (Content-Length-based)."""

    def __init__(self, app: ASGIApp, max_bytes: int, exempt_paths: tuple[str, ...] = ()) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes
        self._exempt_paths = exempt_paths

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self._exempt_paths):
            return await call_next(request)

        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                length = int(cl)
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
            if length > self._max_bytes:
                return JSONResponse(
                    {"detail": f"Request body too large (limit {self._max_bytes} bytes)."},
                    status_code=413,
                )
        return await call_next(request)
