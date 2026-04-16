from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


DB_DIR = Path(__file__).resolve().parents[2] / "db"
SCHEMA_SUMMARY_MAX_TABLES = 6
QUESTION_TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")


def safe_db_path(db_filename: str) -> Path:
    candidate = (DB_DIR / db_filename).resolve()
    db_root = DB_DIR.resolve()

    if not str(candidate).startswith(str(db_root)):
        raise ValueError("Invalid database path")

    if not candidate.exists():
        raise FileNotFoundError(f"Database not found: {db_filename}")

    return candidate


def connect(db_filename: str) -> sqlite3.Connection:
    conn = sqlite3.connect(safe_db_path(db_filename))
    conn.row_factory = sqlite3.Row
    return conn


def list_tables_impl(db_filename: str) -> list[str]:
    with connect(db_filename) as conn:
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
    with connect(db_filename) as conn:
        rows = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
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
    limit = max(1, min(limit, 1000))

    with connect(db_filename) as conn:
        cur = conn.execute(sql)
        rows = cur.fetchmany(limit)
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
    with connect(db_filename) as conn:
        try:
            conn.execute(f"EXPLAIN QUERY PLAN {sql}")
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


def _build_schema_summary_for_tables(db_filename: str, table_names: list[str]) -> str:
    parts: list[str] = []

    for table_name in table_names:
        table_info = describe_table_impl(db_filename, table_name)
        col_text = ", ".join(
            f"{col['name']} {col['type']}" + (" PRIMARY KEY" if col["primary_key"] else "")
            for col in table_info["columns"]
        )
        parts.append(f"TABLE {table_name}: {col_text}")

    return "\n".join(parts)


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
