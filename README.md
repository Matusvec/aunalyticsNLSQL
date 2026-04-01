# aunalyticsNLSQL

## Development

Download requirements:

```bash
pip install -r requirements.txt
```

or for dev/test:

```bash
pip install -r requirements-dev.txt
```

Start the FastAPI app and the MCP server together:

```bash
./start_dev_services.sh
```

This starts:
- the FastAPI app from `backend/app/main.py`
- the MCP server from `backend/mcp_sqlite/server.py`

Press `Ctrl-C` to stop both processes.

## Terminal Client

With the backend running, you can use the terminal client to pick a database from `backend/db` and send natural-language questions to `POST /api/generate-sql`.

Run it with:

```bash
./.venv/bin/python backend_cli.py
```

The client will:
- list available database files
- prompt you to choose one
- let you ask questions in a loop
- print the backend JSON response

Type `quit`, `exit`, or `q` to leave the client.


## Testing `/api/ask`

Run the end-to-end tests for the `/api/ask` route:

```bash
./run_ask_tests.sh
```

This runs:

```bash
.venv/bin/python -m pytest -v -rP backend/tests/test_ask_route.py
```

The flags mean:
- `-v`: show each test name as it runs
- `-rP`: include passed-test details in the summary

You can also pass extra pytest arguments through the script:

```bash
./run_ask_tests.sh -k happy
```


## Testing FILE UPLOAD ENDPT - `/api/upload`

Quick steps for someone who just wants to try uploads without coding:

- Install dependencies:

```bash
pip install -r requirements.txt
```

- Start the backend (from repo root):

```bash
./start_dev_services.sh
```

- Upload a file (CSV/JSON/SQLite) using curl. Example with a CSV:

```bash
curl -X POST "http://127.0.0.1:8000/api/upload" -F "file=@/full/path/to/mydata.csv"
```

- Expected successful response:

```json
{"success": true, "filename": "mydata.sqlite"}
```

- Where to look: the converted or saved SQLite file will be placed in the `backend/db/` directory (filename is the uploaded file stem with `.sqlite`).

Notes:
- JSON upload expects a flat array of objects (e.g. `[{"a":1,"b":2}, {"a":3,"b":4}]`).
- Files larger than 20MB are rejected.
- If you prefer a GUI, you can use tools like Postman or Insomnia to POST a `form-data` file field named `file` to `http://127.0.0.1:8000/api/upload`.


Automated tests for the upload endpoint
--------------------------------------

Run the upload tests with pytest (uses the project's venv):

```bash
.venv/bin/python -m pytest -q backend/tests/test_upload_route.py
```

Or run the whole backend test suite:

```bash
.venv/bin/python -m pytest -q backend/tests
```

Live upload test
----------------

To manually test uploading a file while the server is running:

1. Start the backend services:

```bash
./start_dev_services.sh
```

2. Upload a CSV (example):

```bash
curl -X POST "http://127.0.0.1:8000/api/upload" -F "file=@/full/path/to/mydata.csv"
```

3. Upload a JSON (example):

```bash
curl -X POST "http://127.0.0.1:8000/api/upload" -F "file=@/full/path/to/mydata.json;type=application/json"
```

4. Check `backend/db/` for the resulting `.sqlite` files.

Notes:
- The automated tests clean up files they create; manual uploads will remain in `backend/db/` until deleted.


