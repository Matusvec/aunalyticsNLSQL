from __future__ import annotations

import sqlglot
from sqlglot import exp


FORBIDDEN_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.TruncateTable,
)


def validate_readonly_sql(sql: str) -> None:
    """
    Raise ValueError if SQL is invalid or not read-only.
    """
    try:
        parsed = sqlglot.parse_one(sql, read="sqlite")
    except Exception as exc:
        raise ValueError(f"Invalid SQL syntax: {exc}") from exc

    if isinstance(parsed, FORBIDDEN_EXPRESSIONS):
        raise ValueError("Only read-only SELECT queries are allowed")

    if not isinstance(parsed, (exp.Select, exp.Union, exp.With)):
        # Some CTEs still parse through With wrapping a Select
        if not parsed.find(exp.Select):
            raise ValueError("Query must be a SELECT or WITH ... SELECT")

    if ";" in sql.strip().rstrip(";"):
        raise ValueError("Multiple statements are not allowed")