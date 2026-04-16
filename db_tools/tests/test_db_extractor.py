import json
import sqlite3
from pathlib import Path

import pytest

# CHANGED: Added 'db_tools.' so Python knows where to look from the root folder
from db_tools.db_extractor import SQLiteExtractor, format_schema_to_json

def create_sample_db(path: str):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    cur.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, content TEXT)")
    cur.execute("INSERT INTO users (name, email) VALUES ('alice', 'alice@example.com')")
    cur.execute("INSERT INTO posts (user_id, content) VALUES (1, 'hello world')")
    conn.commit()
    conn.close()

def test_sqlite_extractor_schema_and_samples(tmp_path: Path):
    db_file = tmp_path / "test.db"
    create_sample_db(str(db_file))

    extractor = SQLiteExtractor(str(db_file))
    schema = extractor.get_schema_dict(include_samples=True, sample_limit=1)

    assert "tables" in schema
    assert "users" in schema["tables"]
    assert "posts" in schema["tables"]

    users_cols = [c["name"] for c in schema["tables"]["users"]["columns"]]
    assert set(users_cols) >= {"id", "name", "email"}

    assert "rows" in schema["tables"]["users"]
    assert isinstance(schema["tables"]["users"]["rows"], list)

# COMPLETED: Finished the cut-off test code below
def test_format_schema_to_json_roundtrip(tmp_path: Path):
    db_file = tmp_path / "test2.db"
    create_sample_db(str(db_file))

    extractor = SQLiteExtractor(str(db_file))
    json_str = format_schema_to_json(extractor)

    parsed = json.loads(json_str)
    assert "tables" in parsed
    assert "users" in parsed["tables"]
    assert "posts" in parsed["tables"]