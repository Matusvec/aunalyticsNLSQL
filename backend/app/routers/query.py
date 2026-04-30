from __future__ import annotations

import asyncio
import json
import logging

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.rate_limit import rate
from app.services import gemini_agent
from app.services.ask_service import ask_question
from app.services.history_service import (
    get_recent_history_async,
    log_successful_query_async,
)
from app.services.ollama_service import SQLGenerationError, generate_sql_from_question
from app.services.sqlite_service import (
    SQLExecutionTimeout,
    build_relevant_schema_summary,
    run_sql_readonly,
    validate_sql_compiles,
)
from app.services.sql_validator import validate_readonly_sql
from app.settings import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)
_settings = get_settings()


class GenerateSQLRequest(BaseModel):
    db_filename: str = Field(..., examples=["chinook.sqlite"])
    question: str = Field(..., min_length=1, max_length=2000, examples=["Show the top 5 customers by total spending"])


class ExecuteQueryRequest(BaseModel):
    db_filename: str = Field(..., examples=["chinook.sqlite"])
    sql: str = Field(..., min_length=1, max_length=20_000)
    limit: int = Field(default=200, ge=1, le=1000)


class AskRequest(BaseModel):
    db_filename: str = Field(..., examples=["chinook.sqlite"])
    question: str = Field(..., min_length=1, max_length=2000, examples=["Show the top 5 customers by total spending"])
    limit: int = Field(default=200, ge=1, le=1000)
    tier: str | None = Field(default=None, description="fast | medium | high")


def _request_id(request: Request | None) -> str:
    if request is None:
        return "-"
    rid = getattr(request.state, "request_id", None)
    return rid if isinstance(rid, str) else "-"


@router.post("/generate-sql")
@rate(_settings.rate_limit_ask)
async def generate_sql(request: Request, payload: GenerateSQLRequest):
    rid = _request_id(request)
    try:
        schema_summary = await build_relevant_schema_summary(
            payload.db_filename, payload.question
        )

        result = await generate_sql_from_question(
            question=payload.question,
            schema_summary=schema_summary,
            verifier=None,  # Verifier is the heavy validator + executor below.
        )

        validate_readonly_sql(result.sql)
        await validate_sql_compiles(payload.db_filename, result.sql)

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
    except (ValueError, SQLExecutionTimeout) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLGenerationError as exc:
        logger.warning("rid=%s sql_generation_failed: %s", rid, exc)
        raise HTTPException(status_code=504, detail="SQL generation failed or timed out.") from exc
    except httpx.HTTPError as exc:
        logger.exception("rid=%s sql_generation_http_error", rid)
        raise HTTPException(status_code=502, detail="Upstream LLM service unavailable.") from exc
    except Exception:
        logger.exception("rid=%s sql_generation_unexpected_error", rid)
        raise HTTPException(status_code=500, detail="Internal server error.") from None


