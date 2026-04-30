from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Callable, Optional

import httpx

from app.services.sql_validator import normalize_readonly_sql, validate_readonly_sql
from app.settings import get_settings


logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiNotConfiguredError(RuntimeError):
    pass


class GeminiGenerationError(RuntimeError):
    pass


def get_api_key() -> Optional[str]:
    # Read env directly; .env is loaded via python-dotenv at app startup, so any
    # configured key is present in os.environ. This makes tests deterministic when
    # they call monkeypatch.delenv.
    raw = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if raw is None:
        return None
    cleaned = raw.strip()
    return cleaned or None


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

Text filter and case-sensitivity rules (READ CAREFULLY):
- SQLite's `=`, `IN (...)` and `<>` are case-sensitive on TEXT columns by default.
- The user types in plain English ("red", "active", "us"); their casing rarely matches storage.
- Default for equality / IN filters on a TEXT column: make it case-insensitive.
  - Preferred: `column = 'value' COLLATE NOCASE`
  - Or: `LOWER(column) = LOWER('value')`
  - Or for IN: `LOWER(column) IN ('a','b','c')`
- For LIKE: lowercase the pattern and wrap the column in LOWER, e.g. `LOWER(col) LIKE '%red%'`.
- Only skip case-insensitive treatment when casing is clearly meaningful (codes, hashes, etc.).
- The schema may include "Sample rows (illustrative, not exhaustive)" — use them to see real
  values like "Red" vs "red". Sample rows are not the full dataset, so still apply the
  case-insensitive rule unless the entire sample shows uniform casing.
- Never assume a value exists; if unsure, write the filter case-insensitively and add an
  entry to assumptions.

Sample data:
- A few example rows may appear under each table. Use them to pick correct value spellings
  and to understand the shape of the data, but do NOT assume the rest of the table looks the same.

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
    settings = get_settings()
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    async with httpx.AsyncClient(timeout=settings.gemini_timeout_seconds) as client:
        response = await client.post(
            url,
            headers={"x-goog-api-key": api_key},
            json=payload,
        )
    if response.status_code >= 400:
        # Don't echo upstream body — it may include the prompt verbatim.
        raise GeminiGenerationError(
            f"Gemini API returned HTTP {response.status_code}"
        )
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiGenerationError("Unexpected Gemini response shape") from exc


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

    settings = get_settings()
    selected_model = model or settings.gemini_model
    prompt = _build_prompt(question=question, schema_summary=schema_summary)

    logger.info("Falling back to Gemini model=%s", selected_model)
    raw = await _request_gemini(prompt=prompt, model=selected_model, api_key=api_key)

    try:
        parsed = _extract_json_object(raw)
    except json.JSONDecodeError as exc:
        raise GeminiGenerationError("Gemini did not return valid JSON.") from exc

    try:
        result = SQLGenerationResult.model_validate(parsed)
    except Exception as exc:
        raise GeminiGenerationError("Gemini output failed schema validation.") from exc

    normalized_sql = normalize_readonly_sql(result.sql.strip())
    validate_readonly_sql(normalized_sql)
    if verifier is not None:
        verifier(normalized_sql)
    return result.model_copy(update={"sql": normalized_sql})
