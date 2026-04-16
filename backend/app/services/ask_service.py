from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services import gemini_service
from app.services.ollama_service import generate_sql_from_question
from app.services.sqlite_service import (
    build_relevant_schema_summary_impl,
    run_sql_readonly_impl,
    validate_sql_compiles_impl,
)
from app.services.sql_validator import normalize_readonly_sql, validate_readonly_sql


Provider = Literal["auto", "ollama", "gemini"]


class AskResult(BaseModel):
    sql: str
    confidence: float | None = None
    provider: str = "ollama"
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    limit_applied: int | None = None


def verify_sql_compiles_and_executes(db_filename: str, sql: str) -> None:
    validate_sql_compiles_impl(db_filename, sql)
    run_sql_readonly_impl(db_filename=db_filename, sql=sql, limit=1)


async def ask_question(
    question: str,
    db_filename: str,
    limit: int = 200,
    provider: Provider = "auto",
) -> AskResult:
    schema_summary = build_relevant_schema_summary_impl(db_filename, question)

    def verifier(sql: str) -> None:
        verify_sql_compiles_and_executes(db_filename, sql)

    if provider == "gemini":
        if not gemini_service.is_configured():
            raise ValueError(
                "Gemini provider requested but GEMINI_API_KEY is not configured."
            )
        generated = await gemini_service.generate_sql_via_gemini(
            question=question,
            schema_summary=schema_summary,
            verifier=verifier,
        )
        used_provider = "gemini"
    else:
        # "auto" or "ollama": call Ollama; ollama_service falls back to Gemini
        # internally on connection errors when GEMINI_API_KEY is set.
        generated = await generate_sql_from_question(
            question=question,
            schema_summary=schema_summary,
            verifier=verifier,
        )
        used_provider = "ollama"

    sql = normalize_readonly_sql(generated.sql.strip())
    validate_readonly_sql(sql)
    validate_sql_compiles_impl(db_filename, sql)

    query_result = run_sql_readonly_impl(
        db_filename=db_filename,
        sql=sql,
        limit=limit,
    )

    return AskResult(
        sql=sql,
        confidence=generated.confidence,
        provider=used_provider,
        columns=query_result.get("columns", []),
        rows=query_result.get("rows", []),
        row_count=query_result.get("row_count", 0),
        limit_applied=query_result.get("limit_applied"),
    )
