from __future__ import annotations

import asyncio
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.settings import get_settings


SCHEMA_SUMMARY_MAX_TABLES = 6
SAMPLE_ROWS_PER_TABLE = 3
SAMPLE_VALUE_MAX_LEN = 80
QUESTION_TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
_VALID_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_ \-]{0,127}$")


class SQLExecutionTimeout(ValueError):
    """Raised when an SQL query exceeds the configured wall-clock budget."""


def _db_root() -> Path:
    return get_settings().db_dir.resolve()


def safe_db_path(db_filename: str) -> Path:
    if not db_filename or "/" in db_filename or "\\" in db_filename or db_filename in (".", ".."):
        raise ValueError("Invalid database path")

    root = _db_root()
    candidate = (root / db_filename).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Invalid database path") from exc

    if not candidate.is_file():
        raise FileNotFoundError(f"Database not found: {db_filename}")

    return candidate


def _quote_identifier(name: str) -> str:
    """Safely quote an SQLite identifier (table/column) by escaping single quotes."""
    if not _VALID_IDENTIFIER_RE.match(name):
        raise ValueError("Invalid identifier")
    return "'" + name.replace("'", "''") + "'"


@contextmanager
def _readonly_connection(db_filename: str) -> Iterator[sqlite3.Connection]:
    path = safe_db_path(db_filename)
    # mode=ro forbids writes at the engine level (defense in depth).
    # immutable=1 also disables the rollback journal which suits our read-only use.
    uri = f"file:{path}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _install_query_deadline(conn: sqlite3.Connection, deadline_monotonic: float) -> None:
    """Use sqlite3's progress handler to abort queries that exceed the wall-clock deadline."""
    n_ops = max(100, get_settings().sql_progress_handler_n)

    def _abort_if_past_deadline() -> int:
        return 1 if time.monotonic() >= deadline_monotonic else 0

    conn.set_progress_handler(_abort_if_past_deadline, n_ops)


def _run_with_timeout(conn: sqlite3.Connection, sql: str) -> sqlite3.Cursor:
    timeout = get_settings().sql_query_timeout_seconds
    deadline = time.monotonic() + timeout
    _install_query_deadline(conn, deadline)
    try:
        return conn.execute(sql)
    except sqlite3.OperationalError as exc:
        message = str(exc).lower()
        if "interrupt" in message or "abort" in message:
            raise SQLExecutionTimeout(
                f"Query exceeded the {timeout:.0f}s execution budget"
            ) from exc
        raise


def foreign_keys_impl(db_filename: str, table_name: str) -> list[dict[str, Any]]:
    """Return foreign keys defined on `table_name` via `PRAGMA foreign_key_list`."""
    quoted = _quote_identifier(table_name)
    with _readonly_connection(db_filename) as conn:
        rows = conn.execute(f"PRAGMA foreign_key_list({quoted})").fetchall()
    return [
        {
            "from_column": row["from"],
            "to_table": row["table"],
            "to_column": row["to"],
        }
        for row in rows
    ]


def row_count_impl(db_filename: str, table_name: str) -> int | None:
    quoted = _quote_identifier(table_name)
    try:
        with _readonly_connection(db_filename) as conn:
            row = conn.execute(f"SELECT COUNT(*) AS n FROM {quoted}").fetchone()
            return int(row["n"]) if row is not None else None
    except Exception:
        return None


def list_tables_impl(db_filename: str) -> list[str]:
    with _readonly_connection(db_filename) as conn:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        return [row["name"] for row in rows]


def describe_table_impl(db_filename: str, table_name: str) -> dict[str, Any]:
    quoted = _quote_identifier(table_name)
    with _readonly_connection(db_filename) as conn:
        rows = conn.execute(f"PRAGMA table_info({quoted})").fetchall()
        if not rows:
            raise ValueError(f"Table not found: {table_name}")

        return {
            "table": table_name,
            "columns": [
                {
                    "cid": row["cid"],
                    "name": row["name"],
                    "type": row["type"],
                    "notnull": bool(row["notnull"]),
                    "default_value": row["dflt_value"],
                    "primary_key": bool(row["pk"]),
                }
                for row in rows
            ],
        }


def run_sql_readonly_impl(db_filename: str, sql: str, limit: int = 200) -> dict[str, Any]:
    settings = get_settings()
    limit = max(1, min(limit, settings.sql_max_row_limit))

    with _readonly_connection(db_filename) as conn:
        try:
            cur = _run_with_timeout(conn, sql)
            rows = cur.fetchmany(limit)
        except SQLExecutionTimeout:
            raise
        except sqlite3.Error as exc:
            raise ValueError(str(exc)) from exc

        columns = [desc[0] for desc in cur.description] if cur.description else []
        return {
            "columns": columns,
            "rows": [dict(r) for r in rows],
            "row_count": len(rows),
            "limit_applied": limit,
        }


def validate_sql_compiles_impl(db_filename: str, sql: str) -> None:
    """
    Ask SQLite to compile the query so missing tables/columns fail before runtime.
    """
    with _readonly_connection(db_filename) as conn:
        try:
            _run_with_timeout(conn, f"EXPLAIN QUERY PLAN {sql}")
        except SQLExecutionTimeout:
            raise
        except sqlite3.Error as exc:
            raise ValueError(str(exc)) from exc


