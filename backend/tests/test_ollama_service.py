from __future__ import annotations

import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import ollama_service
from app.services.ollama_service import SQLGenerationResult


@pytest.mark.anyio
async def test_generate_sql_from_question_retries_when_model_returns_multiple_statements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []
    responses = [
        SQLGenerationResult(
            sql="SELECT 1; SELECT 2",
            assumptions=[],
            confidence=0.25,
        ),
        SQLGenerationResult(
            sql="SELECT 1",
            assumptions=[],
            confidence=0.4,
        ),
    ]

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def fake_resolve_ollama_model(client) -> str:
        return "test-model"

    async def fake_request_sql_generation(client, model: str, prompt: str) -> SQLGenerationResult:
        prompts.append(prompt)
        return responses.pop(0)

    monkeypatch.setattr(ollama_service.httpx, "AsyncClient", lambda timeout: DummyClient())
    monkeypatch.setattr(ollama_service, "resolve_ollama_model", fake_resolve_ollama_model)
    monkeypatch.setattr(ollama_service, "_request_sql_generation", fake_request_sql_generation)

    result = await ollama_service.generate_sql_from_question(
        question="Show me one row",
        schema_summary="TABLE customers: CustomerId INTEGER PRIMARY KEY",
    )

    assert result.sql == "SELECT 1"
    assert len(prompts) == 2
    assert "Multiple statements are not allowed" in prompts[1]


@pytest.mark.anyio
async def test_generate_sql_from_question_retries_when_schema_verifier_rejects_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []
    responses = [
        SQLGenerationResult(
            sql="SELECT CustomerId FROM invoice_items",
            assumptions=[],
            confidence=0.25,
        ),
        SQLGenerationResult(
            sql="SELECT InvoiceId FROM invoice_items",
            assumptions=[],
            confidence=0.45,
        ),
    ]

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def fake_resolve_ollama_model(client) -> str:
        return "test-model"

    async def fake_request_sql_generation(client, model: str, prompt: str) -> SQLGenerationResult:
        prompts.append(prompt)
        return responses.pop(0)

    def fake_verifier(sql: str) -> None:
        if sql == "SELECT CustomerId FROM invoice_items":
            raise ValueError("no such column: CustomerId")

    monkeypatch.setattr(ollama_service.httpx, "AsyncClient", lambda timeout: DummyClient())
    monkeypatch.setattr(ollama_service, "resolve_ollama_model", fake_resolve_ollama_model)
    monkeypatch.setattr(ollama_service, "_request_sql_generation", fake_request_sql_generation)

    result = await ollama_service.generate_sql_from_question(
        question="Show one invoice item id",
        schema_summary="TABLE invoice_items: InvoiceLineId INTEGER PRIMARY KEY, InvoiceId INTEGER",
        verifier=fake_verifier,
    )

    assert result.sql == "SELECT InvoiceId FROM invoice_items"
    assert len(prompts) == 2
    assert "no such column: CustomerId" in prompts[1]
