#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

VENV="$PROJECT_DIR/.venv"
if [ ! -d "$VENV" ]; then
    echo "Error: .venv not found. Run 'make setup' first."
    exit 1
fi

exec "$VENV/bin/python" -m postgres_to_neo4j.lineage_loader "$@"
