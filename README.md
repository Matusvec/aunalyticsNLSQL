# aunalyticsNLSQL

A fullstack app that turns natural-language questions into safe, read-only SQLite queries. FastAPI backend + Next.js frontend. Ollama is the primary LLM; Gemini is an automatic fallback when Ollama is unreachable.

## Features

- **Ask questions in plain English** — backend generates SQL, validates it with `sqlglot`, and executes it read-only against your chosen SQLite database.
- **Schema sidebar + database picker** — browse uploaded databases and inspect their tables/columns.
- **Drag-and-drop upload** — upload `.sqlite` / `.db` / `.csv` / `.json`; CSV and JSON are converted to SQLite automatically.
- **Query history** — every successful question is logged; the UI shows recent questions and lets you reuse them.
- **Gemini fallback** — set `GEMINI_API_KEY` in `.env` and the backend transparently falls back to Gemini when Ollama is offline.
- **Schema extractor CLI** — `db_tools/` dumps schema (with optional sample rows) to JSON for offline use.

## Project Layout

- `backend/app/` — FastAPI app (`main.py`), routers (`query`, `schema`, `upload`), services (`ask_service`, `ollama_service`, `gemini_service`, `sqlite_service`, `sql_validator`, `history_service`).
- `backend/db/` — local SQLite databases (e.g., `chinook.db`). Uploads land here too.
- `backend/tests/` — pytest suite for routes and services.
- `frontend/` — Next.js 16 / React 19 / Tailwind + shadcn. HomePage wires schema sidebar, DB picker, upload, query panel, results table, and history.
- `db_tools/` — standalone schema-extractor adapter + tests.
- `backend_cli.py` — terminal client that exercises `/api/ask`.

## Requirements

- Python 3.10+
- Node 20+ / npm
- Ollama running locally at `http://localhost:11434` with at least one supported model installed. Preferred list: `qwen2.5-coder:3b`, `phi3`, `qwen3`, `llama3.2`, `gemma3`. Override with `OLLAMA_MODEL`.
- *(Optional)* `GEMINI_API_KEY` in a root `.env` file for the Gemini fallback.

## Install

Install application dependencies:

```bash
pip install -r requirements.txt
```

```powershell
py -m pip install -r requirements.txt
```

Install development and test dependencies:

```bash
pip install -r requirements-dev.txt
```

```powershell
py -m pip install -r requirements-dev.txt
```

## Run The Backend

### Development

```bash
./start_dev_services.sh
```

```powershell
.\start_dev_services.ps1
```

The dev script runs uvicorn with `--reload` (hot reload). It prefers a virtualenv at the repo root (`.venv`) or under `backend/.venv`, then falls back to `py`, `python`, or `python3`. Stop with `Ctrl-C`.

### Production

```bash
./start_prod_services.sh
```

The prod script runs `gunicorn` with `uvicorn.workers.UvicornWorker`. It requires a real venv at `.venv/` or `backend/.venv/` with `requirements.txt` installed. Configure via env vars:

- `APP_HOST` (default `127.0.0.1`)
- `APP_PORT` (default `8000`)
- `APP_WORKERS` (default `2`)
- `APP_TIMEOUT` (default `60` seconds)
- `APP_GRACEFUL_TIMEOUT`, `APP_KEEPALIVE`

Front it with nginx/Caddy for TLS termination — see `deploy/nginx.conf.example`. systemd unit templates live in `deploy/`. The full settings reference is in `.env.example`.

If PowerShell blocks script execution, you may need:

```powershell
Set-ExecutionPolicy Unrestricted
```

## API Endpoints

Once the backend is running, the main routes are:

- `GET /health`: liveness probe (always 200 if process is up)
- `GET /ready`: readiness probe (checks DB dir, history DB, and at least one LLM backend; 503 if nothing is reachable)
- `GET /api/schema/{db_filename}`: full schema details
- `GET /api/schema-summary/{db_filename}`: compact schema summary
- `POST /api/generate-sql`: generate validated read-only SQL from a question
- `POST /api/execute`: execute validated read-only SQL against a selected database
- `POST /api/ask`: generate SQL, validate it, execute it, and return rows

The `/api/ask` flow builds relevant schema context for the question, asks Ollama for a single read-only SQL statement, validates that SQL, and executes it against SQLite with a row limit.

## Web UI

The Next.js frontend lives in [`frontend/`](frontend/). HomePage wires the schema sidebar (`GET /api/schema/{filename}`), database picker (`GET /api/databases`), drag-and-drop upload (`POST /api/upload`), a **question input + results table** (`POST /api/ask`), and a **history panel** (`GET /api/history`) — clicking a history item reuses that question.

1. Start the backend (see above).
2. In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local          # NEXT_PUBLIC_API_URL defaults to http://127.0.0.1:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Frontend build + tests:

```bash
cd frontend
npm run build
npm run test
```

## Gemini fallback

Copy `.env.example` to `.env` at the repo root and set `GEMINI_API_KEY`. When Ollama's server is unreachable (connection refused during model resolution or during a generation attempt), the backend automatically delegates to Gemini (`gemini-2.5-flash` by default; override with `GEMINI_MODEL`). `.env` is gitignored.

## Terminal Client

With the backend running, launch the terminal client:

```bash
python3 backend_cli.py
```

```powershell
py .\backend_cli.py
```

The client will:

- list available databases from `backend/db`
- prompt you to choose one
- let you ask questions in a loop
- print the backend JSON response

Type `quit`, `exit`, or `q` to leave.

## Testing

Run the full test suite:

```bash
./run_tests.sh
```

```powershell
bash ./run_tests.sh
```

This runs:

```bash
python -m pytest -v -rA backend/tests
```

You can also run focused test modules directly:

```bash
python -m pytest -v -rA backend/tests/test_ask_route.py
python -m pytest -v -rA backend/tests/test_ask_service.py
python -m pytest -v -rA backend/tests/test_ollama_service.py
python -m pytest -v -rA backend/tests/test_sql_validator.py
```

Or pass extra pytest filters through the script:

```bash
./run_tests.sh -k ask
```

## Database Schema Extractor (db_tools)

Auxiliary schema extraction utility in `db_tools/`, using the Adapter pattern with `SQLiteExtractor` (easy to swap in a `PostgresExtractor` later). The main ask flow uses the backend's built-in schema summary; this tool is useful for exporting full schema + sample rows to JSON for offline use.

**Extract a local SQLite database schema to JSON:**
```bash
python3 db_tools/db_extractor.py --db path/to/db.sqlite --out schema.json
```

**Include a small number of sample rows per table for LLM context:**
```bash
python3 db_tools/db_extractor.py --db path/to/db.sqlite --samples 5 --out schema_with_samples.json
```

**Tests:**
```bash
pytest db_tools/tests/test_db_extractor.py
```
