from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import history_service


def test_log_successful_query_and_read_recent_history(tmp_path, monkeypatch) -> None:
    history_db_path = tmp_path / "query_history.sqlite"
    monkeypatch.setattr(history_service, "HISTORY_DB_PATH", history_db_path)

    history_service.log_successful_query(
        question="show me customers",
        sql="SELECT * FROM customers LIMIT 5",
        confidence=0.82,
    )

    items = history_service.get_recent_history()

    assert len(items) == 1
    assert items[0]["question"] == "show me customers"
    assert items[0]["sql"] == "SELECT * FROM customers LIMIT 5"
    assert items[0]["confidence"] == 0.82
    assert items[0]["status"] == "success"
    assert items[0]["error_message"] is None
    assert "T" in items[0]["created_at"]

    with sqlite3.connect(history_db_path) as conn:
        row = conn.execute(
            "SELECT question, sql, confidence, status, error_message FROM query_history"
        ).fetchone()

    assert row == (
        "show me customers",
        "SELECT * FROM customers LIMIT 5",
        0.82,
        "success",
        None,
    )


def test_recent_history_is_limited_to_50_items(tmp_path, monkeypatch) -> None:
    history_db_path = tmp_path / "query_history.sqlite"
    monkeypatch.setattr(history_service, "HISTORY_DB_PATH", history_db_path)

    for index in range(60):
        history_service.log_successful_query(
            question=f"question {index}",
            sql=f"SELECT {index}",
            confidence=0.5,
        )

    items = history_service.get_recent_history(limit=100)

    assert len(items) == 50
    assert items[0]["question"] == "question 59"
    assert items[-1]["question"] == "question 10"
