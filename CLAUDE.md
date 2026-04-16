# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Install runtime + dev dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Start the FastAPI backend (from repo root):

```bash
./start_dev_services.sh          # Linux/macOS
.\start_dev_services.ps1         # Windows PowerShell
```

The script auto-discovers Python in this order: `.venv` at repo root, `backend/.venv`, then `py`/`python`/`python3` on PATH. It `cd`s into `backend/` and runs `uvicorn app.main:app --reload` on `127.0.0.1:8000` (override with `APP_HOST` / `APP_PORT` env vars). A virtualenv is optional, but requirements must be installed against whichever Python the script finds.

Run the full test suite:

```bash
./run_tests.sh                   # runs pytest -v -rA backend/tests
./run_tests.sh -k ask            # pass-through args go to pytest
```

Note: the README references `run_ask_tests.sh`, but the actual script is `run_tests.sh` and it runs all tests under `backend/tests`, not just the ask-route file.

Run a single test file or test:

```bash
./run_tests.sh backend/tests/test_sql_validator.py
./run_tests.sh backend/tests/test_ask_route.py::test_ask_success_path_returns_minimal_query_payload
```

Interactive terminal client (requires backend running):

```bash
python3 backend_cli.py
```

Lists SQLite files in `backend/db/`, prompts for a choice, then loops on `POST /api/ask`. Exits on `q`/`quit`/`exit`.

## Architecture

Single-service FastAPI backend that turns natural-language questions into read-only SQL against a local SQLite database, using a local Ollama LLM. There is no frontend in this repo; clients are either `backend_cli.py` or a separate frontend consuming the HTTP API.

### Request flow (`POST /api/ask`)

`backend/app/routers/query.py` → `ask_service.ask_question()` → three-stage pipeline:

1. **Schema context** — `sqlite_service.build_schema_summary_impl()` reads `sqlite_master` + `PRAGMA table_info` and produces a compact `TABLE name: col type, ...` string. This is injected into the prompt; there is no MCP tool-loop (that was removed — see commit `8d68a6b`).
2. **LLM generation** — `ollama_service.generate_sql_from_question()` calls the local Ollama HTTP API at `localhost:11434` using structured output (`format` set to the `SQLGenerationResult` Pydantic JSON schema). Model is resolved once per process by calling `/api/tags` and picking the first of `PREFERRED_OLLAMA_MODELS` that's installed; `OLLAMA_MODEL` env var overrides. Generation has a built-in repair loop (`MAX_SQL_GENERATION_ATTEMPTS = 2`): on a validation/compile failure the previous output + error are fed back as a repair prompt.
3. **Validation + execution** — `sql_validator.validate_readonly_sql()` parses with `sqlglot` (sqlite dialect) and rejects anything that isn't a single `SELECT` / `WITH ... SELECT` or contains forbidden expression types (Insert/Update/Delete/Create/Drop/Alter/Pragma/Vacuum/Attach/Detach/Transaction/…). Then `validate_sql_compiles_impl()` runs `EXPLAIN QUERY PLAN` to catch missing tables/columns before execution. Finally `run_sql_readonly_impl()` executes and caps rows via `fetchmany(limit)` (limit clamped to `[1, 1000]`).

### Other routes

- `POST /api/generate-sql` — same as `/ask` but returns the SQL + assumptions + confidence without executing. Uses the same validation gates.
- `POST /api/execute` — runs arbitrary SQL already provided by the client; it still goes through `validate_readonly_sql` + `validate_sql_compiles_impl` first.
- `GET /api/schema/{db_filename}` and `GET /api/schema-summary/{db_filename}` — inspect available tables/columns. The `{db_filename}` path parameter is always resolved via `safe_db_path()` which blocks traversal outside `backend/db/`.

### Security-critical invariants

- Every SQL string that reaches SQLite **must** pass both `validate_readonly_sql` (sqlglot-based AST check) and `validate_sql_compiles_impl` (EXPLAIN QUERY PLAN). Don't bypass either — `/api/execute` is a user-supplied-SQL endpoint and relies entirely on these checks.
- Every `db_filename` **must** go through `sqlite_service.safe_db_path()`, which resolves the path and asserts it's still under `backend/db/`. Never open `sqlite3.connect()` directly on user input.
- The `PRAGMA table_info(...)` call in `describe_table_impl` interpolates the table name into SQL, but the name comes from `sqlite_master` (not user input) — keep it that way.

### Layout

- `backend/app/main.py` — FastAPI app factory, mounts routers under `/api`, exposes `/health`.
- `backend/app/routers/` — thin HTTP adapters; business logic lives in `services/`.
- `backend/app/services/` — `ask_service`, `ollama_service`, `sqlite_service`, `sql_validator`. Router code imports services with `from app.services.*` — tests add `backend/` to `sys.path` to make that work (see `backend/tests/test_ask_route.py`).
- `backend/db/` — committed SQLite fixtures (e.g., `chinook.db`). New databases dropped here are automatically pickable by the CLI and the API.
- `backend_cli.py`, `ollama_chat.py` — root-level standalone scripts; not part of the backend package.

## Repo conventions

- Python 3 with `from __future__ import annotations` throughout; Pydantic v2 models for request/response schemas.
- `.env`, `.venv/`, `__pycache__`, `.pytest_cache`, `.codex` are gitignored.
- `strategy.md` at repo root is a large design/strategy document — consult it for product intent, not day-to-day code changes.
