# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

./start_dev_services.sh                     # uvicorn --reload on 127.0.0.1:8000 (dev only)
./start_prod_services.sh                    # gunicorn + uvicorn workers (production)
.venv/bin/python -m pytest backend/tests db_tools/tests   # full test suite
.venv/bin/python -m pytest backend/tests/test_ask_service.py -k repair   # single file / filter
./run_tests.sh -k ask                       # passes extra args to pytest
```

`start_dev_services.sh` picks Python in this order: `.venv` at repo root, `backend/.venv`, then `py`/`python`/`python3` on PATH. `run_tests.sh` has the opposite preference (system python first), so prefer invoking pytest through the venv directly when deps aren't on the system Python.

`start_prod_services.sh` requires a real venv (no system-python fallback) and runs `gunicorn` with `uvicorn.workers.UvicornWorker`. Workers, timeouts, host, and port come from env vars (`APP_WORKERS`, `APP_TIMEOUT`, `APP_HOST`, `APP_PORT`).

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local                  # NEXT_PUBLIC_API_URL points at the backend
npm run dev                                  # Next.js 16 on :3000
npm run build                                # production build (output: 'standalone')
npm run start                                # production server (post-build)
npm run test                                 # vitest
```

### Environment

Copy `.env.example` to `.env` (repo root). Settings flow through `backend/app/settings.py` (`pydantic-settings`), which loads `.env` and validates types at startup. All env vars are documented in `.env.example`.

## Architecture

FastAPI backend + Next.js frontend. Turns natural-language questions into safe, read-only SQL against user-uploaded SQLite databases. Local Ollama is the primary LLM; Gemini is a fallback.

### Settings (`backend/app/settings.py`)

`get_settings()` returns an `lru_cache`d `Settings` instance built from env / `.env`. Every service imports it instead of hard-coding paths or limits. Test code calls `reload_settings()` (auto-applied via `backend/tests/conftest.py`) to start each test with a fresh cache.

### Ask flow (`POST /api/ask`)

`backend/app/routers/query.py` → `ask_service.ask_question()`:

1. **Schema context** — `sqlite_service.build_relevant_schema_summary()` (async wrapper over `_impl`) reads `sqlite_master` + `PRAGMA table_info`, scores tables against the question, and returns a compact `TABLE name: col type, ...` string.
2. **LLM generation** — `ollama_service.generate_sql_from_question()` POSTs to `<OLLAMA_URL>/api/chat` with structured output (`format` = `SQLGenerationResult` JSON schema). Model selection: `OLLAMA_MODEL`, else first available from `PREFERRED_OLLAMA_MODELS` (`qwen2.5-coder:3b`, `phi3`, `qwen3`, `llama3.2`, `gemma3`). The resolved model is cached for `OLLAMA_MODEL_CACHE_TTL_SECONDS` and invalidated on connect errors. Two attempts with timeouts from `OLLAMA_ATTEMPT_TIMEOUTS` (default `45s,180s`); on validation or compile failure the last SQL + error + alias-specific guidance are fed back as a repair prompt.
3. **Gemini fallback** — if Ollama raises `httpx.ConnectError`, `_try_gemini_fallback()` delegates to `gemini_service.generate_sql_via_gemini()` when `GEMINI_API_KEY` is set.
4. **Validation + execution** — `sql_validator.validate_readonly_sql()` uses `sqlglot` (sqlite dialect) to reject anything that isn't `SELECT` / `WITH … SELECT` or contains forbidden statements. `sqlite_service.validate_sql_compiles_impl()` runs `EXPLAIN QUERY PLAN`. `sqlite_service.run_sql_readonly_impl()` opens the DB with `mode=ro&immutable=1`, installs a wall-clock progress handler (`SQL_QUERY_TIMEOUT_SECONDS`), and executes `fetchmany(limit)` (limit clamped to `[1, SQL_MAX_ROW_LIMIT]`).
5. **History** — `history_service.log_successful_query_async()` appends to `query_history.sqlite` (WAL mode + `busy_timeout=5000`). Path comes from `HISTORY_DB_PATH` or defaults to `<DB_DIR>/query_history.sqlite`.

All blocking SQLite work is wrapped in `asyncio.to_thread` so the async event loop never blocks. The sync `*_impl` variants remain available for callers that already run in a threadpool (e.g. the inner verifier callback).

### Routes

- `GET /health` — liveness probe (always 200 if the process is up).
- `GET /ready` — readiness probe; checks DB dir, history DB, and at least one of Ollama / Gemini. Returns 503 if no LLM backend is reachable.
- `POST /api/ask` — question → SQL → execute → rows (logs to history). Rate-limited via `RATE_LIMIT_ASK`.
- `POST /api/generate-sql` — same pipeline, returns SQL + assumptions + confidence without executing.
- `POST /api/execute` — client-supplied SQL; still passes through `validate_readonly_sql` + `validate_sql_compiles`. Rate-limited via `RATE_LIMIT_EXECUTE`.
- `GET /api/schema/{db_filename}` / `GET /api/schema-summary/{db_filename}` — full schema / compact summary.
- `GET /api/databases` — lists `.db`/`.sqlite` files in `DB_DIR` (excluding `query_history.sqlite`).
- `POST /api/upload` — multipart upload of `.sqlite` / `.db` / `.csv` / `.json`. CSV is streamed in chunks; JSON requires a top-level array of objects. Refuses to overwrite existing files (returns 409). Rejects fake SQLite payloads (magic-byte check). Rate-limited via `RATE_LIMIT_UPLOAD`.
- `GET /api/history` — last 50 logged questions.

