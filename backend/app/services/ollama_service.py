from __future__ import annotations

import json
import os
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field


OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:3b"
PREFERRED_OLLAMA_MODELS = ("qwen2.5-coder:3b", "llama3.2", "qwen3", "phi4", "gemma3")
_cached_ollama_model: Optional[str] = None
_env_ollama_model = os.getenv("OLLAMA_MODEL")
if _env_ollama_model:
    _cached_ollama_model = _env_ollama_model


class SQLGenerationResult(BaseModel):
    sql: str = Field(description="A single read-only SQLite SELECT query")
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


def build_sql_prompt(question: str, schema_summary: str) -> str:
    return f"""
You are a careful SQLite query generator.

Your job:
- Convert the user's question into exactly one SQLite read-only query.
- Only generate SELECT queries or WITH ... SELECT queries.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or PRAGMA.
- Prefer simple, readable SQL.
- Use LIMIT when the user asks for a small number of rows or when browsing data.
- If the question is ambiguous, make the most reasonable assumption and list it in assumptions.
- Output must match the required JSON schema exactly.

Database schema:
{schema_summary}

User question:
{question}
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


async def generate_sql_from_question(question: str, schema_summary: str) -> SQLGenerationResult:
    prompt = build_sql_prompt(question=question, schema_summary=schema_summary)

    async with httpx.AsyncClient(timeout=120.0) as client:
        model = await resolve_ollama_model(client)
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

    # Ollama returns the model output in message.content for /api/chat
    content = data["message"]["content"]

    # Validate the model output against the Pydantic schema
    return SQLGenerationResult.model_validate_json(content)
