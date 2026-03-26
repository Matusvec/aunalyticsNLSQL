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
from app.services.ollama_service import SQLGenerationResult


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


@pytest.mark.parametrize(
    ("sql", "expected_columns"),
    [
        (
            "SELECT FirstName, LastName FROM customers ORDER BY CustomerId LIMIT 3",
            ["FirstName", "LastName"],
        ),
        (
            "SELECT CustomerId FROM customers WHERE FirstName = '___definitely_missing___'",
            ["CustomerId"],
        ),
    ],
)
def test_ask_success_paths(monkeypatch: pytest.MonkeyPatch, sql: str, expected_columns: list[str]) -> None:
    async def fake_generate_sql_from_question(question: str, schema_summary: str) -> SQLGenerationResult:
        return SQLGenerationResult(
            sql=sql,
            assumptions=["Interpreted customers as the source table."],
            confidence=0.84,
        )

    monkeypatch.setattr(query_router, "generate_sql_from_question", fake_generate_sql_from_question)

    response = _post_ask("unused")

    assert response.status_code == 200
    body = response.json()
    assert body["sql"] == sql
    assert body["assumptions"] == ["Interpreted customers as the source table."]
    assert body["confidence"] == 0.84
    assert body["columns"] == expected_columns

    if "___definitely_missing___" in sql:
        assert body["rows"] == []
        assert body["row_count"] == 0
    else:
        assert body["row_count"] == 3
        assert body["rows"][0]["FirstName"] == "Luís"


def test_ask_returns_500_for_malformed_model_output(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_generate_sql_from_question(question: str, schema_summary: str) -> SQLGenerationResult:
        SQLGenerationResult.model_validate(
            {
                "sql": "SELECT 1",
                "assumptions": "should have been a list",
                "confidence": "not-a-number",
            }
        )
        raise AssertionError("unreachable")

    monkeypatch.setattr(query_router, "generate_sql_from_question", fake_generate_sql_from_question)

    response = _post_ask("unused")

    assert response.status_code == 500
    assert "Ask failed:" in response.json()["detail"]


def test_ask_rejects_invalid_sql_from_model(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_generate_sql_from_question(question: str, schema_summary: str) -> SQLGenerationResult:
        return SQLGenerationResult(
            sql="DROP TABLE customers",
            assumptions=["Guessed the user wanted destructive cleanup."],
            confidence=0.12,
        )

    monkeypatch.setattr(query_router, "generate_sql_from_question", fake_generate_sql_from_question)

    response = _post_ask("unused")

    assert response.status_code == 400
    assert response.json()["detail"] == "Only read-only SELECT queries are allowed"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT missing_column FROM customers",
        "SELECT CustomerId FROM missing_table",
    ],
)
def test_ask_handles_nonexistent_table_or_column(monkeypatch: pytest.MonkeyPatch, sql: str) -> None:
    async def fake_generate_sql_from_question(question: str, schema_summary: str) -> SQLGenerationResult:
        return SQLGenerationResult(
            sql=sql,
            assumptions=["Mapped the request to a schema object that does not exist."],
            confidence=0.18,
        )

    monkeypatch.setattr(query_router, "generate_sql_from_question", fake_generate_sql_from_question)

    response = _post_ask("unused")

    assert response.status_code == 500
    assert "Ask failed:" in response.json()["detail"]


def test_ask_returns_500_when_ollama_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_generate_sql_from_question(question: str, schema_summary: str) -> SQLGenerationResult:
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(query_router, "generate_sql_from_question", fake_generate_sql_from_question)

    response = _post_ask("unused")

    assert response.status_code == 500
    assert "Connection refused" in response.json()["detail"]
