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
from app.services.ollama_service import OllamaServiceError
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


def test_ask_success_path_uses_tool_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ask_service import AskWithToolsResult, ToolTrace

    async def fake_ask_question_with_tools(question: str, db_filename: str, limit: int) -> AskWithToolsResult:
        assert question == "unused"
        assert db_filename == "chinook.db"
        assert limit == 5
        return AskWithToolsResult(
            answer="Luís Gonçalves is the first customer in the table.",
            sql="SELECT FirstName, LastName FROM customers ORDER BY CustomerId LIMIT 1",
            tool_calls=[
                ToolTrace(
                    tool_name="run_sql_readonly",
                    arguments={
                        "db_filename": "chinook.db",
                        "sql": "SELECT FirstName, LastName FROM customers ORDER BY CustomerId LIMIT 1",
                        "limit": 5,
                    },
                    result_preview='{"columns":["FirstName","LastName"],"rows":[{"FirstName":"Luís","LastName":"Gonçalves"}],"row_count":1,"limit_applied":5}',
                    structured_result={
                        "columns": ["FirstName", "LastName"],
                        "rows": [{"FirstName": "Luís", "LastName": "Gonçalves"}],
                        "row_count": 1,
                        "limit_applied": 5,
                    },
                )
            ],
            columns=["FirstName", "LastName"],
            rows=[{"FirstName": "Luís", "LastName": "Gonçalves"}],
            row_count=1,
            limit_applied=5,
        )

    monkeypatch.setattr(query_router, "ask_question_with_tools", fake_ask_question_with_tools)

    response = _post_ask("unused")

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Luís Gonçalves is the first customer in the table."
    assert body["sql"] == "SELECT FirstName, LastName FROM customers ORDER BY CustomerId LIMIT 1"
    assert body["columns"] == ["FirstName", "LastName"]
    assert body["rows"][0]["FirstName"] == "Luís"
    assert body["tool_calls"][0]["tool_name"] == "run_sql_readonly"


def test_ask_returns_404_for_missing_database(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask_question_with_tools(question: str, db_filename: str, limit: int):
        raise FileNotFoundError("Database not found: missing.db")

    monkeypatch.setattr(query_router, "ask_question_with_tools", fake_ask_question_with_tools)

    response = _post_ask("unused")

    assert response.status_code == 404
    assert response.json()["detail"] == "Database not found: missing.db"


def test_ask_returns_400_for_invalid_request(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask_question_with_tools(question: str, db_filename: str, limit: int):
        raise ValueError("Only read-only SELECT queries are allowed")

    monkeypatch.setattr(query_router, "ask_question_with_tools", fake_ask_question_with_tools)

    response = _post_ask("unused")

    assert response.status_code == 400
    assert response.json()["detail"] == "Only read-only SELECT queries are allowed"


def test_ask_returns_500_when_tool_flow_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask_question_with_tools(question: str, db_filename: str, limit: int):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(query_router, "ask_question_with_tools", fake_ask_question_with_tools)

    response = _post_ask("unused")

    assert response.status_code == 500
    assert "Connection refused" in response.json()["detail"]


def test_ask_returns_503_when_ollama_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask_question_with_tools(question: str, db_filename: str, limit: int):
        raise OllamaServiceError("Ollama request failed at http://localhost:11434/api/chat: 404 Not Found")

    monkeypatch.setattr(query_router, "ask_question_with_tools", fake_ask_question_with_tools)

    response = _post_ask("unused")

    assert response.status_code == 503
    assert "Ollama request failed" in response.json()["detail"]
