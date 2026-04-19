#!/usr/bin/env bash
# AI Shot Cutter — Run launcher (macOS / Linux)
# Uses uv to run inside the project's virtual environment.

set -euo pipefail

cd "$(dirname "$0")"

if ! command -v uv &>/dev/null; then
    echo "[ERROR] uv is not installed. Please run ./install.sh first."
    exit 1
fi

if [[ ! -d ".venv" ]]; then
    echo "[ERROR] Virtual environment not found. Please run ./install.sh first."
    exit 1
fi

exec uv run python main.py "$@"
