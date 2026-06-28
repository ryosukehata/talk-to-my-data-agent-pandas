#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "/.datarobot-pre-bundled" ]; then
  echo "Detected pre-bundled DataRobot environment; installing application dependencies."
  python3 -m pip install -r requirements.txt
  exit 0
fi

if command -v uv >/dev/null 2>&1 && [ -f "uv.lock" ]; then
  uv sync --frozen --no-dev
else
  python3 -m pip install -r requirements.txt
fi
