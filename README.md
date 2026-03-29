# aunalyticsNLSQL

## Development

Install app requirements:

```bash
pip install -r requirements.txt
```

```powershell
py -m pip install -r requirements.txt
```

Install dev/test requirements:

```bash
pip install -r requirements-dev.txt
```

```powershell
py -m pip install -r requirements-dev.txt
```

Start the FastAPI app and the MCP server together:

```bash
./start_dev_services.sh
```

```powershell
.\start_dev_services.ps1
```

The startup scripts prefer the project virtualenv when present (`.venv` at the repo root or inside `backend`), then fall back to `py`, `python`, or `python3`. They do not require a local `.venv`, but they do require that the project requirements are already installed for whichever Python they find.

If you get an error in Powershell saying you can't execute scripts on your machine you may have to run Set-ExecutionPolicy Unrestricted

This starts:
- the FastAPI app from `backend/app/main.py`
- the MCP server from `backend/mcp_sqlite/server.py`

When `MCP_TRANSPORT=streamable-http`, the MCP endpoint used by `/api/ask` is `http://127.0.0.1:8001/mcp` by default. You can override that with `MCP_SERVER_URL`.

Press `Ctrl-C` to stop both processes.

## Terminal Client

With the backend running, you can use the terminal client to pick a database from `backend/db` and send natural-language questions to `POST /api/ask`. That route now lets Ollama choose MCP tools, execute them through the MCP server, and then produce a final answer with the tool result as context.

Run it with:

```bash
python3 backend_cli.py
```

```powershell
py .\backend_cli.py
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

```powershell
bash ./run_ask_tests.sh
```

The script uses the active Python environment, `python`, or `python3` in that order, and exits with a helpful message if `pytest` is not installed.

This runs:

```bash
python -m pytest -v -rP backend/tests/test_ask_route.py
```

```powershell
py -m pytest -v -rP backend/tests/test_ask_route.py
```

The flags mean:
- `-v`: show each test name as it runs
- `-rP`: include passed-test details in the summary

You can also pass extra pytest arguments through the script:

```bash
./run_ask_tests.sh -k happy
```

```powershell
bash ./run_ask_tests.sh -k happy
```
