from __future__ import annotations

import logging

from dotenv import find_dotenv, load_dotenv

# Load .env before importing settings so values are available at import time.
load_dotenv(find_dotenv(usecwd=True), override=False)

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.logging_config import configure_logging
from app.middleware import BodySizeLimitMiddleware, RequestIDMiddleware
from app.rate_limit import limiter
from app.routers.query import router as query_router
from app.routers.schema import router as schema_router
from app.routers.upload import router as upload_router
from app.services import gemini_service
from app.services.history_service import ensure_history_table
from app.settings import get_settings


configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.db_dir.mkdir(parents=True, exist_ok=True)
    try:
        ensure_history_table()
    except Exception:
        logger.exception("Failed to initialize history database")
    yield


app = FastAPI(title="NL to SQL Backend", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Outermost middleware first; FastAPI applies them in reverse order of add_middleware.
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    BodySizeLimitMiddleware,
    max_bytes=settings.max_request_bytes,
    exempt_paths=("/api/upload",),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["content-type", "x-request-id"],
)
app.add_middleware(RequestIDMiddleware)


app.include_router(query_router, prefix="/api", tags=["query"])
app.include_router(schema_router, prefix="/api", tags=["schema"])
app.include_router(upload_router, prefix="/api", tags=["upload"])


@app.get("/health")
def health() -> dict:
    """Liveness probe — returns 200 as long as the process is up."""
    return {"ok": True}


@app.get("/ready")
async def ready() -> JSONResponse:
    """Readiness probe — checks DB dir, history DB, and at least one LLM backend."""
    checks: dict[str, dict] = {}
    overall_ok = True

    # DB directory
    try:
        if not settings.db_dir.exists():
            settings.db_dir.mkdir(parents=True, exist_ok=True)
        probe = settings.db_dir / ".readyz_probe"
        probe.write_text("ok")
        probe.unlink(missing_ok=True)
        checks["db_dir"] = {"ok": True, "path": str(settings.db_dir)}
    except Exception as exc:
        checks["db_dir"] = {"ok": False, "error": exc.__class__.__name__}
        overall_ok = False

    # History DB
    try:
        ensure_history_table()
        checks["history_db"] = {"ok": True}
    except Exception as exc:
        checks["history_db"] = {"ok": False, "error": exc.__class__.__name__}
        overall_ok = False

    # Ollama
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(settings.ollama_tags_url)
            ollama_ok = r.status_code < 500
        checks["ollama"] = {"ok": ollama_ok}
    except Exception as exc:
        checks["ollama"] = {"ok": False, "error": exc.__class__.__name__}

    # Gemini
    gemini_configured = gemini_service.is_configured()
    checks["gemini"] = {"ok": gemini_configured, "configured": gemini_configured}

    # At least one LLM must be available
    if not (ollama_ok or gemini_configured):
        overall_ok = False

    body = {"ok": overall_ok, "checks": checks}
    return JSONResponse(body, status_code=200 if overall_ok else 503)
