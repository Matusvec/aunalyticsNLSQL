from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HISTORY_DB_PATH = Path(__file__).resolve().parents[2] / "db" / "query_history.sqlite"


def connect_history() -> sqlite3.Connection:
    HISTORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(HISTORY_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_history_table() -> None:
    with connect_history() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                sql TEXT,
                confidence REAL,
                status TEXT NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL
            )
            """
        )


def log_successful_query(question: str, sql: str, confidence: float | None) -> None:
    ensure_history_table()
    created_at = datetime.now(timezone.utc).isoformat()

    with connect_history() as conn:
        conn.execute(
            """
            INSERT INTO query_history (question, sql, confidence, status, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (question, sql, confidence, "success", None, created_at),
        )


def get_recent_history(limit: int = 50) -> list[dict[str, Any]]:
    ensure_history_table()
    limit = max(1, min(limit, 50))

    with connect_history() as conn:
        rows = conn.execute(
            """
            SELECT id, question, sql, confidence, status, error_message, created_at
            FROM query_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]
