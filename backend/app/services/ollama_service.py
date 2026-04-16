from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Callable, Optional

import httpx
from pydantic import BaseModel, Field, field_validator

from app.services.sql_validator import normalize_readonly_sql, validate_readonly_sql


OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:3b"
PREFERRED_OLLAMA_MODELS = ("qwen2.5-coder:3b", "phi3", "qwen3", "llama3.2", "gemma3")
SQL_GENERATION_ATTEMPT_TIMEOUTS_SECONDS = (45.0, 180.0)
MAX_SQL_GENERATION_ATTEMPTS = 2
logger = logging.getLogger(__name__)
ALIASED_COLUMN_ERROR_RE = re.compile(r"no such column:\s*([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
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


class SQLGenerationAttempt(BaseModel):
    attempt_number: int
    previous_sql: str
    error: str


class SQLGenerationError(RuntimeError):
    pass

def build_sql_prompt(question: str, schema_summary: str) -> str:
    return f"""
You are a careful SQLite query generator.

Your job:
- Convert the user's question into exactly one SQLite read-only query.
- Only generate SELECT queries or WITH ... SELECT queries.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or PRAGMA.
- Return exactly one SQL statement.
- Use only tables and columns shown in the schema summary.
- If a table name is not listed in the schema summary, it does not exist.
- Table aliases do not create new columns.
- Every alias.column reference must use a real column from the aliased table.
- Do not return multiple statements, comments, markdown fences, prose, or alternative query options.
- Prefer simple, readable SQL.
- Prefer a single SELECT with explicit JOIN clauses over a CTE when both are valid.
- Prefer short table aliases when they improve readability.
- Format SQL clearly with one major clause per line and one JOIN per line.
- Put ORDER BY before LIMIT.
- Use LIMIT when the user asks for a small number of rows or when browsing data.
- If the question is ambiguous, make the most reasonable assumption and list it in assumptions.
- Output must match the required JSON schema exactly.

Preferred style example:
SELECT
    c.CustomerId,
    c.FirstName || ' ' || c.LastName AS CustomerName,
    c.Country,
    SUM(ii.UnitPrice * ii.Quantity) AS TotalSpentOnRock,
    SUM(ii.Quantity) AS RockTracksPurchased
FROM customers c
JOIN invoices i
    ON c.CustomerId = i.CustomerId
JOIN invoice_items ii
    ON i.InvoiceId = ii.InvoiceId
JOIN tracks t
    ON ii.TrackId = t.TrackId
ORDER BY TotalSpentOnRock DESC
LIMIT 5

Strict alias and column rules:
- Each alias must refer to exactly one table from the FROM or JOIN clause.
- Each alias.column reference must use a real column from that alias's exact table only.
- Never invent columns, even if a name seems likely.
- Never borrow a column from a different joined table.
- SELECT aliases are not source columns and cannot be used as if they belong to a table.
- Before outputting SQL, validate every alias.column reference against the schema summary.
- If a referenced column does not exist on that aliased table, rewrite the query or choose a different join path. Never guess.

Aggregation rules (critical — most common mistake):
- If the SELECT list contains any aggregate function (COUNT, SUM, AVG, MIN, MAX) AND any non-aggregated column, you MUST add a GROUP BY clause that lists every non-aggregated column.
- Examples:
    - `SELECT c.CustomerId, SUM(x) FROM ...` is WRONG without `GROUP BY c.CustomerId`. Add the GROUP BY.
    - `SELECT c.CustomerId, c.FirstName, c.LastName, SUM(x) FROM ...` requires `GROUP BY c.CustomerId, c.FirstName, c.LastName`.
    - `SELECT SUM(x) FROM ...` (no non-aggregated columns) needs no GROUP BY — it returns one row.
- "Per customer", "per country", "by genre", "each X" all imply GROUP BY on that column plus an aggregate.
- Never omit GROUP BY just because the query looks simple. SQLite will not error without it — it will silently return wrong results.

Ranking direction rules (top vs. bottom — do not confuse):
- "top N", "highest", "largest", "most", "best", "greatest" → `ORDER BY metric DESC LIMIT N`.
- "bottom N", "lowest", "smallest", "least", "worst", "fewest" → `ORDER BY metric ASC LIMIT N`.
- Re-read the user's question before choosing the direction. Getting ASC vs. DESC wrong gives the opposite of what the user asked for.

Counting vs. listing:
- "How many X" → `SELECT COUNT(...)` returning a single number.
- "Which X" / "list X" / "show X" → return the rows themselves, not a count.
- "How many X per Y" needs `SELECT Y, COUNT(...) ... GROUP BY Y`.

Counting the RIGHT table (common mistake with category words):
- Identify the noun the user is counting (tracks, customers, invoices, orders). That noun's table is the FROM table.
- Filter words (by genre, in country X, from year Y) describe a JOIN or WHERE, not the FROM table.
- Examples of the right shape:
    - "How many tracks are in the Rock genre?"
      → `SELECT COUNT(*) FROM tracks t JOIN genres g ON t.GenreId = g.GenreId WHERE g.Name = 'Rock'`
      → NOT `SELECT COUNT(*) FROM genres WHERE Name = 'Rock'` (that counts genre rows, always 1).
    - "How many customers are in the USA?"
      → `SELECT COUNT(*) FROM customers WHERE Country = 'USA'`
    - "How many albums does Iron Maiden have?"
      → `SELECT COUNT(*) FROM albums al JOIN artists ar ON al.ArtistId = ar.ArtistId WHERE ar.Name = 'Iron Maiden'`
- If the counted noun and the filter noun live in different tables, the query MUST join them.

Self-check before outputting:
1. Does the SELECT list mix aggregates and bare columns? If yes, is there a GROUP BY covering every bare column? If no, add one.
2. Does "top" / "bottom" (or synonyms) in the question match the ORDER BY direction? If no, flip it.
3. Does every `alias.column` reference a real column from that alias's exact table? If no, fix or choose a different join.

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


def format_attempt_feedback(attempt: SQLGenerationAttempt) -> str:
    parts = [f"Attempt {attempt.attempt_number} failed."]
    if attempt.previous_sql:
        parts.append(f"Last SQL: {attempt.previous_sql}")
    parts.append(f"Error: {attempt.error}")
    return "\n".join(parts)


def build_sql_repair_prompt(
    question: str,
    schema_summary: str,
    attempt_feedback: SQLGenerationAttempt,
) -> str:
    error_guidance = build_error_specific_guidance(attempt_feedback.error)
    return f"""
Fix the failed SQL and return JSON matching the required schema exactly.

{format_attempt_feedback(attempt_feedback)}

{error_guidance}

Important:
- Return exactly one SQLite read-only statement.
- Keep the same intent as the user question.
- Use only tables and columns shown in the schema summary.
- Correct the specific mistake shown in the error.
- Do not repeat the same failure.
- Take enough time to verify table names, aliases, and column names against the schema summary before answering.
- Prefer a single SELECT with explicit JOIN clauses over a CTE when both are valid.
- Keep the SQL readable and well-structured, with one JOIN per line and ORDER BY before LIMIT.

Database schema:
{schema_summary}

User question:
{question}
""".strip()


def build_error_specific_guidance(error_message: str) -> str:
    match = ALIASED_COLUMN_ERROR_RE.search(error_message)
    if not match:
        return "Failure-specific guidance:\n- Use only real table and column names from the schema summary."

    alias_name, column_name = match.groups()
    return (
        "Failure-specific guidance:\n"
        f"- `{alias_name}.{column_name}` is invalid.\n"
        "- A table alias does not create or rename columns.\n"
        "- If you use an alias, every `alias.column` reference must map to a real column on that table.\n"
        "- Re-check the schema summary and replace the bad alias column with a real column name."
    )

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
    timeout_seconds: float,
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
    response = await client.post(
        OLLAMA_URL,
        json=payload,
        timeout=timeout_seconds,
    )
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

async def _try_gemini_fallback(
    question: str,
    schema_summary: str,
    verifier: Callable[[str], None] | None,
    reason: str,
) -> Optional["SQLGenerationResult"]:
    """Return a Gemini-generated result, or None if Gemini is not configured/reachable."""
    from app.services import gemini_service

    if not gemini_service.is_configured():
        logger.info("Gemini fallback skipped (%s): GEMINI_API_KEY not set", reason)
        return None
    try:
        logger.warning("Ollama unavailable (%s); attempting Gemini fallback", reason)
        return await gemini_service.generate_sql_via_gemini(
            question=question,
            schema_summary=schema_summary,
            verifier=verifier,
        )
    except Exception:
        logger.exception("Gemini fallback also failed")
        return None


async def generate_sql_from_question(
    question: str,
    schema_summary: str,
    verifier: Callable[[str], None] | None = None,
) -> SQLGenerationResult:
    prompt = build_sql_prompt(question=question, schema_summary=schema_summary)

    async with httpx.AsyncClient(timeout=max(SQL_GENERATION_ATTEMPT_TIMEOUTS_SECONDS)) as client:
        try:
            model = await resolve_ollama_model(client)
        except httpx.ConnectError as exc:
            fallback = await _try_gemini_fallback(
                question=question,
                schema_summary=schema_summary,
                verifier=verifier,
                reason=f"connect error resolving model: {exc}",
            )
            if fallback is not None:
                return fallback
            raise SQLGenerationError(
                "Ollama is unreachable and no Gemini fallback is configured."
            ) from exc

        last_error: ValueError | None = None
        for attempt_number in range(1, MAX_SQL_GENERATION_ATTEMPTS + 1):
            attempt_started = time.perf_counter()
            timeout_seconds = SQL_GENERATION_ATTEMPT_TIMEOUTS_SECONDS[attempt_number - 1]
            try:
                result = await _request_sql_generation(
                    client=client,
                    model=model,
                    prompt=prompt,
                    timeout_seconds=timeout_seconds,
                )
            except httpx.ConnectError as exc:
                fallback = await _try_gemini_fallback(
                    question=question,
                    schema_summary=schema_summary,
                    verifier=verifier,
                    reason=f"connect error on attempt {attempt_number}: {exc}",
                )
                if fallback is not None:
                    return fallback
                raise SQLGenerationError(
                    "Ollama is unreachable and no Gemini fallback is configured."
                ) from exc
            except httpx.TimeoutException as exc:
                elapsed_seconds = time.perf_counter() - attempt_started
                logger.warning(
                    "SQL generation timed out on attempt %s/%s after %.2fs for question=%r",
                    attempt_number,
                    MAX_SQL_GENERATION_ATTEMPTS,
                    elapsed_seconds,
                    question,
                )
                if attempt_number == MAX_SQL_GENERATION_ATTEMPTS:
                    raise SQLGenerationError(
                        "SQL generation timed out after "
                        f"{timeout_seconds:.0f}s on attempt "
                        f"{attempt_number} of {MAX_SQL_GENERATION_ATTEMPTS}"
                    ) from exc
                prompt = build_sql_repair_prompt(
                    question=question,
                    schema_summary=schema_summary,
                    attempt_feedback=SQLGenerationAttempt(
                        attempt_number=attempt_number,
                        previous_sql="",
                        error=f"Timed out after {timeout_seconds:.0f}s before producing SQL",
                    ),
                )
                continue
            except httpx.HTTPError as exc:
                elapsed_seconds = time.perf_counter() - attempt_started
                logger.exception(
                    "SQL generation HTTP error on attempt %s/%s after %.2fs for question=%r",
                    attempt_number,
                    MAX_SQL_GENERATION_ATTEMPTS,
                    elapsed_seconds,
                    question,
                )
                message = str(exc).strip() or exc.__class__.__name__
                raise SQLGenerationError(
                    "SQL generation request failed on attempt "
                    f"{attempt_number} of {MAX_SQL_GENERATION_ATTEMPTS}: {message}"
                ) from exc
            try:
                return _normalize_and_verify_generation(result, verifier=verifier)
            except ValueError as exc:
                elapsed_seconds = time.perf_counter() - attempt_started
                last_error = exc
                logger.info(
                    "SQL generation attempt %s/%s failed verification after %.2fs for question=%r: %s",
                    attempt_number,
                    MAX_SQL_GENERATION_ATTEMPTS,
                    elapsed_seconds,
                    question,
                    exc,
                )
                prompt = build_sql_repair_prompt(
                    question=question,
                    schema_summary=schema_summary,
                    attempt_feedback=SQLGenerationAttempt(
                        attempt_number=attempt_number,
                        previous_sql=result.sql.strip(),
                        error=str(exc),
                    ),
                )

        assert last_error is not None
        raise last_error
