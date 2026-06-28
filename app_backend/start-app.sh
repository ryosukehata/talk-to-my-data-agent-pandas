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
  echo "Building prebundled env ${SCRIPT_DIR} ${UV_CACHE_DIR}"

  PREBUNDLED_ROOT=/home/notebooks/talk-to-my-data-agent
  PREBUNDLED_UV_CACHE="$PREBUNDLED_ROOT/.cache/uv"
  PREBUNDLED_VENV="$PREBUNDLED_ROOT/app_backend/.venv"

  # Keep port 8080 alive to pass health checks while dependencies sync.
  python3 -m http.server "$PORT" >/tmp/prebundled-bootstrap-http.log 2>&1 &
  TEMP_SERVER_PID=$!

  mkdir -p "$UV_CACHE_DIR"
  if [ -d "$PREBUNDLED_UV_CACHE" ]; then
    echo "Copying UV cache"
    cp -r "$PREBUNDLED_UV_CACHE"/. "$UV_CACHE_DIR"/
  fi

  if [ -d "$PREBUNDLED_VENV" ]; then
    echo "Copying prebundled .venv"
    rm -rf ".venv"
    cp -r "$PREBUNDLED_VENV" ".venv"
  fi

  echo "Running uv sync"
  uv sync

  echo "Starting real server"
  kill "$TEMP_SERVER_PID"
  wait "$TEMP_SERVER_PID"

  exec uv run python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level "$LOG_LEVEL" "${EXTRA_OPTS[@]}" --timeout-keep-alive 300
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
