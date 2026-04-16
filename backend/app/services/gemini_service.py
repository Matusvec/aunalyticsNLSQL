from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Callable, Optional

import httpx

from app.services.sql_validator import normalize_readonly_sql, validate_readonly_sql

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TIMEOUT_SECONDS = 60.0


class GeminiNotConfiguredError(RuntimeError):
    pass


class GeminiGenerationError(RuntimeError):
    pass


def get_api_key() -> Optional[str]:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return key.strip() if key else None


def is_configured() -> bool:
    return bool(get_api_key())


def _build_prompt(question: str, schema_summary: str) -> str:
    return f"""You are a careful SQLite query generator.

Convert the user's question into exactly one read-only SQLite query (SELECT or WITH ... SELECT only).
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or PRAGMA.
- Use only tables and columns shown in the schema summary.
- Every alias.column reference must use a real column from that aliased table.
- Prefer LIMIT for browsing queries.
- If the question is ambiguous, pick the most reasonable interpretation and list it in assumptions.

Aggregation rules (critical):
- If the SELECT list mixes aggregate functions (COUNT, SUM, AVG, MIN, MAX) with any non-aggregated column, you MUST add a GROUP BY clause that lists every non-aggregated column.
- "Per X", "by X", "each X" imply GROUP BY X plus an aggregate.
- `SELECT SUM(x) FROM ...` (no non-aggregated columns) returns one row and needs no GROUP BY.
- SQLite will not error without GROUP BY — it will silently return wrong results. Always add it when required.

Ranking direction rules (top vs. bottom — do not confuse):
- "top", "highest", "largest", "most", "best" → `ORDER BY metric DESC LIMIT N`.
- "bottom", "lowest", "smallest", "least", "worst", "fewest" → `ORDER BY metric ASC LIMIT N`.
- Re-read the question before choosing the direction.

Counting vs. listing:
- "How many X" → single-row `SELECT COUNT(...)`.
- "Which X" / "list X" / "show X" → rows themselves.
- "How many X per Y" → `SELECT Y, COUNT(...) ... GROUP BY Y`.

Self-check before answering:
1. If SELECT mixes aggregates and bare columns, is there a GROUP BY covering every bare column?
2. Does the ORDER BY direction (ASC/DESC) match what the user asked for?
3. Is every alias.column a real column on that alias's exact table?

Respond with JSON ONLY (no markdown fences, no prose) in this exact shape:
{{"sql": "<single SQLite SELECT statement>",
  "assumptions": ["<assumption 1>", "..."],
  "confidence": <float between 0.0 and 1.0>}}

Database schema:
{schema_summary}

User question:
{question}
"""


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", stripped, flags=re.DOTALL)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(stripped)
        if not match:
            raise
        return json.loads(match.group(0))


async def _request_gemini(prompt: str, model: str, api_key: str) -> str:
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    async with httpx.AsyncClient(timeout=GEMINI_TIMEOUT_SECONDS) as client:
        response = await client.post(
            url,
            headers={"x-goog-api-key": api_key},
            json=payload,
        )
    if response.status_code >= 400:
        raise GeminiGenerationError(
            f"Gemini API returned {response.status_code}: {response.text[:300]}"
        )
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiGenerationError(f"Unexpected Gemini response shape: {data}") from exc


async def generate_sql_via_gemini(
    question: str,
    schema_summary: str,
    verifier: Callable[[str], None] | None = None,
    model: Optional[str] = None,
):
    from app.services.ollama_service import SQLGenerationResult

    api_key = get_api_key()
    if not api_key:
        raise GeminiNotConfiguredError(
            "GEMINI_API_KEY is not set; cannot fall back to Gemini."
        )

    selected_model = model or os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    prompt = _build_prompt(question=question, schema_summary=schema_summary)

    logger.info("Falling back to Gemini model=%s", selected_model)
    raw = await _request_gemini(prompt=prompt, model=selected_model, api_key=api_key)

    try:
        parsed = _extract_json_object(raw)
    except json.JSONDecodeError as exc:
        raise GeminiGenerationError(f"Gemini did not return valid JSON: {raw[:300]}") from exc

    try:
        result = SQLGenerationResult.model_validate(parsed)
    except Exception as exc:
        raise GeminiGenerationError(f"Gemini output failed schema validation: {exc}") from exc

    normalized_sql = normalize_readonly_sql(result.sql.strip())
    validate_readonly_sql(normalized_sql)
    if verifier is not None:
        verifier(normalized_sql)
    return result.model_copy(update={"sql": normalized_sql})
