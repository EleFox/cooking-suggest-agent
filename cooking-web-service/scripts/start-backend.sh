#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

echo "Running ruff check..."
ruff check app/

echo "Running ruff format check..."
ruff format --check app/

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
