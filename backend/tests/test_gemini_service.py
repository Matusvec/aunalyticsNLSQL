from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import gemini_service  # noqa: E402
from app.services.gemini_service import (  # noqa: E402
    GeminiNotConfiguredError,
    _extract_json_object,
    generate_sql_via_gemini,
    is_configured,
)


def test_is_configured_false_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert is_configured() is False


def test_is_configured_true_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert is_configured() is True


@pytest.mark.anyio
async def test_generate_sql_via_gemini_raises_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(GeminiNotConfiguredError):
        await generate_sql_via_gemini(
            question="q", schema_summary="TABLE t: id INTEGER PRIMARY KEY"
        )


def test_extract_json_object_strips_fences() -> None:
    raw = '```json\n{"sql": "SELECT 1", "assumptions": [], "confidence": 0.9}\n```'
    assert _extract_json_object(raw) == {
        "sql": "SELECT 1",
        "assumptions": [],
        "confidence": 0.9,
    }


def test_extract_json_object_handles_prose_wrapper() -> None:
    raw = 'Here is the answer: {"sql": "SELECT 1", "assumptions": [], "confidence": 0.5} and hope this helps.'
    assert _extract_json_object(raw) == {
        "sql": "SELECT 1",
        "assumptions": [],
        "confidence": 0.5,
    }


@pytest.mark.anyio
async def test_generate_sql_via_gemini_validates_and_normalizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def fake_request(prompt: str, model: str, api_key: str) -> str:
        return '{"sql": "select 1", "assumptions": [], "confidence": 0.8}'

    monkeypatch.setattr(gemini_service, "_request_gemini", fake_request)

    calls: list[str] = []

    def verifier(sql: str) -> None:
        calls.append(sql)

    result = await generate_sql_via_gemini(
        question="one row",
        schema_summary="TABLE t: id INTEGER PRIMARY KEY",
        verifier=verifier,
    )

    assert result.sql == "SELECT 1"
    assert calls == ["SELECT 1"]
    assert result.confidence == 0.8
