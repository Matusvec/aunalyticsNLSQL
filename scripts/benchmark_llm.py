"""Benchmark Ollama vs. Gemini on a fixed set of Chinook questions.

Usage:
    .venv/bin/python scripts/benchmark_llm.py                     # both providers
    .venv/bin/python scripts/benchmark_llm.py --provider ollama   # one provider
    .venv/bin/python scripts/benchmark_llm.py --provider gemini

Ground truth was computed against backend/db/chinook.db; see comments below.
Each case declares the expected result set (as a set of tuples) so the check is
execution-based: column names and row order do not matter, values do.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True), override=False)

from app.services import gemini_service  # noqa: E402
from app.services.ask_service import ask_question  # noqa: E402


logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

DB_FILENAME = "chinook.db"


@dataclass
class Case:
    name: str
    question: str
    # Expected rows as a set of tuples. Each tuple's values must all appear
    # (as a frozenset) in some returned row. If `single_value` is set we only
    # check the first row's first column.
    expected_rows: set[tuple[Any, ...]] = field(default_factory=set)
    expected_single_value: Any = None
    # Optional substring checks on the generated SQL.
    sql_must_contain: tuple[str, ...] = ()
    sql_must_not_contain: tuple[str, ...] = ()


CASES: list[Case] = [
    Case(
        name="count_usa_customers",
        question="How many customers are from the USA?",
        expected_single_value=13,
    ),
    Case(
        name="total_artists",
        question="How many artists are in the database?",
        expected_single_value=275,
    ),
    Case(
        name="total_tracks",
        question="How many tracks total?",
        expected_single_value=3503,
    ),
    Case(
        name="top_3_spenders",
        question="Who are the top 3 customers by total spending?",
        expected_rows={("Helena",), ("Richard",), ("Luis",)},
        sql_must_contain=("GROUP BY", "DESC", "LIMIT"),
    ),
    Case(
        name="bottom_3_spenders",
        question="Who are the bottom 3 customers by total spending?",
        expected_rows={("Puja",), ("Leonie",), ("Daan",)},
        sql_must_contain=("GROUP BY", "ASC", "LIMIT"),
        sql_must_not_contain=("DESC",),
    ),
    Case(
        name="longest_track",
        question="What is the name of the longest track?",
        expected_single_value="Occupation / Precipice",
    ),
    Case(
        name="tracks_per_genre_top3",
        question="Show the top 3 genres with the most tracks",
        expected_rows={("Rock", 1297), ("Latin", 579), ("Metal", 374)},
        sql_must_contain=("GROUP BY", "COUNT", "LIMIT"),
    ),
    Case(
        name="countries_with_customers",
        question="How many distinct countries have customers?",
        expected_single_value=24,
        sql_must_contain=("DISTINCT",),
    ),
    Case(
        name="most_prolific_artist",
        question="Which artist has the most albums?",
        expected_rows={("Iron Maiden",)},
        sql_must_contain=("GROUP BY", "LIMIT"),
    ),
    Case(
        name="rock_track_count",
        question="How many tracks are in the Rock genre?",
        expected_single_value=1297,
    ),
    Case(
        name="top_country_revenue",
        question="Which country has the highest total invoice revenue?",
        expected_rows={("USA",)},
        sql_must_contain=("GROUP BY",),
    ),
    Case(
        name="invoices_in_2009",
        question="How many invoices were issued in 2009?",
        expected_single_value=83,
    ),
    Case(
        name="playlists_count",
        question="How many playlists exist?",
        expected_single_value=18,
    ),
    Case(
        name="employees_count",
        question="How many employees are there?",
        expected_single_value=8,
    ),
]


@dataclass
class RunResult:
    case: str
    provider: str
    success: bool
    sql: str
    rows: list[dict[str, Any]]
    latency_seconds: float
    error: str | None = None
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)


def _row_value_set(rows: list[dict[str, Any]]) -> set[tuple[Any, ...]]:
    out: set[tuple[Any, ...]] = set()
    for row in rows:
        values = tuple(str(v) if v is not None else None for v in row.values())
        out.add(values)
    return out


def _check_expected(case: Case, rows: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []

    if case.expected_single_value is not None:
        if rows and rows[0]:
            actual = list(rows[0].values())[0]
            try:
                ok = actual == case.expected_single_value or str(actual) == str(
                    case.expected_single_value
                )
            except Exception:
                ok = False
            (passed if ok else failed).append(
                f"single_value expected={case.expected_single_value!r} got={actual!r}"
            )
        else:
            failed.append(f"single_value expected={case.expected_single_value!r} got=(no rows)")

    if case.expected_rows:
        # Substring-anywhere match: every value of an expected tuple must
        # appear as a substring of some returned row's string form. Handles
        # cases where SQL concatenates FirstName + LastName into one column.
        row_blobs = [
            " | ".join("" if v is None else str(v) for v in row.values()) for row in rows
        ]
        missing: list[tuple[Any, ...]] = []
        for expected_tuple in case.expected_rows:
            ok = any(
                all(str(v) in blob for v in expected_tuple)
                for blob in row_blobs
            )
            if not ok:
                missing.append(expected_tuple)
        if missing:
            failed.append(f"missing expected rows: {missing}")
        else:
            passed.append(f"all {len(case.expected_rows)} expected rows present")

    return passed, failed


def _check_sql(case: Case, sql: str) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []
    upper = sql.upper()
    for token in case.sql_must_contain:
        if token.upper() in upper:
            passed.append(f"sql contains {token!r}")
        else:
            failed.append(f"sql missing {token!r}")
    for token in case.sql_must_not_contain:
        if token.upper() in upper:
            failed.append(f"sql unexpectedly contains {token!r}")
        else:
            passed.append(f"sql does not contain {token!r}")
    return passed, failed


async def run_case(case: Case, provider: str) -> RunResult:
    started = time.perf_counter()
    try:
        result = await ask_question(
            question=case.question,
            db_filename=DB_FILENAME,
            limit=50,
            provider=provider,
        )
    except Exception as exc:
        return RunResult(
            case=case.name,
            provider=provider,
            success=False,
            sql="",
            rows=[],
            latency_seconds=time.perf_counter() - started,
            error=f"{type(exc).__name__}: {exc}",
        )
    latency = time.perf_counter() - started

    sql_passed, sql_failed = _check_sql(case, result.sql)
    row_passed, row_failed = _check_expected(case, result.rows)
    all_failed = sql_failed + row_failed

    return RunResult(
        case=case.name,
        provider=provider,
        success=not all_failed,
        sql=result.sql,
        rows=result.rows,
        latency_seconds=latency,
        checks_passed=sql_passed + row_passed,
        checks_failed=all_failed,
    )


def format_report(results: list[RunResult]) -> str:
    by_provider: dict[str, list[RunResult]] = {}
    for r in results:
        by_provider.setdefault(r.provider, []).append(r)

    lines: list[str] = ["# LLM Benchmark Report\n"]
    lines.append("| case | " + " | ".join(by_provider.keys()) + " |")
    lines.append("|" + "|".join(["---"] * (len(by_provider) + 1)) + "|")

    case_names = [c.name for c in CASES]
    totals = {p: [0, 0, 0.0] for p in by_provider}  # passed, total, total_latency
    for name in case_names:
        row = [name]
        for provider, runs in by_provider.items():
            run = next((r for r in runs if r.case == name), None)
            if run is None:
                row.append("—")
                continue
            totals[provider][1] += 1
            totals[provider][2] += run.latency_seconds
            if run.error:
                row.append(f"❌ error")
            elif run.success:
                totals[provider][0] += 1
                row.append(f"✅ {run.latency_seconds:.1f}s")
            else:
                row.append(f"❌ {run.latency_seconds:.1f}s")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for provider, (p, t, lat) in totals.items():
        avg = lat / t if t else 0
        lines.append(
            f"- **{provider}** — {p}/{t} passed ({100 * p / t:.0f}%), avg {avg:.1f}s/case"
        )

    lines.append("")
    lines.append("## Failures")
    for provider, runs in by_provider.items():
        lines.append(f"\n### {provider}\n")
        any_fail = False
        for run in runs:
            if run.success and not run.error:
                continue
            any_fail = True
            lines.append(f"**{run.case}** — {'error' if run.error else 'wrong result'}")
            if run.error:
                lines.append(f"- error: `{run.error}`")
            if run.sql:
                lines.append(f"- sql: `{run.sql}`")
            for msg in run.checks_failed:
                lines.append(f"- ❌ {msg}")
            lines.append("")
        if not any_fail:
            lines.append("(none)\n")

    return "\n".join(lines)


async def main(providers: list[str]) -> int:
    if "gemini" in providers and not gemini_service.is_configured():
        print("ERROR: GEMINI_API_KEY not configured; skip --provider gemini", file=sys.stderr)
        return 2

    all_results: list[RunResult] = []
    for provider in providers:
        print(f"\n=== running {len(CASES)} cases against {provider} ===\n", flush=True)
        for case in CASES:
            print(f"  [{provider}] {case.name}... ", end="", flush=True)
            res = await run_case(case, provider)
            mark = "ok" if res.success and not res.error else "FAIL"
            print(f"{mark} ({res.latency_seconds:.1f}s)", flush=True)
            all_results.append(res)

    report = format_report(all_results)
    out_path = ROOT / "benchmark_report.md"
    out_path.write_text(report)
    print(f"\nReport written to {out_path}")
    print(report)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider",
        choices=["ollama", "gemini", "both"],
        default="both",
    )
    args = parser.parse_args()
    providers = ["ollama", "gemini"] if args.provider == "both" else [args.provider]
    raise SystemExit(asyncio.run(main(providers)))
