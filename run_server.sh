#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Create venv if missing
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt
mkdir -p data

echo "================================================"
echo "  Paper DB running at http://127.0.0.1:16666"
echo "  Press Ctrl+C to stop gracefully."
echo "================================================"

python -m uvicorn backend.main:app --host 127.0.0.1 --port 16666
