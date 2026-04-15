from __future__ import annotations

import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import ask_service
from app.services.ollama_service import SQLGenerationResult


@pytest.mark.anyio
async def test_ask_question_verifier_executes_generated_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    verifier_calls: list[str] = []
    execution_calls: list[tuple[str, str, int]] = []

    monkeypatch.setattr(
        ask_service,
        "build_relevant_schema_summary_impl",
        lambda db_filename, question: "TABLE invoice_items: InvoiceId INTEGER",
    )

    async def fake_generate_sql_from_question(question: str, schema_summary: str, verifier):
        assert question == "Show invoice ids"
        assert schema_summary == "TABLE invoice_items: InvoiceId INTEGER"
        verifier("SELECT InvoiceId FROM invoice_items")
        return SQLGenerationResult(
            sql="SELECT InvoiceId FROM invoice_items",
            assumptions=[],
            confidence=0.8,
        )

    def fake_validate_sql_compiles_impl(db_filename: str, sql: str) -> None:
        verifier_calls.append(f"{db_filename}:{sql}")

    def fake_run_sql_readonly_impl(db_filename: str, sql: str, limit: int = 200):
        execution_calls.append((db_filename, sql, limit))
        return {
            "columns": ["InvoiceId"],
            "rows": [{"InvoiceId": 1}],
            "row_count": 1,
            "limit_applied": limit,
        }

    monkeypatch.setattr(ask_service, "generate_sql_from_question", fake_generate_sql_from_question)
    monkeypatch.setattr(ask_service, "validate_sql_compiles_impl", fake_validate_sql_compiles_impl)
    monkeypatch.setattr(ask_service, "run_sql_readonly_impl", fake_run_sql_readonly_impl)

    result = await ask_service.ask_question(
        question="Show invoice ids",
        db_filename="chinook.db",
        limit=5,
    )

    assert result.sql == "SELECT InvoiceId FROM invoice_items"
    assert verifier_calls == [
        "chinook.db:SELECT InvoiceId FROM invoice_items",
        "chinook.db:SELECT InvoiceId FROM invoice_items",
    ]
    assert execution_calls == [
        ("chinook.db", "SELECT InvoiceId FROM invoice_items", 1),
        ("chinook.db", "SELECT InvoiceId FROM invoice_items", 5),
    ]
