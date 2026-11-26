#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/frontend"

if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  pnpm install
fi

echo "Running eslint..."
pnpm run lint

echo "Running prettier check..."
pnpm run format:check

exec pnpm run dev
