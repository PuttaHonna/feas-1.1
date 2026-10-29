#!/usr/bin/env bash
# ====================================================================
# FEAS 2.0 - Linux & macOS Universal Launcher
# ====================================================================
set -e

# Change directory to the root of the repository
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

# Detect Python interpreter
if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
else
    echo "Error: Python 3 is not installed or not in PATH."
    echo "Please install Python 3.10+ (via brew, apt, or python.org)."
    exit 1
fi

# Auto-activate virtual environment if it exists
if [ -f "$DIR/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$DIR/.venv/bin/activate"
    PY_CMD="python"
elif [ -f "$DIR/venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$DIR/venv/bin/activate"
    PY_CMD="python"
fi

# Pass all arguments through to universal runner
exec "$PY_CMD" "$DIR/run.py" "$@"
