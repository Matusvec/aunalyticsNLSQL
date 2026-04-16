from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import ollama_service
from app.services.ollama_service import SQLGenerationError, SQLGenerationResult


@pytest.mark.anyio
async def test_generate_sql_from_question_retries_when_model_returns_multiple_statements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[tuple[str, float]] = []
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

    async def fake_request_sql_generation(
        client,
        model: str,
        prompt: str,
        timeout_seconds: float,
    ) -> SQLGenerationResult:
        prompts.append((prompt, timeout_seconds))
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
    assert prompts[0][1] == 45.0
    assert prompts[1][1] == 180.0
    assert "Prefer a single SELECT with explicit JOIN clauses over a CTE" in prompts[0][0]
    assert "Format SQL clearly with one major clause per line" in prompts[0][0]
    assert "ORDER BY TotalSpentOnRock DESC" in prompts[0][0]
    assert "Fix the failed SQL" in prompts[1][0]
    assert "Last SQL: SELECT 1; SELECT 2" in prompts[1][0]
    assert "Error: Multiple statements are not allowed" in prompts[1][0]
    assert "Do not repeat the same mistake" in prompts[1][0]
    assert "Take enough time to verify table names, aliases, and column names" in prompts[1][0]
    assert "Prefer a single SELECT with explicit JOIN clauses over a CTE" in prompts[1][0]


@pytest.mark.anyio
async def test_generate_sql_from_question_retries_when_schema_verifier_rejects_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[tuple[str, float]] = []
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

    async def fake_request_sql_generation(
        client,
        model: str,
        prompt: str,
        timeout_seconds: float,
    ) -> SQLGenerationResult:
        prompts.append((prompt, timeout_seconds))
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
    assert prompts[0][1] == 45.0
    assert prompts[1][1] == 180.0
    assert "Fix the failed SQL" in prompts[1][0]
    assert "Last SQL: SELECT CustomerId FROM invoice_items" in prompts[1][0]
    assert "Error: no such column: CustomerId" in prompts[1][0]
    assert "Correct the specific mistake shown in the error" in prompts[1][0]
    assert "Failure-specific guidance:" in prompts[1][0]
    assert "one JOIN per line and ORDER BY before LIMIT" in prompts[1][0]


@pytest.mark.anyio
async def test_generate_sql_from_question_stops_after_two_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[tuple[str, float]] = []
    responses = [
        SQLGenerationResult(sql="SELECT bad_column FROM invoice_items", assumptions=[], confidence=0.2),
        SQLGenerationResult(sql="SELECT still_bad FROM invoice_items", assumptions=[], confidence=0.2),
    ]

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def fake_resolve_ollama_model(client) -> str:
        return "test-model"

    async def fake_request_sql_generation(
        client,
        model: str,
        prompt: str,
        timeout_seconds: float,
    ) -> SQLGenerationResult:
        prompts.append((prompt, timeout_seconds))
        return responses.pop(0)

    def fake_verifier(sql: str) -> None:
        raise ValueError(f"bad sql: {sql}")

    monkeypatch.setattr(ollama_service.httpx, "AsyncClient", lambda timeout: DummyClient())
    monkeypatch.setattr(ollama_service, "resolve_ollama_model", fake_resolve_ollama_model)
    monkeypatch.setattr(ollama_service, "_request_sql_generation", fake_request_sql_generation)

    with pytest.raises(ValueError, match="bad sql: SELECT still_bad FROM invoice_items"):
        await ollama_service.generate_sql_from_question(
            question="broken",
            schema_summary="TABLE invoice_items: InvoiceId INTEGER",
            verifier=fake_verifier,
        )

    assert len(prompts) == 2
    assert prompts[0][1] == 45.0
    assert prompts[1][1] == 180.0


