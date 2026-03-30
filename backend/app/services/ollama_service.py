from __future__ import annotations

import os
from typing import Any, Callable, Optional

import httpx
from pydantic import BaseModel, Field, field_validator

from app.services.sql_validator import normalize_readonly_sql, validate_readonly_sql


OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:3b"
PREFERRED_OLLAMA_MODELS = ("qwen2.5-coder:3b", "llama3.2", "qwen3", "phi4", "gemma3")
MAX_SQL_GENERATION_ATTEMPTS = 2
_cached_ollama_model: Optional[str] = None
_env_ollama_model = os.getenv("OLLAMA_MODEL")
if _env_ollama_model:
    _cached_ollama_model = _env_ollama_model


class SQLGenerationResult(BaseModel):
    sql: str = Field(description="A single read-only SQLite SELECT query")
    assumptions: list[str] = Field(
        default_factory=list,
        description="List every meaningful assumption made while generating the query."
    )
    confidence: float = Field(ge=0.0, le=1.0,
        description=(
            "Confidence in the SQL as a numeric score from 0.00 to 1.00, "
            "where higher means the schema match is stronger and the request is less ambiguous."
        )
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: float) -> float:
        if isinstance(value, (int, float)) and 1 < value <= 100:
            return round(value / 100, 2)
        return value



def build_sql_prompt(question: str, schema_summary: str) -> str:
    return f"""
You are a careful SQLite query generator.

Your job:
- Convert the user's question into exactly one SQLite read-only query.
- Only generate SELECT queries or WITH ... SELECT queries.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or PRAGMA.
- Return exactly one SQL statement.
- Do not return multiple statements, comments, markdown fences, prose, or alternative query options.
- Prefer simple, readable SQL.
- Use LIMIT when the user asks for a small number of rows or when browsing data.
- If the question is ambiguous, make the most reasonable assumption and list it in assumptions.
- Output must match the required JSON schema exactly.

Assumptions Rules:
- If the user's wording is ambiguous, list the assumptions you made.
- If you guessed which table, metric, join path, date field, grouping, sort order, or filter to use, include that in assumptions.
- If you had to interpret vague words like "top", "best", "recent", "active", or "sales", include that in assumptions.
- If you choose one reasonable interpretation from several possible ones, assumptions must not be empty.
- If there are no meaningful assumptions, return an empty list.

Confidence rules:
- Confidence must be a numeric value from 0.00 to 1.00.
- Prefer two decimal places, for example 0.34, 0.78, or 0.92.
- Higher confidence means the schema match is direct and the user request is clear.
- Lower confidence means the request is ambiguous or required more assumptions.
- Confidence and assumptions must agree: more or larger assumptions should reduce confidence.

Database schema:
{schema_summary}

User question:
{question}
""".strip()


def build_sql_repair_prompt(
    question: str,
    schema_summary: str,
    previous_result: SQLGenerationResult,
    validation_error: str,
) -> str:
    return f"""
The previous SQL output failed validation.

Validation error:
{validation_error}

You must fix the SQL and return JSON matching the required schema exactly.

Important:
- Return exactly one SQLite read-only statement.
- Do not return multiple statements.
- Do not include comments, markdown fences, prose, or explanation outside the JSON fields.
- Keep the same intent as the original user question.

Database schema:
{schema_summary}

User question:
{question}

Previous JSON output:
{previous_result.model_dump_json()}
""".strip()

async def resolve_ollama_model(client: httpx.AsyncClient) -> Optional[str]:
    global _cached_ollama_model

    if _cached_ollama_model:
        return _cached_ollama_model

    try:
        response = await client.get(OLLAMA_TAGS_URL, timeout=5.0)
        response.raise_for_status()
        models = response.json().get("models", [])
    except httpx.HTTPError:
        _cached_ollama_model = DEFAULT_OLLAMA_MODEL
        return _cached_ollama_model

    available_models = [model.get("name", "") for model in models if model.get("name")]
    for preferred_model in PREFERRED_OLLAMA_MODELS:
        for available_model in available_models:
            if available_model == preferred_model or available_model.startswith(f"{preferred_model}:"):
                _cached_ollama_model = available_model
                return _cached_ollama_model

    _cached_ollama_model = available_models[0] if available_models else DEFAULT_OLLAMA_MODEL
    return _cached_ollama_model


async def _request_sql_generation(
    client: httpx.AsyncClient,
    model: str,
    prompt: str,
) -> SQLGenerationResult:
    payload: dict[str, Any] = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You generate safe SQLite read-only SQL. "
                    "Return only data that matches the provided JSON schema."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "format": SQLGenerationResult.model_json_schema(),
    }
    response = await client.post(OLLAMA_URL, json=payload)
    response.raise_for_status()
    data = response.json()
    content = data["message"]["content"]
    return SQLGenerationResult.model_validate_json(content)


def _normalize_and_verify_generation(
    result: SQLGenerationResult,
    verifier: Callable[[str], None] | None = None,
) -> SQLGenerationResult:
    normalized_sql = normalize_readonly_sql(result.sql.strip())
    validate_readonly_sql(normalized_sql)
    if verifier is not None:
        verifier(normalized_sql)
    return result.model_copy(update={"sql": normalized_sql})


async def generate_sql_from_question(
    question: str,
    schema_summary: str,
    verifier: Callable[[str], None] | None = None,
) -> SQLGenerationResult:
    prompt = build_sql_prompt(question=question, schema_summary=schema_summary)

    async with httpx.AsyncClient(timeout=120.0) as client:
        model = await resolve_ollama_model(client)
        last_error: ValueError | None = None
        for _ in range(MAX_SQL_GENERATION_ATTEMPTS):
            result = await _request_sql_generation(client=client, model=model, prompt=prompt)
            try:
                return _normalize_and_verify_generation(result, verifier=verifier)
            except ValueError as exc:
                last_error = exc
                prompt = build_sql_repair_prompt(
                    question=question,
                    schema_summary=schema_summary,
                    previous_result=result,
                    validation_error=str(exc),
                )

        assert last_error is not None
        raise last_error
