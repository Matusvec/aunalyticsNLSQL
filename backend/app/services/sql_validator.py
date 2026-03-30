from __future__ import annotations

import sqlglot
from sqlglot import exp


FORBIDDEN_EXPRESSIONS = tuple(
    expression
    for expression in (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.TruncateTable,
        getattr(exp, "Attach", None),
        getattr(exp, "Detach", None),
        getattr(exp, "Pragma", None),
        getattr(exp, "Vacuum", None),
        getattr(exp, "Reindex", None),
        getattr(exp, "Command", None),
        getattr(exp, "Transaction", None),
    )
    if expression is not None
)


def _parse_readonly_sql(sql: str) -> exp.Expression:
    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except Exception as exc:
        raise ValueError(f"Invalid SQL syntax: {exc}") from exc

    if len(statements) != 1:
        raise ValueError("Multiple statements are not allowed")

    parsed = statements[0]
    if parsed is None:
        raise ValueError("Query must not be empty")

    if any(parsed.find(expression) for expression in FORBIDDEN_EXPRESSIONS):
        raise ValueError("Only read-only SELECT queries are allowed")

    if not isinstance(parsed, (exp.Select, exp.Union, exp.With)):
        # Some CTEs still parse through With wrapping a Select
        if not parsed.find(exp.Select):
            raise ValueError("Query must be a SELECT or WITH ... SELECT")
        raise ValueError("Only read-only SELECT queries are allowed")

    return parsed


def validate_readonly_sql(sql: str) -> None:
    """
    Raise ValueError if SQL is invalid or not read-only.
    """
    _parse_readonly_sql(sql)


def normalize_readonly_sql(sql: str) -> str:
    """
    Return a normalized single-statement read-only SQLite query.
    """
    parsed = _parse_readonly_sql(sql)
    return parsed.sql(dialect="sqlite")
