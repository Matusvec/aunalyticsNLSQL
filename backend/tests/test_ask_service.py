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
    # Force the static-schema flow for this test — the tool-calling path is covered separately.
    monkeypatch.setenv("LLM_USE_TOOLS", "false")
    from app.settings import reload_settings
    reload_settings()

    verifier_calls: list[str] = []
    execution_calls: list[tuple[str, str, int]] = []

    async def fake_build_relevant_schema_summary(db_filename: str, question: str):
        return "TABLE invoice_items: InvoiceId INTEGER"

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

    async def fake_validate_sql_compiles(db_filename: str, sql: str) -> None:
        verifier_calls.append(f"{db_filename}:{sql}")

    async def fake_run_sql_readonly(db_filename: str, sql: str, limit: int = 200):
        execution_calls.append((db_filename, sql, limit))
        return {
            "columns": ["InvoiceId"],
            "rows": [{"InvoiceId": 1}],
            "row_count": 1,
            "limit_applied": limit,
        }

    monkeypatch.setattr(ask_service, "build_relevant_schema_summary", fake_build_relevant_schema_summary)
    monkeypatch.setattr(ask_service, "generate_sql_from_question", fake_generate_sql_from_question)
    monkeypatch.setattr(ask_service, "validate_sql_compiles_impl", fake_validate_sql_compiles_impl)
    monkeypatch.setattr(ask_service, "run_sql_readonly_impl", fake_run_sql_readonly_impl)
    monkeypatch.setattr(ask_service, "validate_sql_compiles", fake_validate_sql_compiles)
    monkeypatch.setattr(ask_service, "run_sql_readonly", fake_run_sql_readonly)

    result = await ask_service.ask_question(
        question="Show invoice ids",
        db_filename="chinook.db",
        limit=5,
    )

    assert result.sql == "SELECT InvoiceId FROM invoice_items"
    # Verifier ran inside generate_sql, then the post-generation pipeline ran the
    # async validate + execute pair once each.
    assert verifier_calls == [
        "chinook.db:SELECT InvoiceId FROM invoice_items",  # verifier in generate_sql (compile)
        "chinook.db:SELECT InvoiceId FROM invoice_items",  # post-generation validate_sql_compiles
    ]
    assert execution_calls == [
        ("chinook.db", "SELECT InvoiceId FROM invoice_items", 1),  # verifier in generate_sql (run)
        ("chinook.db", "SELECT InvoiceId FROM invoice_items", 5),  # final post-generation execute
    ]