def build_schema_summary_impl(db_filename: str) -> str:
    tables = list_tables_impl(db_filename)
    return _build_schema_summary_for_tables(db_filename, tables)


def build_relevant_schema_summary_impl(
    db_filename: str,
    question: str,
    max_tables: int = SCHEMA_SUMMARY_MAX_TABLES,
) -> str:
    tables = list_tables_impl(db_filename)
    table_names_summary = _build_table_names_summary(tables)
    if len(tables) <= max_tables:
        return "\n\n".join(
            [table_names_summary, _build_schema_summary_for_tables(db_filename, tables)]
        )

    question_tokens = _extract_question_tokens(question)
    scored_tables: list[tuple[int, str]] = []
    for table_name in tables:
        table_info = describe_table_impl(db_filename, table_name)
        score = _score_table_relevance(table_info, question_tokens)
        scored_tables.append((score, table_name))

    scored_tables.sort(key=lambda item: (-item[0], item[1]))
    selected_tables = [table_name for _, table_name in scored_tables[:max_tables]]
    remaining_tables = [table_name for table_name in tables if table_name not in selected_tables]

    parts = [
        table_names_summary,
        "Detailed schemas for the most relevant tables:\n"
        + _build_schema_summary_for_tables(db_filename, selected_tables),
    ]
    if remaining_tables:
        parts.append("Other available tables (names only): " + ", ".join(remaining_tables))
    return "\n\n".join(parts)


# Async wrappers — use these from async routes/services to avoid blocking the loop.
async def list_tables(db_filename: str) -> list[str]:
    return await asyncio.to_thread(list_tables_impl, db_filename)


async def describe_table(db_filename: str, table_name: str) -> dict[str, Any]:
    return await asyncio.to_thread(describe_table_impl, db_filename, table_name)


async def run_sql_readonly(db_filename: str, sql: str, limit: int = 200) -> dict[str, Any]:
    return await asyncio.to_thread(run_sql_readonly_impl, db_filename, sql, limit)


async def validate_sql_compiles(db_filename: str, sql: str) -> None:
    await asyncio.to_thread(validate_sql_compiles_impl, db_filename, sql)


async def build_schema_summary(db_filename: str) -> str:
    return await asyncio.to_thread(build_schema_summary_impl, db_filename)


async def build_relevant_schema_summary(
    db_filename: str,
    question: str,
    max_tables: int = SCHEMA_SUMMARY_MAX_TABLES,
) -> str:
    return await asyncio.to_thread(
        build_relevant_schema_summary_impl, db_filename, question, max_tables
    )


def _build_schema_summary_for_tables(db_filename: str, table_names: list[str]) -> str:
    parts: list[str] = []

    for table_name in table_names:
        table_info = describe_table_impl(db_filename, table_name)
        col_text = ", ".join(
            f"{col['name']} {col['type']}" + (" PRIMARY KEY" if col["primary_key"] else "")
            for col in table_info["columns"]
        )
        block = [f"TABLE {table_name}: {col_text}"]
        sample_block = _format_sample_rows(db_filename, table_name)
        if sample_block:
            block.append(sample_block)
        parts.append("\n".join(block))

    return "\n".join(parts)


def _format_sample_rows(db_filename: str, table_name: str) -> str:
    rows = _fetch_sample_rows(db_filename, table_name, SAMPLE_ROWS_PER_TABLE)
    if not rows:
        return ""
    formatted = ["  Sample rows (illustrative, not exhaustive):"]
    for row in rows:
        pairs = ", ".join(f"{k}={_format_sample_value(v)}" for k, v in row.items())
        formatted.append(f"    {{{pairs}}}")
    return "\n".join(formatted)


def _fetch_sample_rows(db_filename: str, table_name: str, n: int) -> list[dict[str, Any]]:
    try:
        quoted = _quote_identifier(table_name)
    except ValueError:
        return []
    try:
        with _readonly_connection(db_filename) as conn:
            cur = conn.execute(f"SELECT * FROM {quoted} LIMIT ?", (n,))
            return [dict(row) for row in cur.fetchmany(n)]
    except Exception:
        return []


def _format_sample_value(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    text = str(value)
    if len(text) > SAMPLE_VALUE_MAX_LEN:
        text = text[: SAMPLE_VALUE_MAX_LEN - 1] + "…"
    return '"' + text.replace('"', '\\"') + '"'


def _build_table_names_summary(table_names: list[str]) -> str:
    return "Available tables in this database (use only these table names): " + ", ".join(table_names)


def _extract_question_tokens(question: str) -> set[str]:
    tokens = {match.group(0).lower() for match in QUESTION_TOKEN_RE.finditer(question)}
    expanded_tokens = set(tokens)
    for token in tokens:
        if token.endswith("s") and len(token) > 3:
            expanded_tokens.add(token[:-1])
        else:
            expanded_tokens.add(f"{token}s")
    return expanded_tokens


def _score_table_relevance(table_info: dict[str, Any], question_tokens: set[str]) -> int:
    table_name = str(table_info["table"]).lower()
    score = 0

    if table_name in question_tokens:
        score += 10

    for part in table_name.split("_"):
        if part in question_tokens:
            score += 4

    for column in table_info["columns"]:
        column_name = str(column["name"]).lower()
        if column_name in question_tokens:
            score += 6
        for part in column_name.split("_"):
            if part in question_tokens:
                score += 2

    return score
