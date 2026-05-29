#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=== postgres-to-neo4j setup ==="

# ── 1. Create Python virtual environment ──────────────────────────────
if [ ! -d ".venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv .venv
else
    echo "[1/3] Virtual environment already exists."
fi

# ── 2. Install package + dependencies ─────────────────────────────────
echo "[2/3] Installing package and dependencies..."
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e .

# ── 3. Configure .env ─────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo "[3/3] Creating .env from template — edit it with your credentials."
    cp .env.example .env
else
    echo "[3/3] .env already exists."
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit  .env        — set your PG_DSN and Neo4j credentials"
echo "  2. Edit  config/tables.yaml   — choose which tables to extract"
echo "  3. Run   make run     or  .venv/bin/postgres-to-neo4j"
echo "  4. Run   make dry-run  for a dry run first"
