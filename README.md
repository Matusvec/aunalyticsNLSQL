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

