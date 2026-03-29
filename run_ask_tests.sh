#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_python() {
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi

  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    echo "$ROOT_DIR/.venv/bin/python"
    return 0
  fi

  return 1
}

if ! PYTHON_BIN="$(find_python)"; then
  echo "Python was not found. Install Python and the project requirements first." >&2
  exit 1
fi

if ! "$PYTHON_BIN" -c "import pytest" >/dev/null 2>&1; then
  echo "pytest is not installed for $PYTHON_BIN." >&2
  echo "Install the dev requirements first, for example:" >&2
  echo "  $PYTHON_BIN -m pip install -r requirements-dev.txt" >&2
  exit 1
fi

cd "$ROOT_DIR"
exec "$PYTHON_BIN" -m pytest -v -rP backend/tests/test_ask_route.py "$@"
