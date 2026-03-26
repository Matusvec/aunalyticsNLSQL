"""
Database schema extraction using the Adapter pattern.

SQLite is implemented here; add a PostgresExtractor later by subclassing
DatabaseExtractor and filling the same dict shape (see get_schema_dict docstrings).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from abc import ABC, abstractmethod


class DatabaseExtractor(ABC):
    """Abstract base for database-specific schema extractors."""

    @abstractmethod
    def get_schema_dict(self) -> dict:
        """
        Return a JSON-serializable schema description.

        Contract (all subclasses should honor this shape):

        {
            "database": str,  # connection label or file path
            "tables": [
                {
                    "name": str,
                    "columns": [
                        {
                            "name": str,
                            "type": str,
                            "notnull": bool,
                            "pk": bool,
                            "default": str | None,
                        },
                        ...
                    ],
                },
                ...
            ],
        }
        """
        raise NotImplementedError


class SQLiteExtractor(DatabaseExtractor):
    """
    Extracts table/column metadata from a SQLite file via sqlite_master and PRAGMA.

    For Postgres/Supabase later: subclass DatabaseExtractor and query
    information_schema.columns (and related catalogs) instead of sqlite_master
    and PRAGMA table_info, but emit the same keys under "tables" / "columns".
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = os.path.abspath(db_path)
        if not os.path.isfile(self._db_path):
            raise FileNotFoundError(f"SQLite database file not found: {self._db_path}")

    def get_schema_dict(self) -> dict:
        tables: list[dict] = []

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # User-defined tables only (exclude sqlite internal objects)
            cur.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
            table_names = [row["name"] for row in cur.fetchall()]

            for table_name in table_names:
                # Quote identifiers so odd table names remain valid SQL tokens.
                cur.execute(f"PRAGMA table_info({self._quote_ident(table_name)})")
                columns: list[dict] = []
                for row in cur.fetchall():
                    # PRAGMA table_info: cid, name, type, notnull, dflt_value, pk
                    columns.append(
                        {
                            "name": row[1],
                            "type": (row[2] or ""),
                            "notnull": bool(row[3]),
                            "pk": bool(row[5]),
                            "default": row[4],
                        }
                    )
                tables.append({"name": table_name, "columns": columns})

        return {"database": self._db_path, "tables": tables}

    @staticmethod
    def _quote_ident(name: str) -> str:
        """Quote a SQLite identifier for use in PRAGMA (escape embedded ")."""
        escaped = name.replace('"', '""')
        return f'"{escaped}"'


def format_schema_to_json(extractor: DatabaseExtractor) -> str:
    """Serialize any extractor's schema dict to a cleanly indented JSON string."""
    return json.dumps(
        extractor.get_schema_dict(),
        indent=2,
        ensure_ascii=False,
    )


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python schema_extractor.py <path_to_sqlite.db>", file=sys.stderr)
        sys.exit(1)
    extractor = SQLiteExtractor(sys.argv[1])
    print(format_schema_to_json(extractor))


if __name__ == "__main__":
    main()
