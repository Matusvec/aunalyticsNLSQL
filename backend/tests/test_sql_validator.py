from __future__ import annotations

import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.sql_validator import validate_readonly_sql
from app.services.sqlite_service import run_sql_readonly_impl, validate_sql_compiles_impl


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO customers (FirstName) VALUES ('Alice')",
        "UPDATE customers SET FirstName = 'Alice' WHERE CustomerId = 1",
        "DELETE FROM customers WHERE CustomerId = 1",
        "DROP TABLE customers",
        "ALTER TABLE customers ADD COLUMN test TEXT",
        "CREATE TABLE test (id INTEGER)",
        "ATTACH DATABASE 'other.db' AS other",
        "DETACH DATABASE other",
        "REINDEX customers",
        "VACUUM",
        "PRAGMA table_info(customers)",
        "SELECT 1; SELECT 2",
    ],
)
def test_validate_readonly_sql_rejects_unsafe_statements(sql: str) -> None:
    with pytest.raises(ValueError):
        validate_readonly_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT FirstName, LastName FROM customers ORDER BY CustomerId LIMIT 1",
        "WITH first_customer AS (SELECT FirstName, LastName FROM customers ORDER BY CustomerId LIMIT 1) SELECT * FROM first_customer",
    ],
)
def test_validate_readonly_sql_allows_select_queries(sql: str) -> None:
    validate_readonly_sql(sql)


def test_run_sql_readonly_impl_enforces_maximum_row_limit() -> None:
    result = run_sql_readonly_impl(
        db_filename="chinook.db",
        sql="SELECT * FROM customers",
        limit=5000,
    )

    assert result["limit_applied"] == 1000
    assert result["row_count"] <= result["limit_applied"]


def test_validate_sql_compiles_impl_rejects_unknown_column() -> None:
    with pytest.raises(ValueError, match="no such column: i.CustomerId"):
        validate_sql_compiles_impl(
            db_filename="chinook.db",
            sql=(
                "SELECT i.CustomerId "
                "FROM invoice_items AS i "
                "LIMIT 1"
            ),
        )
