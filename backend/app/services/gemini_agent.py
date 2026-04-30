"""Tool-calling SQL agent backed by Gemini.

The agent receives an upfront database brief (table names + column types + row counts)
and a toolbox to probe further. It loops, calling tools, until it submits a final SQL
via `submit_sql`. If the submitted SQL fails validation, the error is fed back as a tool
response so the model can self-correct.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import httpx

from app.services.gemini_service import (
    GEMINI_API_BASE,
    GeminiGenerationError,
    GeminiNotConfiguredError,
    get_api_key,
)
from app.services.sql_validator import normalize_readonly_sql, validate_readonly_sql
from app.services.sqlite_service import (
    SQLExecutionTimeout,
    _quote_identifier,
    _readonly_connection,
    describe_table_impl,
    list_tables_impl,
    run_sql_readonly_impl,
)
from app.settings import get_settings


logger = logging.getLogger(__name__)


EmitFn = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class TierConfig:
    name: str
    max_iterations: int
    max_submit_retries: int
    prompt_addendum: str
    description: str


TIERS: dict[str, TierConfig] = {
    "fast": TierConfig(
        name="fast",
        max_iterations=3,
        max_submit_retries=1,
        prompt_addendum=(
            "TIER: FAST. Use the brief plus at most 1-2 tool calls, then submit. "
            "Make reasonable assumptions instead of probing every uncertainty. "
            "Prefer a slightly less-optimal SQL over more tool calls."
        ),
        description="1–2 tool calls. Cheapest, least accurate.",
    ),
    "medium": TierConfig(
        name="medium",
        max_iterations=6,
        max_submit_retries=2,
        prompt_addendum="TIER: MEDIUM. Probe what is uncertain, then submit. Default behavior.",
        description="Up to ~5 tool calls. Balanced.",
    ),
    "high": TierConfig(
        name="high",
        max_iterations=12,
        max_submit_retries=4,
        prompt_addendum=(
            "TIER: HIGH. Be thorough. Always verify text-column casing with distinct_values "
            "before filtering on it. Use find_related to confirm join paths. Test complex joins "
            "with run_query before calling submit_sql. Spending a few extra tool calls is fine."
        ),
        description="Up to ~10 tool calls + run_query verification. Most accurate, most expensive.",
    ),
}

DEFAULT_TIER = "medium"


def resolve_tier(name: str | None) -> TierConfig:
    if not name:
        return TIERS[DEFAULT_TIER]
    if name in TIERS:
        return TIERS[name]
    return TIERS[DEFAULT_TIER]


async def _noop_emit(_: dict[str, Any]) -> None:
    return None


SYSTEM_PROMPT = """You are an expert SQL agent that converts natural-language questions into safe read-only SQLite queries.

You will be shown an upfront database brief (table list with columns and row counts).
Use the toolbox below to dig deeper before answering. The brief gets you started; the tools
let you confirm anything uncertain.

Toolbox:
- list_tables() — full table list (already in the brief; rarely needed).
- describe_table(table) — columns, types, primary keys.
- sample_rows(table, limit=5) — peek at real rows so you know how values are stored.
- distinct_values(table, column) — top 50 distinct values with counts. Best tool for
  seeing categorical values like "Red"/"Green" or "active"/"inactive".
- count_rows(table) — total rows in a table.
- find_related(table) — foreign keys defined on the table. Use to discover JOIN paths.
- search_value(value, table?) — find which TEXT columns contain a substring (case-insensitive).
  Use when the user says a value but you don't know what column it's stored in.
- run_query(sql) — execute an exploratory read-only SELECT (returns up to 20 rows). Use this
  to test joins, aggregations, or filters before committing to a final answer.
- submit_sql(sql, assumptions, confidence) — submit your final answer. The pipeline will
  validate, compile, and execute it. If validation fails you'll get the error back and can
  call submit_sql again with a fix.

When to probe:
- Always call distinct_values or sample_rows for any text column you filter on.
- Call find_related when joining tables you haven't seen the FKs of.
- Call run_query whenever you're uncertain — testing is cheap.

