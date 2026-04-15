from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ask_service import ask_question
from app.services.ollama_service import SQLGenerationError, generate_sql_from_question
from app.services.sqlite_service import (
    build_relevant_schema_summary_impl,
    run_sql_readonly_impl,
    validate_sql_compiles_impl,
)
from app.services.sql_validator import validate_readonly_sql

router = APIRouter()
logger = logging.getLogger(__name__)

class GenerateSQLRequest(BaseModel):
    db_filename: str = Field(..., examples=["chinook.sqlite"])
    question: str = Field(..., examples=["Show the top 5 customers by total spending"])

class ExecuteQueryRequest(BaseModel):
    db_filename: str = Field(..., examples=["chinook.sqlite"])
    sql: str
    limit: int = 200

class AskRequest(BaseModel):
    db_filename: str = Field(..., examples=["chinook.sqlite"])
    question: str = Field(..., examples=["Show the top 5 customers by total spending"])
    limit: int = 200


def _format_exception_detail(prefix: str, exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return f"{prefix}: {message}"

@router.post("/generate-sql")
async def generate_sql(payload: GenerateSQLRequest):
    try:
        schema_summary = build_relevant_schema_summary_impl(payload.db_filename, payload.question)

        result = await generate_sql_from_question(
            question=payload.question,
            schema_summary=schema_summary,
            verifier=lambda sql: validate_sql_compiles_impl(payload.db_filename, sql),
        )

        # Validate before returning so the frontend only sees safe SQL proposals
        validate_readonly_sql(result.sql)
        validate_sql_compiles_impl(payload.db_filename, result.sql)

        return {
            "db_filename": payload.db_filename,
            "question": payload.question,
            "schema_summary_used": schema_summary,
            "sql": result.sql,
            "assumptions": result.assumptions,
            "confidence": result.confidence,
        }

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLGenerationError as exc:
        logger.warning(
            "SQL generation failed for db=%s question=%r: %s",
            payload.db_filename,
            payload.question,
            exc,
        )
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        logger.exception(
            "HTTP error during SQL generation for db=%s question=%r",
            payload.db_filename,
            payload.question,
        )
        raise HTTPException(
            status_code=502,
            detail=_format_exception_detail("SQL generation HTTP failure", exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected SQL generation error for db=%s question=%r",
            payload.db_filename,
            payload.question,
        )
        raise HTTPException(
            status_code=500,
            detail=_format_exception_detail("SQL generation failed", exc),
        ) from exc


@router.post("/ask")
async def ask(payload: AskRequest):
    try:
        result = await ask_question(
            question=payload.question,
            db_filename=payload.db_filename,
            limit=payload.limit,
        )

        return {
            "db_filename": payload.db_filename,
            "question": payload.question,
            "sql": result.sql,
            "columns": result.columns,
            "rows": result.rows,
            "row_count": result.row_count,
            "limit_applied": result.limit_applied,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLGenerationError as exc:
        logger.warning(
            "Ask failed during SQL generation for db=%s question=%r: %s",
            payload.db_filename,
            payload.question,
            exc,
        )
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        logger.exception(
            "HTTP error during ask flow for db=%s question=%r",
            payload.db_filename,
            payload.question,
        )
        raise HTTPException(
            status_code=502,
            detail=_format_exception_detail("Ask HTTP failure", exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected ask error for db=%s question=%r",
            payload.db_filename,
            payload.question,
        )
        raise HTTPException(
            status_code=500,
            detail=_format_exception_detail("Ask failed", exc),
        ) from exc


@router.post("/execute")
def execute_query(payload: ExecuteQueryRequest):
    try:
        validate_readonly_sql(payload.sql)
        validate_sql_compiles_impl(payload.db_filename, payload.sql)
        result = run_sql_readonly_impl(
            db_filename=payload.db_filename,
            sql=payload.sql,
            limit=payload.limit,
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Execution failed: {exc}") from exc
