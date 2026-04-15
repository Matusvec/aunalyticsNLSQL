import logging

from fastapi import FastAPI
from .routers.query import router as query_router
from .routers.schema import router as schema_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="NL to SQL Backend")

app.include_router(query_router, prefix="/api", tags=["query"])
app.include_router(schema_router, prefix="/api", tags=["schema"])


@app.get("/health")
def health():
    return {"ok": True}
