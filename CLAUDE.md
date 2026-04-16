# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

./start_dev_services.sh              # uvicorn on 127.0.0.1:8000
.venv/bin/python -m pytest backend/tests db_tools/tests   # full test suite
```

`start_dev_services.sh` picks Python in this order: `.venv` at repo root, `backend/.venv`, then `py`/`python`/`python3` on PATH. `run_tests.sh` has the opposite preference (system python first), so prefer invoking pytest through the venv directly when deps aren't on the system Python.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local          # point NEXT_PUBLIC_API_URL at the backend
npm run dev                          # Next.js 16 on :3000
npm run build                        # production build
npm run test                         # vitest
```

### Environment

Copy `.env.example` to `.env` (repo root) to set `GEMINI_API_KEY` — the Gemini fallback activates automatically when Ollama is unreachable. `.env` is gitignored.

## Architecture

FastAPI backend + Next.js frontend. Turns natural-language questions into safe, read-only SQL against user-uploaded SQLite databases. Local Ollama is the primary LLM; Gemini is a fallback.

### Ask flow (`POST /api/ask`)

`backend/app/routers/query.py` → `ask_service.ask_question()`:

1. **Schema context** — `sqlite_service.build_relevant_schema_summary_impl()` reads `sqlite_master` + `PRAGMA table_info`, scores tables against the question, and returns a compact `TABLE name: col type, ...` string.
2. **LLM generation** — `ollama_service.generate_sql_from_question()` posts to `localhost:11434/api/chat` with structured output (`format` = `SQLGenerationResult` JSON schema). Model selection: `OLLAMA_MODEL` env var, else first available from `PREFERRED_OLLAMA_MODELS`. Two attempts with timeouts `45s` → `180s`; on validation or compile failure the last SQL + error + alias-specific guidance are fed back as a repair prompt.
3. **Gemini fallback** — if Ollama raises `httpx.ConnectError` (server not running), `_try_gemini_fallback()` delegates to `gemini_service.generate_sql_via_gemini()` when `GEMINI_API_KEY` is set. Default model is `gemini-2.5-flash`; override with `GEMINI_MODEL`.
4. **Validation + execution** — `sql_validator.validate_readonly_sql()` uses `sqlglot` (sqlite dialect) to reject anything that isn't `SELECT` / `WITH … SELECT` or contains Insert/Update/Delete/Create/Drop/Alter/Pragma/Vacuum/Attach/Detach/Transaction. Then `validate_sql_compiles_impl()` runs `EXPLAIN QUERY PLAN` to catch missing tables/columns. Finally `run_sql_readonly_impl()` executes with `fetchmany(limit)` (limit clamped to `[1, 1000]`).
5. **History** — `history_service.log_successful_query()` appends `{question, sql, confidence, status, timestamp}` to `backend/db/query_history.sqlite` (auto-created, gitignored).

### Routes

- `POST /api/ask` — question → SQL → execute → rows (logs to history).
- `POST /api/generate-sql` — same pipeline, returns SQL + assumptions + confidence without executing.
- `POST /api/execute` — client-supplied SQL; still passes through `validate_readonly_sql` + `validate_sql_compiles_impl`.
- `GET /api/schema/{db_filename}` / `GET /api/schema-summary/{db_filename}` — full schema / compact summary.
- `GET /api/databases` — lists files in `backend/db/` with size metadata.
- `POST /api/upload` — multipart upload of `.sqlite` / `.db` / `.csv` / `.json`; CSV/JSON converted to SQLite via pandas.
- `GET /api/history` — last N logged questions.

### Security invariants

- Every SQL string reaching SQLite **must** pass both `validate_readonly_sql` (AST check) and `validate_sql_compiles_impl` (EXPLAIN QUERY PLAN). `/api/execute` relies entirely on these checks.
- Every `db_filename` **must** go through `sqlite_service.safe_db_path()`, which resolves the path and asserts it stays under `backend/db/`.
- The `PRAGMA table_info(...)` call in `describe_table_impl` interpolates the table name, but the name comes from `sqlite_master` — never accept user-supplied table names there.

### Layout

- `backend/app/main.py` — FastAPI app, CORS middleware (`CORS_ORIGINS` env var), mounts routers under `/api`.
- `backend/app/routers/` — `query.py` (ask/generate-sql/execute/history), `schema.py`, `upload.py` (upload + list databases).
- `backend/app/services/` — `ask_service`, `ollama_service`, `gemini_service`, `sqlite_service`, `sql_validator`, `history_service`.
- `frontend/` — Next.js 16 app router. `app/page.tsx` renders `HomePage` (sidebar schema + database picker + upload + query panel + history panel). Components in `components/`, shadcn primitives in `components/ui/`, hooks in `hooks/`, API client in `lib/api.ts`.
- `db_tools/` — standalone `SQLiteExtractor` adapter that dumps schema (and optional sample rows) to JSON. CLI: `python3 db_tools/db_extractor.py --db … --out schema.json`.
- `backend_cli.py` — terminal client that lists `backend/db/`, picks one, loops on `/api/ask`.
- `strategy.md` — original design/roadmap; consult for product intent, not day-to-day code.

## Repo conventions

- Python 3 with `from __future__ import annotations` throughout; Pydantic v2.
- `.env`, `.venv/`, `node_modules/`, `__pycache__`, `.pytest_cache`, `.codex`, `backend/db/query_history.sqlite` are gitignored.
- Next.js 16 with React 19 — all interactive components need `"use client"`.
- Frontend styled with Tailwind 4 + shadcn. New components should follow existing shadcn patterns in `components/ui/`.
