from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.routers import query as query_router
from app.services.ask_service import AskResult
from app.services.ollama_service import SQLGenerationError

client = TestClient(app)


def _post_ask(question: str, limit: int = 5) -> httpx.Response:
    return client.post(
        "/api/ask",
        json={
            "db_filename": "chinook.db",
            "question": question,
            "limit": limit,
        },
    )


def test_ask_success_path_returns_minimal_query_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask_question(question: str, db_filename: str, limit: int) -> AskResult:
        assert question == "unused"
        assert db_filename == "chinook.db"
        assert limit == 5
        return AskResult(
            sql="SELECT FirstName, LastName FROM customers ORDER BY CustomerId LIMIT 1",
            columns=["FirstName", "LastName"],
            rows=[{"FirstName": "Luís", "LastName": "Gonçalves"}],
            row_count=1,
            limit_applied=5,
        )

    monkeypatch.setattr(query_router, "ask_question", fake_ask_question)

    response = _post_ask("unused")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "db_filename": "chinook.db",
        "question": "unused",
        "sql": "SELECT FirstName, LastName FROM customers ORDER BY CustomerId LIMIT 1",
        "columns": ["FirstName", "LastName"],
        "rows": [{"FirstName": "Luís", "LastName": "Gonçalves"}],
        "row_count": 1,
        "limit_applied": 5,
    }
    assert "answer" not in body
    assert "tool_calls" not in body


def test_ask_returns_404_for_missing_database(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask_question(question: str, db_filename: str, limit: int):
        raise FileNotFoundError("Database not found: missing.db")

    monkeypatch.setattr(query_router, "ask_question", fake_ask_question)

    response = _post_ask("unused")

    assert response.status_code == 404
    assert response.json()["detail"] == "Database not found: missing.db"


def test_ask_returns_400_for_invalid_request(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask_question(question: str, db_filename: str, limit: int):
        raise ValueError("Only read-only SELECT queries are allowed")

    monkeypatch.setattr(query_router, "ask_question", fake_ask_question)

    response = _post_ask("unused")

    assert response.status_code == 400
    assert response.json()["detail"] == "Only read-only SELECT queries are allowed"


def test_ask_returns_400_for_invalid_generated_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask_question(question: str, db_filename: str, limit: int):
        raise ValueError("no such column: i.CustomerId")

    monkeypatch.setattr(query_router, "ask_question", fake_ask_question)

    response = _post_ask("unused")

    assert response.status_code == 400
    assert response.json()["detail"] == "no such column: i.CustomerId"


def test_ask_returns_500_when_direct_query_flow_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask_question(question: str, db_filename: str, limit: int):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(query_router, "ask_question", fake_ask_question)

    response = _post_ask("unused")

    assert response.status_code == 502
    assert "Connection refused" in response.json()["detail"]


def test_ask_returns_504_for_sql_generation_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask_question(question: str, db_filename: str, limit: int):
        raise SQLGenerationError("SQL generation timed out after 45s on attempt 1 of 2")

    monkeypatch.setattr(query_router, "ask_question", fake_ask_question)

    response = _post_ask("unused")

    assert response.status_code == 504
    assert response.json()["detail"] == "SQL generation timed out after 45s on attempt 1 of 2"


def test_ask_returns_exception_type_when_error_message_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask_question(question: str, db_filename: str, limit: int):
        raise RuntimeError()

    monkeypatch.setattr(query_router, "ask_question", fake_ask_question)

    response = _post_ask("unused")

    assert response.status_code == 500
    assert response.json()["detail"] == "Ask failed: RuntimeError"
