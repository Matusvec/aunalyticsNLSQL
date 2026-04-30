from __future__ import annotations

import asyncio
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.settings import get_settings


# Module-level default; tests may monkeypatch this attribute to a tmp path.
HISTORY_DB_PATH: Path = get_settings().effective_history_db_path

_init_lock = threading.Lock()
_initialized_path: Path | None = None


def _current_history_path() -> Path:
    # Read via globals() so monkeypatch.setattr(module, "HISTORY_DB_PATH", ...) is honored.
    return Path(globals()["HISTORY_DB_PATH"])


def connect_history() -> sqlite3.Connection:
    path = _current_history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_history_table() -> None:
    global _initialized_path
    path = _current_history_path()

    with _init_lock:
        if _initialized_path == path:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path, timeout=5.0) as conn:
            # WAL allows readers and a single writer to proceed without blocking.
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
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
        _initialized_path = path


def log_successful_query(question: str, sql: str, confidence: float | None) -> None:
    ensure_history_table()
    created_at = datetime.now(timezone.utc).isoformat()

    with connect_history() as conn:
        conn.execute("PRAGMA busy_timeout=5000")
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
        conn.execute("PRAGMA busy_timeout=5000")
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


async def log_successful_query_async(question: str, sql: str, confidence: float | None) -> None:
    await asyncio.to_thread(log_successful_query, question, sql, confidence)


async def get_recent_history_async(limit: int = 50) -> list[dict[str, Any]]:
    return await asyncio.to_thread(get_recent_history, limit)
