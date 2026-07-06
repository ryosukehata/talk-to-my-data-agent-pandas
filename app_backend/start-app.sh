#!/usr/bin/env bash

set -euo pipefail

WORKING_DIR=$(pwd)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RUNTIME_DIR="${TMPDIR:-/tmp}/datarobot-app-runtime"
export UV_CACHE_DIR="${UV_CACHE_DIR:-${RUNTIME_DIR}/uv-cache}"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-${RUNTIME_DIR}/.venv}"

export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"

if [ -f "/.datarobot-pre-bundled" ]; then
    echo "Building prebundled env ${WORKING_DIR} ${UV_CACHE_DIR} ${UV_PROJECT_ENVIRONMENT}"

    PREBUNDLED_ROOT=/home/notebooks/talk-to-my-data-agent
    PREBUNDLED_UV_CACHE="$PREBUNDLED_ROOT/.cache/uv"
    PREBUNDLED_VENV="$PREBUNDLED_ROOT/app_backend/.venv"
    TEMP_SERVER_PID=""

    cleanup_bootstrap_server() {
        if [ -n "${TEMP_SERVER_PID:-}" ]; then
            kill "$TEMP_SERVER_PID" 2>/dev/null || true
            wait "$TEMP_SERVER_PID" 2>/dev/null || true
        fi
    }
    trap cleanup_bootstrap_server EXIT

    # Keep port 8080 alive to pass health checks while dependencies are being synchronized.
    python3 -m http.server 8080 >/tmp/prebundled-bootstrap-http.log 2>&1 &
    TEMP_SERVER_PID=$!

    mkdir -p "$UV_CACHE_DIR" "$(dirname "$UV_PROJECT_ENVIRONMENT")"
    if [ -d "$PREBUNDLED_UV_CACHE" ]; then
        echo "Copying UV cache"
        cp -r "$PREBUNDLED_UV_CACHE"/. "$UV_CACHE_DIR"/
    fi

    echo "Syncing .venv"

    if [ -d "$PREBUNDLED_VENV" ]; then
        rm -rf "$UV_PROJECT_ENVIRONMENT"
        cp -r "$PREBUNDLED_VENV" "$UV_PROJECT_ENVIRONMENT"
    fi

    echo "Running uv sync"

    uv sync --frozen

    echo "Starting real server"

    cleanup_bootstrap_server
    trap - EXIT

    exec uv run --frozen python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --proxy-headers --timeout-keep-alive 300
else
    # pyproject.toml build path: deps installed system-wide by the DR platform.
    # core/ is a symlink, so include core/src on PYTHONPATH for the src layout.
    export PYTHONPATH="${SCRIPT_DIR}/core/src:${SCRIPT_DIR}:${PYTHONPATH:-}"
    exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --proxy-headers --timeout-keep-alive 300
fi
