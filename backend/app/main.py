import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.query import router as query_router
from .routers.schema import router as schema_router
from .routers.upload import router as upload_router

app = FastAPI(title="NL to SQL Backend")

_cors_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://127.0.0.1:3000,http://localhost:3000",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router, prefix="/api", tags=["query"])
app.include_router(schema_router, prefix="/api", tags=["schema"])
app.include_router(upload_router, prefix="/api", tags=["upload"])


@app.get("/health")
def health():
    return {"ok": True}
