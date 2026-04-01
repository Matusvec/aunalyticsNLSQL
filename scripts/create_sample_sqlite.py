#!/usr/bin/env python3
"""Create a small sample SQLite database at samples/sample.sqlite"""
import sqlite3
from pathlib import Path


SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = SAMPLES_DIR / "sample.sqlite"

def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS people (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")
    cur.execute("DELETE FROM people")
    cur.executemany("INSERT INTO people (id, name, age) VALUES (?, ?, ?)",
                    [(1, "Alice", 30), (2, "Bob", 25)])
    conn.commit()
    conn.close()
    print(f"Created sample sqlite: {DB_PATH}")


if __name__ == "__main__":
    main()
