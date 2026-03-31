from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.sqlite_service import list_tables_impl, describe_table_impl, build_schema_summary_impl

router = APIRouter()


@router.get("/schema/{db_filename}")
def get_schema(db_filename: str):
    try:
        tables = list_tables_impl(db_filename)
        return {
            "database": db_filename,
            "tables": [describe_table_impl(db_filename, t) for t in tables],
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load schema: {exc}") from exc
    
@router.get("/schema-summary/{db_filename}")
def get_schema_summary(db_filename: str):
    try:
        return {
            "database": db_filename,
            "schema_summary": build_schema_summary_impl(db_filename),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to build schema summary: {exc}") from exc
