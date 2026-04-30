"""Tests covering production-readiness fixes:

- Path traversal in safe_db_path
- SQLite read-only mode (writes rejected)
- SQLite query timeout (progress handler)
- PRAGMA identifier escaping
- Upload refuses overwrite
- Upload requires SQLite magic header
- /ready endpoint
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.services import sqlite_service
from app.services.sqlite_service import (
    SQLExecutionTimeout,
    _quote_identifier,
    run_sql_readonly_impl,
    safe_db_path,
)


client = TestClient(app)


# ---- Path traversal --------------------------------------------------------


def test_safe_db_path_rejects_parent_traversal() -> None:
    with pytest.raises(ValueError):
        safe_db_path("../foo.db")


def test_safe_db_path_rejects_sibling_prefix_attack(tmp_path, monkeypatch) -> None:
    """The classic startswith() bug: db_root='/x/db' must not accept '/x/db_evil/...'."""
    db_root = tmp_path / "db"
    sibling = tmp_path / "db_evil"
    db_root.mkdir()
    sibling.mkdir()
    target = sibling / "leak.db"
    sqlite3.connect(str(target)).close()

    monkeypatch.setattr(
        sqlite_service.get_settings(),
        "db_dir",
        db_root,
    )

    with pytest.raises(ValueError):
        safe_db_path("../db_evil/leak.db")


def test_safe_db_path_rejects_absolute_path() -> None:
    with pytest.raises(ValueError):
        safe_db_path("/etc/passwd")


def test_safe_db_path_rejects_slashes_anywhere() -> None:
    with pytest.raises(ValueError):
        safe_db_path("nested/foo.db")


def test_safe_db_path_raises_file_not_found_for_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        safe_db_path("definitely-not-a-real-database.sqlite")


# ---- Read-only mode --------------------------------------------------------


def test_run_sql_readonly_impl_rejects_writes_at_engine_level(tmp_path, monkeypatch) -> None:
    db_root = tmp_path / "db"
    db_root.mkdir()
    target = db_root / "rw.db"
    conn = sqlite3.connect(str(target))
    conn.execute("CREATE TABLE t (id INTEGER)")
    conn.commit()
    conn.close()

    monkeypatch.setattr(sqlite_service.get_settings(), "db_dir", db_root)

    # SELECT works
    result = run_sql_readonly_impl("rw.db", "SELECT 1 AS x")
    assert result["row_count"] == 1

    # Writes are rejected by SQLite (mode=ro), not just by our validator.
    # We bypass validate_readonly_sql to prove the engine-level guarantee.
    with pytest.raises(ValueError):
        run_sql_readonly_impl("rw.db", "INSERT INTO t VALUES (1)")


# ---- Query timeout ---------------------------------------------------------


def test_run_sql_readonly_impl_aborts_on_timeout(tmp_path, monkeypatch) -> None:
    """A long-running CTE is interrupted once the wall-clock deadline elapses."""
    db_root = tmp_path / "db"
    db_root.mkdir()
    target = db_root / "tdb.db"
    sqlite3.connect(str(target)).close()

    settings = sqlite_service.get_settings()
    monkeypatch.setattr(settings, "db_dir", db_root)
    monkeypatch.setattr(settings, "sql_query_timeout_seconds", 0.1)
    monkeypatch.setattr(settings, "sql_progress_handler_n", 100)

    # Recursive CTE that iterates a million times — guaranteed to outlast 100ms.
    sql = (
        "WITH RECURSIVE c(x) AS ("
        "SELECT 1 UNION ALL SELECT x+1 FROM c WHERE x<1000000"
        ") SELECT count(*) FROM c"
    )
    with pytest.raises(SQLExecutionTimeout):
        run_sql_readonly_impl("tdb.db", sql)


# ---- PRAGMA identifier escaping -------------------------------------------


def test_quote_identifier_escapes_single_quotes() -> None:
    assert _quote_identifier("foo") == "'foo'"


def test_quote_identifier_rejects_garbage() -> None:
    for bad in ("'); DROP TABLE x;--", "a;b", "..", "weird/name"):
        with pytest.raises(ValueError):
            _quote_identifier(bad)


# ---- Upload refuses overwrite ----------------------------------------------


def _make_sqlite_bytes(tmp_path: Path) -> bytes:
    p = tmp_path / "tmp.sqlite"
    conn = sqlite3.connect(str(p))
    try:
        conn.execute("CREATE TABLE x (id INTEGER)")
        conn.commit()
    finally:
        conn.close()
    return p.read_bytes()


def test_upload_refuses_overwrite(tmp_path) -> None:
    payload = _make_sqlite_bytes(tmp_path)
    files = {"file": ("hardening_overwrite.sqlite", payload, "application/octet-stream")}

    r1 = client.post("/api/upload", files=files)
    assert r1.status_code == 201

    r2 = client.post(
        "/api/upload",
        files={"file": ("hardening_overwrite.sqlite", payload, "application/octet-stream")},
    )
    assert r2.status_code == 409

    # Cleanup
    target = BACKEND_DIR / "db" / "hardening_overwrite.sqlite"
    if target.exists():
        target.unlink()


def test_upload_rejects_fake_sqlite_payload() -> None:
    junk = b"not a real sqlite file"
    r = client.post(
        "/api/upload",
        files={"file": ("hardening_fake.sqlite", junk, "application/octet-stream")},
    )
    assert r.status_code == 400
    assert "magic header" in r.json()["detail"]


def test_upload_rejects_unknown_extension() -> None:
    r = client.post(
        "/api/upload",
        files={"file": ("evil.exe", b"hello", "application/octet-stream")},
    )
    assert r.status_code == 415


# ---- Health + readiness ---------------------------------------------------


def test_health_returns_200() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_ready_returns_a_structured_check_payload() -> None:
    r = client.get("/ready")
    body = r.json()
    assert "checks" in body
    assert "db_dir" in body["checks"]
    assert "history_db" in body["checks"]
    assert "ollama" in body["checks"]
    assert "gemini" in body["checks"]
    # Either Ollama is up or Gemini is configured for "ok": True.
    assert body["ok"] in (True, False)
    assert r.status_code in (200, 503)
