from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sqlite-mcp")

DB_DIR = Path(__file__).resolve().parents[1] / "db"


def _safe_db_path(db_filename: str) -> Path:
    """
    Restrict database access to backend/db only.
    Prevents path traversal like ../../../etc/passwd
    """
    candidate = (DB_DIR / db_filename).resolve()
    db_root = DB_DIR.resolve()

    if not str(candidate).startswith(str(db_root)):
        raise ValueError("Invalid database path")

    if not candidate.exists():
        raise FileNotFoundError(f"Database not found: {db_filename}")

    return candidate


def _connect(db_filename: str) -> sqlite3.Connection:
    path = _safe_db_path(db_filename)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def _is_readonly_sql(sql: str) -> bool:
    """
    Extra defense. FastAPI layer should still validate with sqlglot.
    """
    stripped = sql.strip().lower()
    return stripped.startswith("select") or stripped.startswith("with")

@mcp.tool()
def list_databases() -> list[str]:
    """List available SQLite database files in backend/db."""
    if not DB_DIR.exists():
        return []
    return sorted([p.name for p in DB_DIR.glob("*.sqlite")])

@mcp.tool()
def list_tables(db_filename: str) -> list[str]:
    """Return all user tables in a SQLite database."""
    with _connect(db_filename) as conn:
        rows = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()
        return [row["name"] for row in rows]


@mcp.tool()
def describe_table(db_filename: str, table_name: str) -> dict[str, Any]:
    """Return columns for a table using PRAGMA table_info."""
    with _connect(db_filename) as conn:
        rows = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()

        if not rows:
            raise ValueError(f"Table not found: {table_name}")

        columns = []
        for row in rows:
            columns.append({
                "cid": row["cid"],
                "name": row["name"],
                "type": row["type"],
                "notnull": bool(row["notnull"]),
                "default_value": row["dflt_value"],
                "primary_key": bool(row["pk"]),
            })

        return {
            "table": table_name,
            "columns": columns,
        }


@mcp.tool()
def get_foreign_keys(db_filename: str, table_name: str) -> list[dict[str, Any]]:
    """Return foreign keys for a table using PRAGMA foreign_key_list."""
    with _connect(db_filename) as conn:
        rows = conn.execute(f"PRAGMA foreign_key_list('{table_name}')").fetchall()
        return [
            {
                "id": row["id"],
                "seq": row["seq"],
                "from_column": row["from"],
                "to_table": row["table"],
                "to_column": row["to"],
                "on_update": row["on_update"],
                "on_delete": row["on_delete"],
            }
            for row in rows
        ]


@mcp.tool()
def sample_rows(db_filename: str, table_name: str, limit: int = 5) -> dict[str, Any]:
    """Return a few sample rows from a table."""
    limit = max(1, min(limit, 20))

    with _connect(db_filename) as conn:
        rows = conn.execute(f'SELECT * FROM "{table_name}" LIMIT ?', (limit,)).fetchall()

        results = [dict(row) for row in rows]
        columns = list(results[0].keys()) if results else []

        return {
            "table": table_name,
            "columns": columns,
            "rows": results,
            "row_count": len(results),
        }


@mcp.tool()
def run_sql_readonly(db_filename: str, sql: str, limit: int = 200) -> dict[str, Any]:
    """
    Execute a read-only query and return rows.
    FastAPI should validate first with sqlglot.
    """
    if not _is_readonly_sql(sql):
        raise ValueError("Only read-only SELECT/CTE queries are allowed")

    limit = max(1, min(limit, 1000))

    wrapped_sql = f"SELECT * FROM ({sql}) LIMIT {limit}"

    with _connect(db_filename) as conn:
        cur = conn.execute(wrapped_sql)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []

        return {
            "columns": columns,
            "rows": [dict(row) for row in rows],
            "row_count": len(rows),
            "limit_applied": limit,
        }


@mcp.resource("schema://{db_filename}")
def database_schema_resource(db_filename: str) -> str:
    """
    A compact schema summary that can be injected into prompts.
    """
    with _connect(db_filename) as conn:
        tables = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

        lines: list[str] = []
        for table_row in tables:
            table_name = table_row["name"]
            cols = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
            col_parts = []
            for col in cols:
                suffix = " PRIMARY KEY" if col["pk"] else ""
                col_parts.append(f'{col["name"]} {col["type"]}{suffix}')
            lines.append(f"TABLE {table_name}: " + ", ".join(col_parts))

        return "\n".join(lines)


if __name__ == "__main__":
    print("Starting SQLite MCP server on http://localhost:8000")
    mcp.run()