SQL rules for the value you submit:
- Only SELECT or WITH ... SELECT.
- Use only real tables and columns you have observed via tools.
- For text equality / IN / LIKE filters, default to case-insensitive: `column = 'value' COLLATE NOCASE`
  or `LOWER(column) = LOWER('value')`. Skip only when casing is meaningful (codes, hashes).
- One SQL statement only — no comments, no markdown fences, no prose.
- Format SQL clearly with one major clause per line and one JOIN per line.
- Put ORDER BY before LIMIT.
"""


# Gemini's tool schema is a subset of OpenAPI. Stick to types it accepts.
TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "list_tables",
        "description": "List all user tables. The brief already includes them; only use this if you suspect the brief is stale.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "describe_table",
        "description": "Get the columns of a table including type, NOT NULL, default, and primary-key flag.",
        "parameters": {
            "type": "object",
            "properties": {"table": {"type": "string"}},
            "required": ["table"],
        },
    },
    {
        "name": "sample_rows",
        "description": "Return up to `limit` (default 5, max 20) example rows from a table to see how values look.",
        "parameters": {
            "type": "object",
            "properties": {
                "table": {"type": "string"},
                "limit": {"type": "integer", "description": "1 to 20. Default 5."},
            },
            "required": ["table"],
        },
    },
    {
        "name": "distinct_values",
        "description": "Return up to 50 distinct values of a column with their occurrence counts. Best tool for inspecting categorical text columns.",
        "parameters": {
            "type": "object",
            "properties": {
                "table": {"type": "string"},
                "column": {"type": "string"},
            },
            "required": ["table", "column"],
        },
    },
    {
        "name": "count_rows",
        "description": "Total number of rows in a table.",
        "parameters": {
            "type": "object",
            "properties": {"table": {"type": "string"}},
            "required": ["table"],
        },
    },
    {
        "name": "find_related",
        "description": "Show foreign keys defined on a table — use this to discover how to join to related tables.",
        "parameters": {
            "type": "object",
            "properties": {"table": {"type": "string"}},
            "required": ["table"],
        },
    },
    {
        "name": "search_value",
        "description": (
            "Search for a value (substring, case-insensitive) across all TEXT columns of every table, "
            "or just the given table. Returns matching {table, column, value, count} rows. "
            "Use this when the user mentions a value (e.g. 'red apples') but you don't know which column holds it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "table": {"type": "string", "description": "Optional. Restrict the search to one table."},
            },
            "required": ["value"],
        },
    },
    {
        "name": "run_query",
        "description": (
            "Run an exploratory read-only SELECT (or WITH ... SELECT) and return up to 20 rows. "
            "Same validation as the final answer; same security. Use this to test joins, aggregations, or "
            "filters before committing to a final answer."
        ),
        "parameters": {
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
        },
    },
    {
        "name": "submit_sql",
        "description": (
            "Submit your final SQL. Pipeline will validate, compile, and execute it. "
            "If validation fails, the error is returned to you and you may call submit_sql again with a fix."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string"},
                "assumptions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Meaningful assumptions you made.",
                },
                "confidence": {
                    "type": "number",
                    "description": "0.0 to 1.0. Lower means more guesswork.",
                },
            },
            "required": ["sql", "confidence"],
        },
    },
]


# ---------------------------------------------------------------------------
# Database brief
# ---------------------------------------------------------------------------


def _safe_count_rows(db_filename: str, table: str) -> int | None:
    try:
        quoted = _quote_identifier(table)
        result = run_sql_readonly_impl(
            db_filename, f"SELECT COUNT(*) AS n FROM {quoted}", limit=1
        )
        return int(result["rows"][0]["n"])
    except Exception:
        return None


def _build_database_brief(db_filename: str) -> str:
    """One-shot inventory of every table — always included in the initial prompt."""
    try:
        tables = list_tables_impl(db_filename)
    except Exception as exc:
        return f"# Database brief unavailable: {exc.__class__.__name__}"

    lines: list[str] = [
        f"# Database brief",
        f"file: {db_filename} · {len(tables)} table{'' if len(tables) == 1 else 's'}",
        "",
    ]
    for table in tables:
        try:
            info = describe_table_impl(db_filename, table)
        except Exception:
            lines.append(f"- {table}: <unable to describe>")
            continue
        cols = []
        for c in info["columns"]:
            tag = "*" if c.get("primary_key") else ""
            ctype = (c.get("type") or "").strip() or "ANY"
            cols.append(f"{c['name']}{tag}:{ctype}")
        count = _safe_count_rows(db_filename, table)
        size = f"{count} rows" if count is not None else "? rows"
        lines.append(f"- {table} ({size}): {', '.join(cols)}")
    lines.append("")
    lines.append("Legend: * marks a primary key column. Use the toolbox to inspect any of these further.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return str(value)


def _ascii_text_columns(info: dict[str, Any]) -> list[str]:
    """Best-effort detection of text columns (TEXT/CHAR/VARCHAR/CLOB/NVARCHAR/...)."""
    out: list[str] = []
    for col in info.get("columns", []):
        ctype = str(col.get("type", "")).upper()
        if any(token in ctype for token in ("CHAR", "TEXT", "CLOB", "STRING")) or not ctype:
            out.append(col["name"])
    return out


def _foreign_keys_impl(db_filename: str, table: str) -> dict[str, Any]:
    quoted = _quote_identifier(table)
    with _readonly_connection(db_filename) as conn:
        rows = conn.execute(f"PRAGMA foreign_key_list({quoted})").fetchall()
    return {
        "foreign_keys": [
            {
                "from_column": r["from"],
                "to_table": r["table"],
                "to_column": r["to"],
                "on_update": r["on_update"],
                "on_delete": r["on_delete"],
            }
            for r in rows
        ]
    }


def _search_value_impl(
    db_filename: str, value: str, only_table: str | None
) -> dict[str, Any]:
    if not value:
        return {"error": "missing 'value'"}

    try:
        tables = list_tables_impl(db_filename)
    except Exception as exc:
        return {"error": str(exc)}

    if only_table is not None:
        tables = [t for t in tables if t == only_table]
        if not tables:
            return {"error": f"Table not found: {only_table}"}

    matches: list[dict[str, Any]] = []
    escaped = value.replace("'", "''")
    pattern = f"%{escaped}%"
    for table in tables:
        try:
            info = describe_table_impl(db_filename, table)
        except Exception:
            continue
        for col in _ascii_text_columns(info):
            try:
                qt = _quote_identifier(table)
                qc = _quote_identifier(col)
                sql = (
                    f"SELECT {qc} AS value, COUNT(*) AS count "
                    f"FROM {qt} "
                    f"WHERE LOWER({qc}) LIKE LOWER('{pattern}') "
                    f"GROUP BY {qc} "
                    f"ORDER BY count DESC "
                    f"LIMIT 5"
                )
                result = run_sql_readonly_impl(db_filename, sql, limit=5)
                if result["rows"]:
                    matches.append(
                        {
                            "table": table,
                            "column": col,
                            "matches": result["rows"],
                        }
                    )
            except Exception:
                continue
        if len(matches) >= 30:
            break

    return {"matches": matches}


def _run_query_impl(db_filename: str, sql: str) -> dict[str, Any]:
    if not isinstance(sql, str) or not sql.strip():
        return {"error": "missing 'sql'"}
    try:
        normalized = normalize_readonly_sql(sql.strip())
        validate_readonly_sql(normalized)
    except ValueError as exc:
        return {"error": f"invalid SQL: {exc}"}
    try:
        return _jsonable(run_sql_readonly_impl(db_filename, normalized, limit=20))
    except (ValueError, SQLExecutionTimeout) as exc:
        return {"error": str(exc)}


def _execute_tool_sync(name: str, args: dict[str, Any], db_filename: str) -> dict[str, Any]:
    """Run one tool. Always returns a JSON-serializable dict (errors returned, not raised)."""
    try:
        if name == "list_tables":
            return {"tables": list_tables_impl(db_filename)}

        if name == "describe_table":
            table = args.get("table")
            if not isinstance(table, str):
                return {"error": "missing 'table'"}
            return _jsonable(describe_table_impl(db_filename, table))

        if name == "sample_rows":
            table = args.get("table")
            if not isinstance(table, str):
                return {"error": "missing 'table'"}
            try:
                limit = max(1, min(int(args.get("limit", 5)), 20))
            except (TypeError, ValueError):
                limit = 5
            quoted = _quote_identifier(table)
            return _jsonable(
                run_sql_readonly_impl(db_filename, f"SELECT * FROM {quoted}", limit=limit)
            )

        if name == "distinct_values":
            table = args.get("table")
            column = args.get("column")
            if not isinstance(table, str) or not isinstance(column, str):
                return {"error": "missing 'table' or 'column'"}
            qt = _quote_identifier(table)
            qc = _quote_identifier(column)
            sql = (
                f"SELECT {qc} AS value, COUNT(*) AS count FROM {qt} "
                f"GROUP BY {qc} ORDER BY count DESC LIMIT 50"
            )
            return _jsonable(run_sql_readonly_impl(db_filename, sql, limit=50))

        if name == "count_rows":
            table = args.get("table")
            if not isinstance(table, str):
                return {"error": "missing 'table'"}
            quoted = _quote_identifier(table)
            return _jsonable(
                run_sql_readonly_impl(db_filename, f"SELECT COUNT(*) AS count FROM {quoted}", limit=1)
            )

        if name == "find_related":
            table = args.get("table")
            if not isinstance(table, str):
                return {"error": "missing 'table'"}
            return _foreign_keys_impl(db_filename, table)

        if name == "search_value":
            value = args.get("value")
            only_table = args.get("table")
            if not isinstance(value, str):
                return {"error": "missing 'value'"}
            if only_table is not None and not isinstance(only_table, str):
                only_table = None
            return _search_value_impl(db_filename, value, only_table)

        if name == "run_query":
            return _run_query_impl(db_filename, args.get("sql", ""))

        return {"error": f"unknown tool: {name}"}

    except Exception as exc:  # noqa: BLE001 — surface any error to the model.
        return {"error": f"{exc.__class__.__name__}: {exc}"}


async def _execute_tool(name: str, args: dict[str, Any], db_filename: str) -> dict[str, Any]:
    return await asyncio.to_thread(_execute_tool_sync, name, args, db_filename)


# ---------------------------------------------------------------------------
# Gemini transport
# ---------------------------------------------------------------------------


async def _post_gemini(
    contents: list[dict[str, Any]],
    api_key: str,
    model: str,
    timeout_seconds: float,
    system_prompt: str = SYSTEM_PROMPT,
) -> dict[str, Any]:
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "tools": [{"function_declarations": TOOL_DECLARATIONS}],
        "generationConfig": {"temperature": 0.1},
    }
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent"

    # Retry once on transient errors (429 / 5xx) with a short backoff.
    backoff_seconds = 4.0
    for attempt in (1, 2):
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": api_key},
                json=payload,
            )
        if response.status_code < 400:
            return response.json()
        if response.status_code in (429, 500, 502, 503, 504) and attempt == 1:
            logger.warning(
                "gemini-agent transient %s on attempt %s; backing off %.1fs",
                response.status_code,
                attempt,
                backoff_seconds,
            )
            await asyncio.sleep(backoff_seconds)
            continue
        # Surface a short snippet of the error body so logs show the real cause.
        body_preview = response.text[:300].replace("\n", " ")
        raise GeminiGenerationError(
            f"Gemini API HTTP {response.status_code}: {body_preview}"
        )
    raise GeminiGenerationError("Gemini API exhausted retries.")


def _extract_function_calls(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [p["functionCall"] for p in parts if "functionCall" in p]


def _build_function_response_part(name: str, response: dict[str, Any]) -> dict[str, Any]:
    return {"functionResponse": {"name": name, "response": response}}


def _validate_submit_args(args: dict[str, Any], verifier: Callable[[str], None] | None):
    """Validate submit_sql args. Raises ValueError / SQLExecutionTimeout on failure."""
    from app.services.ollama_service import SQLGenerationResult

    raw_sql = args.get("sql")
    if not isinstance(raw_sql, str) or not raw_sql.strip():
        raise ValueError("submit_sql is missing a non-empty 'sql' argument.")

    normalized = normalize_readonly_sql(raw_sql.strip())
    validate_readonly_sql(normalized)
    if verifier is not None:
        verifier(normalized)  # may raise ValueError or SQLExecutionTimeout

    assumptions_raw = args.get("assumptions") or []
    if not isinstance(assumptions_raw, list):
        assumptions_raw = []
    assumptions = [str(a) for a in assumptions_raw if a is not None]

    confidence = args.get("confidence")
    try:
        confidence_f = float(confidence) if confidence is not None else 0.5
    except (TypeError, ValueError):
        confidence_f = 0.5
    if confidence_f > 1.5:
        confidence_f = confidence_f / 100.0
    confidence_f = max(0.0, min(1.0, confidence_f))

    return SQLGenerationResult(
        sql=normalized,
        assumptions=assumptions,
        confidence=confidence_f,
    )


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------


def _summarize_tool_result(name: str, result: dict[str, Any]) -> dict[str, Any]:
    """Compact representation of a tool result for live trace UIs."""
    if "error" in result:
        return {"error": str(result["error"])[:200]}

    if name == "list_tables":
        tables = result.get("tables", [])
        return {"count": len(tables), "tables": tables[:30]}

    if name == "describe_table":
        cols = result.get("columns", [])
        return {
            "table": result.get("table"),
            "column_count": len(cols),
            "columns": [c.get("name") for c in cols[:30]],
        }

    if name in ("sample_rows", "run_query"):
        rows = result.get("rows", [])
        return {
            "row_count": result.get("row_count", len(rows)),
            "columns": result.get("columns", []),
            "preview": rows[:3],
        }

    if name == "distinct_values":
        rows = result.get("rows", [])
        return {
            "distinct_returned": result.get("row_count", len(rows)),
            "preview": rows[:10],
        }

    if name == "count_rows":
        rows = result.get("rows", [])
        n = rows[0].get("count") if rows else None
        return {"count": n}

    if name == "find_related":
        fks = result.get("foreign_keys", [])
        return {"foreign_key_count": len(fks), "foreign_keys": fks}

    return {"ok": True}


async def generate_sql_with_tools(
    *,
    question: str,
    db_filename: str,
    verifier: Callable[[str], None] | None = None,
    tier: str | TierConfig = DEFAULT_TIER,
    emit: EmitFn | None = None,
):
    """Run the tool-calling agent loop and return a SQLGenerationResult.

    Parameters
    ----------
    tier
        "fast", "medium", or "high" — controls iteration + submit retry budgets and
        prompt addenda. Pass a TierConfig directly to override.
    emit
        Optional async callback invoked with structured event dicts so callers can
        stream progress (used by the SSE endpoint).
    """
    api_key = get_api_key()
    if not api_key:
        raise GeminiNotConfiguredError("GEMINI_API_KEY is not set; cannot use Gemini tool agent.")

    tier_config = tier if isinstance(tier, TierConfig) else resolve_tier(tier)
    emit_fn: EmitFn = emit or _noop_emit

    settings = get_settings()
    model = settings.gemini_model
    timeout = settings.gemini_timeout_seconds
    max_iterations = max(1, tier_config.max_iterations)
    max_submit_retries = max(1, tier_config.max_submit_retries)

    system_prompt = SYSTEM_PROMPT
    if tier_config.prompt_addendum:
        system_prompt = f"{SYSTEM_PROMPT}\n\n{tier_config.prompt_addendum}"

    await emit_fn(
        {
            "type": "start",
            "tier": tier_config.name,
            "max_iterations": max_iterations,
            "max_submit_retries": max_submit_retries,
            "model": model,
        }
    )

    brief = await asyncio.to_thread(_build_database_brief, db_filename)
    await emit_fn({"type": "brief", "brief": brief})

    initial_text = (
        f"{brief}\n\n"
        f"User question: {question}\n\n"
        "Inspect anything uncertain with the toolbox, then call submit_sql with your final answer."
    )
    contents: list[dict[str, Any]] = [
        {"role": "user", "parts": [{"text": initial_text}]},
    ]

    submit_attempts = 0
    last_text = ""

    for iteration in range(1, max_iterations + 1):
        await emit_fn({"type": "iteration", "iteration": iteration})

        try:
            data = await _post_gemini(
                contents=contents,
                api_key=api_key,
                model=model,
                timeout_seconds=timeout,
                system_prompt=system_prompt,
            )
        except httpx.HTTPError as exc:
            raise GeminiGenerationError(f"Gemini transport error: {exc.__class__.__name__}") from exc

        candidates = data.get("candidates") or []
        if not candidates:
            raise GeminiGenerationError("Gemini returned no candidates.")

        parts = candidates[0].get("content", {}).get("parts", []) or []
        function_calls = _extract_function_calls(parts)
        text_parts = [p["text"] for p in parts if "text" in p]
        if text_parts:
            last_text = "\n".join(text_parts)
            await emit_fn({"type": "model_text", "text": last_text})

        contents.append({"role": "model", "parts": parts})

        if not function_calls:
            if iteration == max_iterations:
                raise GeminiGenerationError(
                    f"Model gave up without calling submit_sql. Last text: {(last_text or '<empty>')[:300]}"
                )
            await emit_fn({"type": "nudge", "reason": "no tool call"})
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "You did not call any tool. Either call a tool to gather more info, "
                                "or call submit_sql with your final SQL."
                            )
                        }
                    ],
                }
            )
            continue

        function_response_parts: list[dict[str, Any]] = []
        final_result = None

        for call in function_calls:
            name = call.get("name", "")
            args = call.get("args") or {}
            logger.info(
                "gemini-agent iter=%s tool=%s args=%s",
                iteration,
                name,
                json.dumps(args)[:200],
            )
            await emit_fn(
                {"type": "tool_call", "iteration": iteration, "name": name, "args": args}
            )

            if name == "submit_sql":
                submit_attempts += 1
                try:
                    final_result = _validate_submit_args(args, verifier)
                except (ValueError, SQLExecutionTimeout) as exc:
                    error_msg = str(exc)
                    await emit_fn(
                        {
                            "type": "submit_failed",
                            "attempt": submit_attempts,
                            "max_attempts": max_submit_retries,
                            "error": error_msg,
                            "sql": args.get("sql"),
                        }
                    )
                    if submit_attempts >= max_submit_retries:
                        raise GeminiGenerationError(
                            f"submit_sql failed {submit_attempts} times. Last error: {error_msg}"
                        )
                    err_payload = {
                        "ok": False,
                        "error": error_msg,
                        "hint": (
                            "Your SQL did not pass validation. Inspect the schema again "
                            "(describe_table, distinct_values, run_query) and call submit_sql with a fix. "
                            f"You have {max_submit_retries - submit_attempts} attempt(s) left."
                        ),
                        "attempt": submit_attempts,
                    }
                    function_response_parts.append(
                        _build_function_response_part("submit_sql", err_payload)
                    )
                    continue
                else:
                    await emit_fn(
                        {
                            "type": "submit_ok",
                            "sql": final_result.sql,
                            "confidence": final_result.confidence,
                            "assumptions": list(final_result.assumptions),
                        }
                    )
                    break  # leave the per-call loop, then return below

            result = await _execute_tool(name, args, db_filename)
            await emit_fn(
                {
                    "type": "tool_result",
                    "iteration": iteration,
                    "name": name,
                    "summary": _summarize_tool_result(name, result),
                }
            )
            function_response_parts.append(_build_function_response_part(name, result))

        if final_result is not None:
            return final_result

        if function_response_parts:
            contents.append({"role": "user", "parts": function_response_parts})

    raise GeminiGenerationError(
        f"Gemini agent exceeded {max_iterations} iterations without a valid submit_sql."
    )
