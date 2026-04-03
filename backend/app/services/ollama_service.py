from __future__ import annotations

import json

import os
from typing import Any, Literal, Optional

import httpx
from pydantic import BaseModel, Field, field_validator


OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:3b"
PREFERRED_OLLAMA_MODELS = ("qwen2.5-coder:3b", "llama3.2", "qwen3", "phi4", "gemma3")
_cached_ollama_model: Optional[str] = None
_env_ollama_model = os.getenv("OLLAMA_MODEL")
if _env_ollama_model:
    _cached_ollama_model = _env_ollama_model


class OllamaServiceError(RuntimeError):
    """Raised when Ollama cannot be reached or returns an invalid response."""


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


class AskNextStepResult(BaseModel):
    action: Literal["call_tool", "respond"] = Field(
        description="Choose whether to call one MCP tool next or answer the user directly."
    )
    answer: str = Field(
        default="",
        description="Natural-language answer for the user when action is respond. Otherwise empty.",
    )
    tool_name: str | None = Field(
        default=None,
        description="Exact MCP tool name to call when action is call_tool.",
    )
    tool_arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON arguments for the tool call when action is call_tool.",
    )


class AskDirectQueryResult(BaseModel):
    action: Literal["call_tool", "needs_exploration", "respond"] = Field(
        description="Usually call run_sql_readonly directly. Use needs_exploration only when schema summary is insufficient."
    )
    answer: str = Field(
        default="",
        description="Natural-language answer when action is respond. Otherwise empty.",
    )
    sql: str = Field(
        default="",
        description="SQLite read-only SQL to execute with run_sql_readonly when action is call_tool.",
    )
    rationale: str = Field(
        default="",
        description="Brief explanation of why a direct query is enough or why exploration is needed.",
    )



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


def build_ask_next_step_prompt(
    *,
    question: str,
    db_filename: str,
    limit: int,
    schema_summary: str,
    tool_catalog: str,
    tool_history: list[dict[str, Any]],
) -> str:
    history_json = json_dumps(tool_history)
    return f"""
You are an assistant that can answer database questions by deciding whether to call exactly one MCP tool at a time.

Rules:
- Your available tools are listed below. Only use those exact tool names.
- Prefer tool calls whenever the answer depends on database contents, schema details, or query results.
- You already have a schema summary below. If it is enough to write the SQL, skip schema-discovery tools and call `run_sql_readonly` directly.
- For common analytical questions like "top customers", "total spending", counts, sums, averages, rankings, and grouped reports, prefer a single `run_sql_readonly` call.
- Use `list_tables`, `describe_table`, `get_foreign_keys`, or `sample_rows` only when the schema summary is insufficient or ambiguous.
- If you already have a successful `run_sql_readonly` result in tool history, respond to the user instead of calling another tool.
- If you call `run_sql_readonly`, the SQL must be SQLite read-only SQL and should answer the user's question directly.
- Include `{db_filename}` as `db_filename` for database tools unless it is already present.
- Respect the row limit `{limit}` when using `run_sql_readonly` or `sample_rows`.
- After you have enough tool context, respond in natural language and do not call another tool.
- Never invent tool results.
- Return JSON only and match the required schema exactly.

Database:
{db_filename}

Schema summary:
{schema_summary}

Available tools:
{tool_catalog}

Previous tool history:
{history_json}

User question:
{question}
""".strip()


def build_direct_query_prompt(
    *,
    question: str,
    db_filename: str,
    limit: int,
    schema_summary: str,
) -> str:
    return f"""
You are deciding the fastest safe way to answer a SQLite database question.

Default behavior:
- If the schema summary is enough, write one read-only SQLite query and choose `call_tool`.
- Use `needs_exploration` only if the schema summary is too ambiguous to write a reasonable query.
- Use `respond` only for greetings, meta questions, or cases where no database lookup is needed.

Rules for `call_tool`:
- Produce exactly one SQLite SELECT or WITH ... SELECT query.
- Prefer a single grouped/aggregated query for rankings, totals, counts, averages, trends, and top-N questions.
- Add `LIMIT {limit}` when the user asks for a small number of rows like top 5.
- Do not use schema-discovery tools if the schema summary already shows the needed tables and columns.
- Return SQL only in the `sql` field, not markdown.

Database:
{db_filename}

Schema summary:
{schema_summary}

User question:
{question}
""".strip()


