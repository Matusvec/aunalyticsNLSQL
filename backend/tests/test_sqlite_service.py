from __future__ import annotations

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import sqlite_service


def test_build_relevant_schema_summary_impl_prefers_question_matched_tables(monkeypatch) -> None:
    monkeypatch.setattr(
        sqlite_service,
        "list_tables_impl",
        lambda db_filename: ["albums", "customers", "invoice_items", "tracks"],
    )

    table_map = {
        "albums": {"table": "albums", "columns": [{"name": "AlbumId", "type": "INTEGER", "primary_key": True}]},
        "customers": {
            "table": "customers",
            "columns": [
                {"name": "CustomerId", "type": "INTEGER", "primary_key": True},
                {"name": "FirstName", "type": "TEXT", "primary_key": False},
            ],
        },
        "invoice_items": {
            "table": "invoice_items",
            "columns": [
                {"name": "InvoiceId", "type": "INTEGER", "primary_key": False},
                {"name": "UnitPrice", "type": "NUMERIC", "primary_key": False},
            ],
        },
        "tracks": {"table": "tracks", "columns": [{"name": "TrackId", "type": "INTEGER", "primary_key": True}]},
    }

    monkeypatch.setattr(
        sqlite_service,
        "describe_table_impl",
        lambda db_filename, table_name: table_map[table_name],
    )

    summary = sqlite_service.build_relevant_schema_summary_impl(
        db_filename="chinook.db",
        question="Show customer invoice totals",
        max_tables=2,
    )

    assert "TABLE customers:" in summary
    assert "TABLE invoice_items:" in summary
    assert "TABLE albums:" not in summary
    assert "TABLE tracks:" not in summary
    assert "Available tables in this database (use only these table names): albums, customers, invoice_items, tracks" in summary
    assert "Other available tables (names only): albums, tracks" in summary


def test_build_relevant_schema_summary_impl_includes_all_table_names_when_schema_is_small(monkeypatch) -> None:
    monkeypatch.setattr(
        sqlite_service,
        "list_tables_impl",
        lambda db_filename: ["albums", "tracks"],
    )

    table_map = {
        "albums": {"table": "albums", "columns": [{"name": "AlbumId", "type": "INTEGER", "primary_key": True}]},
        "tracks": {"table": "tracks", "columns": [{"name": "TrackId", "type": "INTEGER", "primary_key": True}]},
    }

    monkeypatch.setattr(
        sqlite_service,
        "describe_table_impl",
        lambda db_filename, table_name: table_map[table_name],
    )

    summary = sqlite_service.build_relevant_schema_summary_impl(
        db_filename="chinook.db",
        question="Show tracks",
        max_tables=6,
    )

    assert "Available tables in this database (use only these table names): albums, tracks" in summary
    assert "TABLE albums:" in summary
    assert "TABLE tracks:" in summary
