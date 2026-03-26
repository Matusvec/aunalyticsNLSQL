#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
UVICORN_BIN="$ROOT_DIR/.venv/bin/uvicorn"

APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-8000}"
MCP_HOST="${MCP_HOST:-127.0.0.1}"
MCP_PORT="${MCP_PORT:-8001}"
MCP_TRANSPORT="${MCP_TRANSPORT:-streamable-http}"

if [[ ! -x "$VENV_PYTHON" || ! -x "$UVICORN_BIN" ]]; then
  echo "Expected .venv with python and uvicorn under $ROOT_DIR/.venv/bin" >&2
  exit 1
fi

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if [[ -n "${APP_PID:-}" ]]; then
    kill "$APP_PID" 2>/dev/null || true
  fi
  if [[ -n "${MCP_PID:-}" ]]; then
    kill "$MCP_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  if [[ "$exit_code" -eq 0 || "$exit_code" -eq 130 || "$exit_code" -eq 143 ]]; then
    echo "FastAPI app and MCP server shut down cleanly."
  else
    echo "FastAPI app and MCP server stopped with exit code $exit_code." >&2
  fi
  exit "$exit_code"
}

trap cleanup EXIT INT TERM

cd "$BACKEND_DIR"

"$UVICORN_BIN" app.main:app --reload --host "$APP_HOST" --port "$APP_PORT" &
APP_PID=$!

MCP_TRANSPORT="$MCP_TRANSPORT" MCP_HOST="$MCP_HOST" MCP_PORT="$MCP_PORT" \
  "$VENV_PYTHON" -m mcp_sqlite.server &
MCP_PID=$!

echo "FastAPI app: http://$APP_HOST:$APP_PORT"
echo "MCP server:   http://$MCP_HOST:$MCP_PORT ($MCP_TRANSPORT)"
echo "Press Ctrl-C to stop both services."

wait -n "$APP_PID" "$MCP_PID"
