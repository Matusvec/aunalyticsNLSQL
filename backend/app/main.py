from fastapi import FastAPI
from .routers.query import router as query_router
from .routers.schema import router as schema_router
from .routers.upload import router as upload_router

app = FastAPI(title="NL to SQL Backend")

app.include_router(query_router, prefix="/api", tags=["query"])
app.include_router(schema_router, prefix="/api", tags=["schema"])  # For MCP tools
app.include_router(upload_router, prefix="/api", tags=["upload"])


@app.get("/health")
def health():
    return {"ok": True}