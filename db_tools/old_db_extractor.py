#!/usr/bin/env python3
"""Adapter-pattern database schema extractor (SQLite implementation).

This module defines `DatabaseExtractor` (ABC), `SQLiteExtractor`, and
`format_schema_to_json()`.

The file is intentionally standalone and uses only the standard
library so it's easy to test and extend (e.g., add `PostgresExtractor`).
"""

import abc
import sqlite3
import json
from typing import Any, Dict, List


class DatabaseExtractor(abc.ABC):
    """Abstract base class for database schema extractors.

    Subclasses must implement `get_schema_dict()` and return a Python
    dictionary representing the schema.
    """

    @abc.abstractmethod
    def get_schema_dict(self, include_samples: bool = False, sample_limit: int = 0) -> Dict[str, Any]:
        raise NotImplementedError


class SQLiteExtractor(DatabaseExtractor):
    """SQLite implementation of DatabaseExtractor.

    Connects to a local SQLite file, reads `sqlite_master` for tables,
    and uses `PRAGMA table_info()` to gather column names and types.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_schema_dict(self, include_samples: bool = False, sample_limit: int = 0) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()

            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            rows = cur.fetchall()

            table_names = [r[0] for r in rows if not r[0].startswith("sqlite_")]

            schema: Dict[str, Any] = {"tables": {}}

            for table in table_names:
                cur.execute(f"PRAGMA table_info('{table}')")
                cols = []
                for col in cur.fetchall():
                    _, name, ctype, notnull, dflt_value, pk = col
                    cols.append({
                        "name": name,
                        "type": ctype,
                        "notnull": bool(notnull),
                        "default": dflt_value,
                        "pk": bool(pk),
                    })

                table_info: Dict[str, Any] = {"columns": cols}

                if include_samples and sample_limit > 0:
                    try:
                        cur.execute(f"SELECT * FROM '{table}' LIMIT {int(sample_limit)}")
                        sample_rows = cur.fetchall()
                        names = [d[0] for d in cur.description]
                        rows_list: List[Dict[str, Any]] = [dict(zip(names, row)) for row in sample_rows]
                    except Exception:
                        rows_list = []

                    table_info["rows"] = rows_list

                schema["tables"][table] = table_info

            return schema
        finally:
            conn.close()


def format_schema_to_json(extractor: DatabaseExtractor) -> str:
    """Format an extractor's schema dict as pretty JSON."""
    schema = extractor.get_schema_dict()
    return json.dumps(schema, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Extract SQLite schema (and optional samples) and output JSON.")
    p.add_argument("--db", required=True, help="Path to SQLite database file")
    p.add_argument("--out", help="Output JSON file path (if omitted, prints to stdout)")
    p.add_argument("--samples", type=int, default=0, help="Number of sample rows per table to include (default: 0)")
    args = p.parse_args()

    extractor = SQLiteExtractor(args.db)
    schema_json = format_schema_to_json(extractor) if args.samples == 0 else json.dumps(
        extractor.get_schema_dict(include_samples=True, sample_limit=args.samples), indent=2, ensure_ascii=False
    )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(schema_json)
        print(f"Wrote schema JSON to {args.out}")
    else:
        print(schema_json)