def build_final_answer_prompt(
    *,
    question: str,
    db_filename: str,
    sql: str,
    query_result: dict[str, Any],
) -> str:
    return f"""
You are answering a user about a SQLite database.

Use the executed SQL result below to answer clearly and concisely.
- Do not invent facts not present in the result.
- If rows are empty, say that no matching rows were found.
- Mention the main takeaway first.
- Keep the answer short and natural.

Database:
{db_filename}

User question:
{question}

SQL used:
{sql}

Query result:
{json_dumps(query_result)}
""".strip()


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


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

    try:
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
    except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValueError) as exc:
        raise OllamaServiceError(f"Ollama request failed at {OLLAMA_URL}: {exc}") from exc

    # Ollama returns the model output in message.content for /api/chat
    content = data["message"]["content"]

    # Validate the model output against the Pydantic schema
    try:
        return SQLGenerationResult.model_validate_json(content)
    except ValueError as exc:
        raise OllamaServiceError(f"Ollama returned invalid SQL payload: {exc}") from exc


async def choose_ask_next_step(
    *,
    question: str,
    db_filename: str,
    limit: int,
    schema_summary: str,
    tool_catalog: str,
    tool_history: list[dict[str, Any]],
) -> AskNextStepResult:
    prompt = build_ask_next_step_prompt(
        question=question,
        db_filename=db_filename,
        limit=limit,
        schema_summary=schema_summary,
        tool_catalog=tool_catalog,
        tool_history=tool_history,
    )

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            model = await resolve_ollama_model(client)
            payload: dict[str, Any] = {
                "model": model,
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a cautious database assistant. "
                            "Return only valid JSON that matches the provided schema."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "format": AskNextStepResult.model_json_schema(),
            }
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()

        return AskNextStepResult.model_validate_json(data["message"]["content"])
    except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValueError) as exc:
        raise OllamaServiceError(f"Ollama ask-step request failed at {OLLAMA_URL}: {exc}") from exc


async def choose_direct_query_step(
    *,
    question: str,
    db_filename: str,
    limit: int,
    schema_summary: str,
) -> AskDirectQueryResult:
    prompt = build_direct_query_prompt(
        question=question,
        db_filename=db_filename,
        limit=limit,
        schema_summary=schema_summary,
    )

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            model = await resolve_ollama_model(client)
            payload: dict[str, Any] = {
                "model": model,
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a careful SQLite analyst. "
                            "Prefer a single direct query when possible and return only valid JSON."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "format": AskDirectQueryResult.model_json_schema(),
            }
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()

        return AskDirectQueryResult.model_validate_json(data["message"]["content"])
    except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValueError) as exc:
        raise OllamaServiceError(f"Ollama direct-query request failed at {OLLAMA_URL}: {exc}") from exc


async def summarize_answer_from_query_result(
    *,
    question: str,
    db_filename: str,
    sql: str,
    query_result: dict[str, Any],
) -> str:
    prompt = build_final_answer_prompt(
        question=question,
        db_filename=db_filename,
        sql=sql,
        query_result=query_result,
    )

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            model = await resolve_ollama_model(client)
            payload: dict[str, Any] = {
                "model": model,
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": "You answer using only the provided SQL result context.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            }
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()

        return data["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValueError) as exc:
        raise OllamaServiceError(f"Ollama summarize request failed at {OLLAMA_URL}: {exc}") from exc
