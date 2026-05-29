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
echo "  1. Edit  .env              — set your Neo4j credentials"
echo "  2. Run   make push-lineage  — push dbt lineage to Neo4j"
echo "  3. Run   make verify        — verify the graph in Neo4j"
echo "  4. Run   make manage-list   — list all models"
echo ""
echo "Optional (PG schema sync):"
echo "  - Set PG_DSN in .env, then run:  make run"
