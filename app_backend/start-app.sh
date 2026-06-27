#!/usr/bin/env bash

export UV_CACHE_DIR=.uv
export PORT=${PORT:-"8080"}
DEV_MODE=${DEV_MODE:-false}
LOG_LEVEL="info"
EXTRA_OPTS=(--proxy-headers)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit
PRE_BUNDLED_MARKER="/.datarobot-pre-bundled"

if [ "$(echo "$DEV_MODE" | tr '[:upper:]' '[:lower:]')" = "true" ]; then
  EXTRA_OPTS+=("--reload")
  # Disable telemetry in dev mode to avoid OTLP connection errors
  export DISABLE_TELEMETRY=true
fi

if [ -f "$PRE_BUNDLED_MARKER" ]; then
  export PYTHONPATH="${SCRIPT_DIR}/core/src:${SCRIPT_DIR}:${PYTHONPATH:-}"
  if [ -x ".venv/bin/python" ]; then
    exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level "$LOG_LEVEL" "${EXTRA_OPTS[@]}"
  fi
  exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level "$LOG_LEVEL" "${EXTRA_OPTS[@]}"
fi

if command -v uv >/dev/null 2>&1; then
  if [ ! -d ".venv" ]; then
    uv sync
  fi
  exec uv run uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level "$LOG_LEVEL" "${EXTRA_OPTS[@]}"
else
  export PYTHONPATH="${SCRIPT_DIR}/core/src:${SCRIPT_DIR}:${PYTHONPATH:-}"
  exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level "$LOG_LEVEL" "${EXTRA_OPTS[@]}"
fi
