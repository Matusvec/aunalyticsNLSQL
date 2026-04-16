# aunalyticsNLSQL

A small FastAPI application that turns natural-language questions into safe, read-only SQLite queries using Ollama. The repo also includes a terminal client for exercising the API against sample databases in `backend/db`.

## Project Layout

- `backend/app/main.py`: FastAPI entrypoint
- `backend/app/routers`: API routes for query and schema endpoints
- `backend/app/services`: Ollama, SQLite, validation, and ask-flow logic
- `backend/db`: local SQLite databases such as `chinook.db`
- `backend/tests`: route and service tests
- `backend_cli.py`: terminal client for the `/api/ask` endpoint

## Requirements

- Python 3.10+
- Ollama running locally at `http://localhost:11434`
- At least one Ollama model available locally

The backend prefers the `OLLAMA_MODEL` environment variable when set. Otherwise it will try an installed model from this list: `qwen2.5-coder:3b`, `phi3`, `qwen3`, `llama3.2`, `gemma3`.

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

Start the FastAPI app with the helper script:

```bash
./start_dev_services.sh
```

```powershell
.\start_dev_services.ps1
```

The startup scripts prefer a virtualenv at the repo root (`.venv`) or under `backend/.venv`, then fall back to `py`, `python`, or `python3`.

This starts the API from `backend/app/main.py`. Stop it with `Ctrl-C`.

If PowerShell blocks script execution, you may need:

```powershell
Set-ExecutionPolicy Unrestricted
```

## API Endpoints

Once the backend is running, the main routes are:

- `GET /health`: health check
- `GET /api/schema/{db_filename}`: full schema details
- `GET /api/schema-summary/{db_filename}`: compact schema summary
- `POST /api/generate-sql`: generate validated read-only SQL from a question
- `POST /api/execute`: execute validated read-only SQL against a selected database
- `POST /api/ask`: generate SQL, validate it, execute it, and return rows

The `/api/ask` flow builds relevant schema context for the question, asks Ollama for a single read-only SQL statement, validates that SQL, and executes it against SQLite with a row limit.

## Web UI (Week 2 — schema sidebar and file upload)

The Next.js frontend lives in [`frontend/`](frontend/). It shows a **collapsible schema sidebar** (`GET /api/schema/{filename}`), a **database picker** (`GET /api/databases`), and **drag-and-drop upload** (`POST /api/upload`).

1. Start the API (see above).
2. In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Set `NEXT_PUBLIC_API_URL` in `.env.local` if the API is not on `http://127.0.0.1:8000`.

Frontend tests (Vitest):

```bash
cd frontend && npm run test
```

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