### Security invariants

- Every SQL string reaching SQLite **must** pass both `validate_readonly_sql` (AST check) and `validate_sql_compiles_impl` (EXPLAIN QUERY PLAN). `/api/execute` relies entirely on these checks.
- SQLite connections are opened with `mode=ro&immutable=1` URI flags — defense-in-depth against parser bypasses.
- Every `db_filename` **must** go through `sqlite_service.safe_db_path()`, which uses `Path.is_relative_to()` (not a fragile `startswith`) and rejects slashes / `..`.
- `PRAGMA table_info(...)` calls go through `_quote_identifier()`, which validates the identifier against `^[A-Za-z_][A-Za-z0-9_ \-]{0,127}$` and SQL-escapes single quotes. Even malicious uploaded SQLite files cannot inject statements through table names.
- Long-running queries are aborted by a `set_progress_handler` deadline (`SQL_QUERY_TIMEOUT_SECONDS`).
- All blocking SQLite work runs in `asyncio.to_thread`; the loop is never blocked.
- Error responses are sanitized — internal exception messages never leak to clients. Look at server logs (request_id correlation) for the underlying error.
- IP-based rate limits (slowapi) are applied per route. Disable for tests via `limiter.enabled = False` (handled by `conftest.py`).
- Body size middleware caps non-upload requests at `MAX_REQUEST_BYTES`. Uploads go through `_read_capped` with `MAX_UPLOAD_BYTES` and `MAX_UPLOAD_ROWS`.

### Layout

- `backend/app/main.py` — FastAPI app, lifespan setup, CORS / rate-limit / body-size / request-id middleware, `/health` + `/ready`, mounts routers under `/api`.
- `backend/app/settings.py` — pydantic-settings `Settings` class. Single source of truth for config.
- `backend/app/logging_config.py` — JSON log formatter + `configure_logging()`. Honors `LOG_LEVEL` and `LOG_FORMAT`.
- `backend/app/middleware.py` — `RequestIDMiddleware` (assigns `x-request-id`, emits structured access log) + `BodySizeLimitMiddleware`.
- `backend/app/rate_limit.py` — single `slowapi.Limiter` instance + `rate(...)` decorator.
- `backend/app/routers/` — `query.py` (ask/generate-sql/execute/history), `schema.py`, `upload.py`.
- `backend/app/services/` — `ask_service`, `ollama_service`, `gemini_service`, `sqlite_service`, `sql_validator`, `history_service`. `sqlite_service` exposes both async and `_impl` variants.
- `frontend/` — Next.js 16 app router. `app/page.tsx` renders `HomePage`. `next.config.ts` sets `output: 'standalone'` and adds CSP / HSTS / X-Frame-Options / X-Content-Type-Options / Referrer-Policy / Permissions-Policy headers. The CSP `connect-src` includes `NEXT_PUBLIC_API_URL` so the browser can reach the backend.
- `db_tools/` — standalone `SQLiteExtractor` adapter that dumps schema (+ optional sample rows) to JSON. CLI: `python3 db_tools/db_extractor.py --db … --out schema.json`.
- `backend_cli.py` — terminal client that lists `DB_DIR`, picks one, loops on `/api/ask`.
- `deploy/` — `aunalytics-backend.service` + `aunalytics-frontend.service` systemd units (with sandboxing) and `nginx.conf.example` (HTTPS termination, per-zone `limit_req`, sane proxy timeouts for the LLM-backed endpoints).
- `strategy.md` — original design/roadmap; consult for product intent, not day-to-day code.

## Production deployment

1. Create `.env` from `.env.example` and set `GEMINI_API_KEY`, override `CORS_ORIGINS` for your domain, set `DB_DIR` to a persistent path outside the repo (e.g. `/var/lib/aunalytics/db`).
2. Create a venv at the repo root and install `requirements.txt` (gunicorn is included).
3. Install `deploy/aunalytics-backend.service` to `/etc/systemd/system/`. Adjust `User=`, `Group=`, paths, and `ReadWritePaths=` to match your `DB_DIR`. Reload + enable + start.
4. `cd frontend && npm ci && npm run build`, then install `deploy/aunalytics-frontend.service` similarly.
5. Configure nginx from `deploy/nginx.conf.example` (TLS via certbot, per-route rate limits, generous `proxy_read_timeout` for `/api/ask` since LLM calls are slow).
6. Verify: `curl https://your.domain/health` (200), `curl https://your.domain/ready` (200 only if at least one LLM backend is reachable).

## Repo conventions

- Python 3.10+ with `from __future__ import annotations` throughout; Pydantic v2; `pydantic-settings` for env config.
- `.env`, `.venv/`, `node_modules/`, `__pycache__`, `.pytest_cache`, `.codex`, `backend/db/query_history.sqlite`, `backend/db/query_history.sqlite-*` are gitignored.
- Next.js 16 with React 19 — all interactive components need `"use client"`. **`frontend/AGENTS.md` warns that Next.js 16 has breaking API/convention/file-structure changes vs. older training data; consult `frontend/node_modules/next/dist/docs/` before writing or refactoring frontend code, and respect deprecation notices.**
- Frontend styled with Tailwind 4 + shadcn. New components should follow existing shadcn patterns in `components/ui/`.
- Tests: every test runs through `backend/tests/conftest.py`, which resets the settings cache and disables the rate limiter. New async tests must use `@pytest.mark.anyio`; the conftest provides the `anyio_backend` fixture (`asyncio`).
