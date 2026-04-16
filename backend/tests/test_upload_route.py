from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

client = TestClient(app)


def db_path_for_stem(stem: str) -> Path:
    return BACKEND_DIR / "db" / f"{stem}.sqlite"


def cleanup_db(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def assert_table_has_columns(db_path: Path, table: str, expected_cols: list[str]) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info('{table}')")
        cols = [row[1] for row in cur.fetchall()]
        for c in expected_cols:
            assert c in cols
    finally:
        conn.close()


def test_list_databases() -> None:
    resp = client.get("/api/databases")
    assert resp.status_code == 200
    body = resp.json()
    assert "databases" in body
    assert isinstance(body["databases"], list)
    names = {d["filename"] for d in body["databases"]}
    assert "chinook.db" in names


def test_upload_csv_creates_sqlite(tmp_path: Path) -> None:
    stem = "testcsv"
    dest = db_path_for_stem(stem)
    cleanup_db(dest)

    csv_content = "id,name\n1,Alice\n2,Bob\n"
    files = {"file": (f"{stem}.csv", csv_content, "text/csv")}
    resp = client.post("/api/upload", files=files)

    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["filename"] == f"{stem}.sqlite"

    assert dest.exists()
    assert_table_has_columns(dest, stem, ["id", "name"])

    cleanup_db(dest)


def test_upload_json_creates_sqlite(tmp_path: Path) -> None:
    stem = "testjson"
    dest = db_path_for_stem(stem)
    cleanup_db(dest)

    items = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    json_content = json.dumps(items)
    files = {"file": (f"{stem}.json", json_content, "application/json")}
    resp = client.post("/api/upload", files=files)

    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["filename"] == f"{stem}.sqlite"

    assert dest.exists()
    assert_table_has_columns(dest, stem, ["a", "b"])

    cleanup_db(dest)


def test_upload_sqlite_saves_file(tmp_path: Path) -> None:
    stem = "testsqlite"
    dest = db_path_for_stem(stem)
    cleanup_db(dest)

    tmp_db = tmp_path / f"{stem}.sqlite"
    conn = sqlite3.connect(str(tmp_db))
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE demo (x INT, y TEXT)")
        cur.execute("INSERT INTO demo (x,y) VALUES (1,'z')")
        conn.commit()
    finally:
        conn.close()

    with open(tmp_db, "rb") as f:
        data = f.read()

    files = {"file": (f"{stem}.sqlite", data, "application/octet-stream")}
    resp = client.post("/api/upload", files=files)

    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["filename"] == f"{stem}.sqlite"

    assert dest.exists()

    conn = sqlite3.connect(str(dest))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='demo'")
        assert cur.fetchone() is not None
    finally:
        conn.close()

    cleanup_db(dest)
