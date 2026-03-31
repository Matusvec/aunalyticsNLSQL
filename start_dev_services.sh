#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-8000}"

PYTHON_CMD=()

find_python() {
  if [[ -x "$ROOT_DIR/.venv/Scripts/python.exe" ]]; then
    PYTHON_CMD=("$ROOT_DIR/.venv/Scripts/python.exe")
    return 0
  fi

  if [[ -x "$BACKEND_DIR/.venv/Scripts/python.exe" ]]; then
    PYTHON_CMD=("$BACKEND_DIR/.venv/Scripts/python.exe")
    return 0
  fi

  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    PYTHON_CMD=("$ROOT_DIR/.venv/bin/python")
    return 0
  fi

  if [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
    PYTHON_CMD=("$BACKEND_DIR/.venv/bin/python")
    return 0
  fi

  if command -v py >/dev/null 2>&1; then
    PYTHON_CMD=("$(command -v py)")
    return 0
  fi

  if command -v python >/dev/null 2>&1; then
    PYTHON_CMD=("$(command -v python)")
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=("$(command -v python3)")
    return 0
  fi

  return 1
}

if ! find_python; then
  echo "Python was not found. Install Python and the project requirements first." >&2
  exit 1
fi

cd "$BACKEND_DIR"

if ! "${PYTHON_CMD[@]}" -c "import uvicorn; import app.main" >/dev/null 2>&1; then
  echo "Required packages or local backend modules are not available for ${PYTHON_CMD[*]}." >&2
  echo "Install the app requirements first, for example:" >&2
  echo "  ${PYTHON_CMD[*]} -m pip install -r requirements.txt" >&2
  exit 1
fi

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if [[ -n "${APP_PID:-}" ]]; then
    kill "$APP_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  if [[ "$exit_code" -eq 0 || "$exit_code" -eq 130 || "$exit_code" -eq 143 ]]; then
    echo "FastAPI app shut down cleanly."
  else
    echo "FastAPI app stopped with exit code $exit_code." >&2
  fi
  exit "$exit_code"
}

wait_for_first_exit() {
  local pid

  while true; do
    for pid in "$@"; do
      if ! kill -0 "$pid" 2>/dev/null; then
        wait "$pid"
        return $?
      fi
    done
    sleep 1
  done
}

trap cleanup EXIT INT TERM

"${PYTHON_CMD[@]}" -m uvicorn app.main:app --reload --host "$APP_HOST" --port "$APP_PORT" &
APP_PID=$!

echo "FastAPI app: http://$APP_HOST:$APP_PORT"
echo "Press Ctrl-C to stop the service."

wait_for_first_exit "$APP_PID"