@router.post("/ask")
@rate(_settings.rate_limit_ask)
async def ask(request: Request, payload: AskRequest):
    rid = _request_id(request)
    try:
        result = await ask_question(
            question=payload.question,
            db_filename=payload.db_filename,
            limit=payload.limit,
            tier=payload.tier,
        )
        await log_successful_query_async(
            question=payload.question,
            sql=result.sql,
            confidence=result.confidence,
        )

        return {
            "db_filename": payload.db_filename,
            "question": payload.question,
            "sql": result.sql,
            "columns": result.columns,
            "rows": result.rows,
            "row_count": result.row_count,
            "limit_applied": result.limit_applied,
            "tier": result.tier,
            "assumptions": result.assumptions,
            "confidence": result.confidence,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLExecutionTimeout as exc:
        logger.warning("rid=%s sql_timeout: %s", rid, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLGenerationError as exc:
        logger.warning("rid=%s ask_sql_generation_failed: %s", rid, exc)
        raise HTTPException(status_code=504, detail="SQL generation failed or timed out.") from exc
    except httpx.HTTPError as exc:
        logger.exception("rid=%s ask_http_error", rid)
        raise HTTPException(status_code=502, detail="Upstream LLM service unavailable.") from exc
    except Exception:
        logger.exception("rid=%s ask_unexpected_error", rid)
        raise HTTPException(status_code=500, detail="Internal server error.") from None


@router.post("/ask/stream")
@rate(_settings.rate_limit_ask)
async def ask_stream(request: Request, payload: AskRequest):
    """Stream the agent's tool trace + final result as Server-Sent Events.

    Each event is a single line: `data: {...json...}\\n\\n`.
    Event `type` field values:
      - start: agent is starting; includes tier, max_iterations, max_submit_retries
      - brief: the database brief sent to the LLM
      - iteration: a new agent iteration is starting
      - tool_call: model called a tool; includes name + args
      - tool_result: tool returned; includes a short summary (not the full payload)
      - submit_failed: submit_sql validation failed; agent will retry
      - submit_ok: agent submitted SQL that passed validation
      - model_text: the model emitted plain text (sometimes accompanies a tool call)
      - final: the question is fully answered; includes rows + columns + sql
      - error: agent or backend failure; terminates the stream
    """
    rid = _request_id(request)

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()

        async def emit(event: dict) -> None:
            await queue.put(event)

        async def runner() -> None:
            try:
                await emit({"type": "request_id", "request_id": rid})
                result = await ask_question(
                    question=payload.question,
                    db_filename=payload.db_filename,
                    limit=payload.limit,
                    tier=payload.tier,
                    emit=emit,
                )
                # Best-effort log to the history table.
                try:
                    await log_successful_query_async(
                        question=payload.question,
                        sql=result.sql,
                        confidence=result.confidence,
                    )
                except Exception:
                    logger.exception("rid=%s history_log_failed", rid)

                await emit(
                    {
                        "type": "final",
                        "db_filename": payload.db_filename,
                        "question": payload.question,
                        "sql": result.sql,
                        "columns": result.columns,
                        "rows": result.rows,
                        "row_count": result.row_count,
                        "limit_applied": result.limit_applied,
                        "tier": result.tier,
                        "assumptions": result.assumptions,
                        "confidence": result.confidence,
                    }
                )
            except FileNotFoundError as exc:
                await emit({"type": "error", "status": 404, "detail": str(exc)})
            except SQLExecutionTimeout as exc:
                await emit({"type": "error", "status": 400, "detail": str(exc)})
            except ValueError as exc:
                await emit({"type": "error", "status": 400, "detail": str(exc)})
            except SQLGenerationError as exc:
                logger.warning("rid=%s stream_sql_generation_failed: %s", rid, exc)
                await emit({"type": "error", "status": 504, "detail": str(exc)})
            except Exception:
                logger.exception("rid=%s stream_unexpected_error", rid)
                await emit({"type": "error", "status": 500, "detail": "Internal server error."})
            finally:
                await queue.put(None)  # sentinel

        task = asyncio.create_task(runner())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item, default=str)}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/agent/tiers")
def list_agent_tiers():
    """Return the available agent tiers and their parameters."""
    return {
        "default": gemini_agent.DEFAULT_TIER,
        "tiers": [
            {
                "name": t.name,
                "max_iterations": t.max_iterations,
                "max_submit_retries": t.max_submit_retries,
                "description": t.description,
            }
            for t in gemini_agent.TIERS.values()
        ],
    }


@router.get("/history")
async def get_history(request: Request):
    rid = _request_id(request)
    try:
        return {"items": await get_recent_history_async(limit=50)}
    except Exception:
        logger.exception("rid=%s history_load_failed", rid)
        raise HTTPException(status_code=500, detail="Failed to load history.") from None


@router.post("/execute")
@rate(_settings.rate_limit_execute)
async def execute_query(request: Request, payload: ExecuteQueryRequest):
    rid = _request_id(request)
    try:
        validate_readonly_sql(payload.sql)
        await validate_sql_compiles(payload.db_filename, payload.sql)
        return await run_sql_readonly(
            db_filename=payload.db_filename,
            sql=payload.sql,
            limit=payload.limit,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLExecutionTimeout as exc:
        logger.warning("rid=%s execute_timeout: %s", rid, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("rid=%s execute_unexpected_error", rid)
        raise HTTPException(status_code=500, detail="Internal server error.") from None