@pytest.mark.anyio
async def test_generate_sql_from_question_retries_with_longer_timeout_after_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[tuple[str, float]] = []

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def fake_resolve_ollama_model(client) -> str:
        return "test-model"

    async def fake_request_sql_generation(
        client,
        model: str,
        prompt: str,
        timeout_seconds: float,
    ) -> SQLGenerationResult:
        prompts.append((prompt, timeout_seconds))
        if len(prompts) == 1:
            raise httpx.TimeoutException("timed out")
        return SQLGenerationResult(
            sql="SELECT InvoiceId FROM invoice_items",
            assumptions=["Assumed invoice_items is the relevant table."],
            confidence=0.41,
        )

    monkeypatch.setattr(ollama_service.httpx, "AsyncClient", lambda timeout: DummyClient())
    monkeypatch.setattr(ollama_service, "resolve_ollama_model", fake_resolve_ollama_model)
    monkeypatch.setattr(ollama_service, "_request_sql_generation", fake_request_sql_generation)

    result = await ollama_service.generate_sql_from_question(
        question="Show invoice ids",
        schema_summary="TABLE invoice_items: InvoiceId INTEGER",
    )

    assert result.sql == "SELECT InvoiceId FROM invoice_items"
    assert len(prompts) == 2
    assert prompts[0][1] == 45.0
    assert prompts[1][1] == 180.0
    assert "Timed out after 45s before producing SQL" in prompts[1][0]
    assert "Take enough time to verify table names, aliases, and column names" in prompts[1][0]


@pytest.mark.anyio
async def test_generate_sql_from_question_adds_alias_guidance_for_bad_alias_columns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[tuple[str, float]] = []
    responses = [
        SQLGenerationResult(
            sql="SELECT i.CustomerId FROM invoice_items AS i",
            assumptions=[],
            confidence=0.2,
        ),
        SQLGenerationResult(
            sql="SELECT i.InvoiceId FROM invoice_items AS i",
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

    async def fake_request_sql_generation(
        client,
        model: str,
        prompt: str,
        timeout_seconds: float,
    ) -> SQLGenerationResult:
        prompts.append((prompt, timeout_seconds))
        return responses.pop(0)

    def fake_verifier(sql: str) -> None:
        if sql == "SELECT i.CustomerId FROM invoice_items AS i":
            raise ValueError("no such column: i.CustomerId")

    monkeypatch.setattr(ollama_service.httpx, "AsyncClient", lambda timeout: DummyClient())
    monkeypatch.setattr(ollama_service, "resolve_ollama_model", fake_resolve_ollama_model)
    monkeypatch.setattr(ollama_service, "_request_sql_generation", fake_request_sql_generation)

    result = await ollama_service.generate_sql_from_question(
        question="Show one invoice item id",
        schema_summary="TABLE invoice_items: InvoiceLineId INTEGER PRIMARY KEY, InvoiceId INTEGER",
        verifier=fake_verifier,
    )

    assert result.sql == "SELECT i.InvoiceId FROM invoice_items AS i"
    assert "i.CustomerId is invalid" in prompts[1][0]
    assert "A table alias does not create or rename columns" in prompts[1][0]
    assert "every `alias.column` reference must map to a real column" in prompts[1][0]


@pytest.mark.anyio
async def test_generate_sql_from_question_reports_second_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def fake_resolve_ollama_model(client) -> str:
        return "test-model"

    async def fake_request_sql_generation(
        client,
        model: str,
        prompt: str,
        timeout_seconds: float,
    ) -> SQLGenerationResult:
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(ollama_service.httpx, "AsyncClient", lambda timeout: DummyClient())
    monkeypatch.setattr(ollama_service, "resolve_ollama_model", fake_resolve_ollama_model)
    monkeypatch.setattr(ollama_service, "_request_sql_generation", fake_request_sql_generation)

    with pytest.raises(
        SQLGenerationError,
        match="SQL generation timed out after 180s on attempt 2 of 2",
    ):
        await ollama_service.generate_sql_from_question(
            question="Show invoice ids",
            schema_summary="TABLE invoice_items: InvoiceId INTEGER",
        )
