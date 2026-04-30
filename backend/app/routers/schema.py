from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Path, Request

import asyncio

from app.services.sqlite_service import (
    build_schema_summary,
    describe_table,
    foreign_keys_impl,
    list_tables,
    row_count_impl,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _request_id(request: Request | None) -> str:
    if request is None:
        return "-"
    rid = getattr(request.state, "request_id", None)
    return rid if isinstance(rid, str) else "-"


@router.get("/schema/{db_filename}")
async def get_schema(
    request: Request,
    db_filename: str = Path(..., min_length=1, max_length=255),
):
    rid = _request_id(request)
    try:
        tables = await list_tables(db_filename)
        described = []
        for t in tables:
            described.append(await describe_table(db_filename, t))
        return {"database": db_filename, "tables": described}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("rid=%s schema_load_failed", rid)
        raise HTTPException(status_code=500, detail="Failed to load schema.") from None


@router.get("/schema-graph/{db_filename}")
async def get_schema_graph(
    request: Request,
    db_filename: str = Path(..., min_length=1, max_length=255),
):
    """Return tables (with row counts) and foreign keys — drives the live SchemaMap UI."""
    rid = _request_id(request)
    try:
        tables = await list_tables(db_filename)

        async def for_table(name: str):
            described = await describe_table(db_filename, name)
            fks = await asyncio.to_thread(foreign_keys_impl, db_filename, name)
            count = await asyncio.to_thread(row_count_impl, db_filename, name)
            return {
                "name": name,
                "row_count": count,
                "columns": described["columns"],
                "foreign_keys": fks,
            }

        gathered = [await for_table(t) for t in tables]
        edges = [
            {
                "from_table": t["name"],
                "from_column": fk["from_column"],
                "to_table": fk["to_table"],
                "to_column": fk["to_column"],
            }
            for t in gathered
            for fk in t["foreign_keys"]
        ]

        return {
            "database": db_filename,
            "tables": [
                {"name": t["name"], "row_count": t["row_count"], "columns": t["columns"]}
                for t in gathered
            ],
            "foreign_keys": edges,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("rid=%s schema_graph_failed", rid)
        raise HTTPException(status_code=500, detail="Failed to build schema graph.") from None


@router.get("/schema-summary/{db_filename}")
async def get_schema_summary(
    request: Request,
    db_filename: str = Path(..., min_length=1, max_length=255),
):
    rid = _request_id(request)
    try:
        return {
            "database": db_filename,
            "schema_summary": await build_schema_summary(db_filename),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("rid=%s schema_summary_failed", rid)
        raise HTTPException(status_code=500, detail="Failed to build schema summary.") from None
