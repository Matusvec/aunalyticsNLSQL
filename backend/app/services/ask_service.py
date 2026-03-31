from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.services.ollama_service import generate_sql_from_question
from app.services.sqlite_service import (
    build_schema_summary_impl,
    run_sql_readonly_impl,
    validate_sql_compiles_impl,
)
from app.services.sql_validator import normalize_readonly_sql, validate_readonly_sql


class AskResult(BaseModel):
    sql: str
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    limit_applied: int | None = None


async def ask_question(question: str, db_filename: str, limit: int = 200) -> AskResult:
    schema_summary = build_schema_summary_impl(db_filename)

    generated = await generate_sql_from_question(
        question=question,
        schema_summary=schema_summary,
        verifier=lambda sql: validate_sql_compiles_impl(db_filename, sql),
    )
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
        columns=query_result.get("columns", []),
        rows=query_result.get("rows", []),
        row_count=query_result.get("row_count", 0),
        limit_applied=query_result.get("limit_applied"),
    )
