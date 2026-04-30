from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field

from app.services import gemini_agent, gemini_service
from app.services.ollama_service import (
    SQLGenerationError,
    generate_sql_from_question,
)
from app.services.sqlite_service import (
    build_relevant_schema_summary,
    run_sql_readonly,
    run_sql_readonly_impl,
    validate_sql_compiles,
    validate_sql_compiles_impl,
)
from app.services.sql_validator import normalize_readonly_sql, validate_readonly_sql
from app.settings import get_settings


logger = logging.getLogger(__name__)


EmitFn = Callable[[dict[str, Any]], Awaitable[None]]


class AskResult(BaseModel):
    sql: str
    confidence: float | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    limit_applied: int | None = None
    tier: str | None = None
    assumptions: list[str] = Field(default_factory=list)


def verify_sql_compiles_and_executes(db_filename: str, sql: str) -> None:
    """Sync verifier passed to LLM repair loops. Runs inside asyncio.to_thread."""
    validate_sql_compiles_impl(db_filename, sql)
    run_sql_readonly_impl(db_filename=db_filename, sql=sql, limit=1)


async def ask_question(
    question: str,
    db_filename: str,
    limit: int = 200,
    tier: str | None = None,
    emit: EmitFn | None = None,
) -> AskResult:
    settings = get_settings()

    def verifier(sql: str) -> None:
        verify_sql_compiles_and_executes(db_filename, sql)

    use_agent = settings.llm_use_tools and gemini_service.is_configured()
    tier_resolved = gemini_agent.resolve_tier(tier).name if use_agent else None
    assumptions: list[str] = []

    if use_agent:
        logger.info("ask_question: using Gemini tool-calling agent (tier=%s)", tier_resolved)
        try:
            generated = await gemini_agent.generate_sql_with_tools(
                question=question,
                db_filename=db_filename,
                verifier=verifier,
                tier=tier_resolved,
                emit=emit,
            )
        except gemini_service.GeminiNotConfiguredError:
            logger.warning("Gemini agent unavailable mid-flight; falling back to static schema flow")
            generated = await _static_schema_flow(question, db_filename, verifier)
        assumptions = list(getattr(generated, "assumptions", []) or [])
    else:
        generated = await _static_schema_flow(question, db_filename, verifier)
        assumptions = list(getattr(generated, "assumptions", []) or [])

    sql = normalize_readonly_sql(generated.sql.strip())
    validate_readonly_sql(sql)
    await validate_sql_compiles(db_filename, sql)

    query_result = await run_sql_readonly(
        db_filename=db_filename,
        sql=sql,
        limit=limit,
    )

    return AskResult(
        sql=sql,
        confidence=generated.confidence,
        columns=query_result.get("columns", []),
        rows=query_result.get("rows", []),
        row_count=query_result.get("row_count", 0),
        limit_applied=query_result.get("limit_applied"),
        tier=tier_resolved,
        assumptions=assumptions,
    )


async def _static_schema_flow(question: str, db_filename: str, verifier):
    schema_summary = await build_relevant_schema_summary(db_filename, question)
    return await generate_sql_from_question(
        question=question,
        schema_summary=schema_summary,
        verifier=verifier,
    )


__all__ = ["AskResult", "ask_question", "SQLGenerationError"]
