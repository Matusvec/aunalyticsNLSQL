#!/usr/bin/env bash
# Production entrypoint for the FastAPI backend.
# Run from the repo root. Environment variables are loaded from .env automatically by app.main.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-8000}"
APP_WORKERS="${APP_WORKERS:-2}"
APP_TIMEOUT="${APP_TIMEOUT:-60}"
APP_GRACEFUL_TIMEOUT="${APP_GRACEFUL_TIMEOUT:-30}"
APP_KEEPALIVE="${APP_KEEPALIVE:-5}"

# Prefer venv; require it in production so deps are pinned.
if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
elif [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  PYTHON="$BACKEND_DIR/.venv/bin/python"
else
  echo "No virtualenv found at .venv/ or backend/.venv/. Refusing to start." >&2
  echo "Create one and install requirements.txt before launching." >&2
  exit 1
fi

if ! "$PYTHON" -c "import gunicorn, uvicorn, app.main" >/dev/null 2>&1; then
  echo "Required packages not available in $PYTHON." >&2
  echo "Run: $PYTHON -m pip install -r requirements.txt" >&2
  exit 1
fi

cd "$BACKEND_DIR"

exec "$PYTHON" -m gunicorn app.main:app \
  --workers "$APP_WORKERS" \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind "$APP_HOST:$APP_PORT" \
  --timeout "$APP_TIMEOUT" \
  --graceful-timeout "$APP_GRACEFUL_TIMEOUT" \
  --keep-alive "$APP_KEEPALIVE" \
  --access-logfile - \
  --error-logfile -
