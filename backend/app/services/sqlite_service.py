from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DB_DIR = Path(__file__).resolve().parents[2] / "db"


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
    parts: list[str] = []

    for table_name in tables:
        table_info = describe_table_impl(db_filename, table_name)
        col_text = ", ".join(
            f"{col['name']} {col['type']}" + (" PRIMARY KEY" if col["primary_key"] else "")
            for col in table_info["columns"]
        )
        parts.append(f"TABLE {table_name}: {col_text}")

    return "\n".join(parts)
