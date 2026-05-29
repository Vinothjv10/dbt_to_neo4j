# dbt Lineage → Neo4j Pipeline

Extract table and column-level lineage from dbt models and store it in Neo4j as a property graph.  
An LLM (or any application) can then query Neo4j to discover tables, columns, and JOIN paths.

---

## 1. What This Does

```
┌──────────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  dbt Model SQL Files │ ──> │  YAML Lineage    │ ──> │  Neo4j Graph DB     │
│  + manifest.json     │     │  (config/model_  │     │  Schema → Table →   │
│                      │     │   lineage/*.yml) │     │  Column → MAPS_TO   │
└──────────────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                                  │
                                              LLM queries via Cypher
                                              (table discovery,
                                               column lookup,
                                               JOIN path finding)
```

**What gets stored in Neo4j:**

| Node/Edge | Meaning | Example |
|-----------|---------|---------|
| `(:Schema)` | Database schema | `silver_layer` |
| `(:Table)` | A table or model | `t3_Eway_Report`, `t2_master_hubops` |
| `(:Column)` | A column with name, data_type, description | `awb_number`, `booking_date` |
| `(:Table)-[:DEPENDS_ON]->(:Table)` | Model depends on upstream table | `t3_Eway_Report` → `t2_master_hubops_bk` |
| `(:Column)-[:MAPS_TO]->(:Column)` | Column sourced from upstream column | `booking_cp_id` → `origin_cp_id` |
| `(:Schema)-[:HAS_TABLE]->(:Table)` | Schema contains table | |
| `(:Table)-[:HAS_COLUMN]->(:Column)` | Table contains column | |

---

## 2. Prerequisites

- **Python 3.11+** installed (`python3 --version`)
- **Neo4j Database** running (local or remote) — [Download Neo4j](https://neo4j.com/download/)
- **dbt project** with compiled `manifest.json` at `target/manifest.json`
- **PostgreSQL database** (optional — only needed for the PG schema sync pipeline)

---

## 3. One-Time Setup

### Step 1: Clone / Navigate to the Project

```bash
cd /home/ubuntu/neo4j     # or wherever this project is located
```

### Step 2: Run Setup

```bash
make setup
```

This will:
1. Create a Python virtual environment (`.venv/`)
2. Install all required packages (neo4j, pyyaml, python-dotenv)
3. Copy `.env.example` to `.env` if it doesn't exist

### Step 3: Configure `.env`

Open `.env` in any text editor and fill in your credentials:

```bash
nano .env
```

It should look like this:

```env
# ── Database (only needed for PG→Neo4j schema sync) ───────────
PG_DSN=postgresql://username:password@localhost:5432/your_database

# ── Neo4j ─────────────────────────────────────────────────────
NEO4J_URI=bolt://localhost:7687        # Neo4j connection address
NEO4J_USER=neo4j                       # Neo4j username
NEO4J_PASSWORD=your_neo4j_password     # Neo4j password
```

> **Neo4j not installed?** Download from [neo4j.com/download](https://neo4j.com/download/),  
> extract, run `bin/neo4j start`, and set password at `http://localhost:7474`.

---

## 4. Data Flow Overview

```
Step A: dbt Lineage → YAML (already done for 14 models)
         └─ config/model_lineage/t3_*.yml

Step B: Push YAML → Neo4j
         └─ make push-lineage

Step C: Generate SQL JOIN queries
         └─ make generate-joins
         └─ config/model_lineage/_generated_joins.sql

Step D: Verify in Neo4j
         └─ make verify
```

---

## 5. Push Lineage to Neo4j

### Push all 14 models to Neo4j:

```bash
make push-lineage
```

This reads all YAML files from `config/model_lineage/` and creates the full graph in Neo4j:
- Schema, Table, Column nodes
- DEPENDS_ON (table-level) and MAPS_TO (column-level) relationships
- Column descriptions from the YAML files

### See what would be pushed (without writing):

```bash
make push-dry-run
```

### Show a summary of lineage data:

```bash
make push-summary
```

---

## 6. Generate SQL JOIN Queries

```bash
make generate-joins
```

This creates `config/model_lineage/_generated_joins.sql` with SELECT + LEFT JOIN
queries for every model, using the column lineage to build ON conditions.

---

## 7. Verify in Neo4j

Open Neo4j Browser at `http://localhost:7474` and run these queries:

### Check counts:

```cypher
MATCH (s:Schema) RETURN count(s) AS schemas;
MATCH (t:Table) RETURN count(t) AS tables;
MATCH (c:Column) RETURN count(c) AS columns;
MATCH ()-[d:DEPENDS_ON]->() RETURN count(d) AS depends_on;
MATCH ()-[m:MAPS_TO]->() RETURN count(m) AS maps_to;
```

**Expected output (after full push):**

| Item | Count |
|------|-------|
| Schemas | 1 |
| Tables | 31 |
| Columns | 519 |
| DEPENDS_ON | 38 |
| MAPS_TO | 244 |

### List all models and their upstream tables:

```cypher
MATCH (t:Table)-[:DEPENDS_ON]->(up:Table)
WHERE t.name STARTS WITH 't3_'
RETURN t.name AS model, collect(up.name) AS upstreams
ORDER BY model;
```

### See column-level lineage for a specific model:

```cypher
MATCH (t:Table {name: 't3_Eway_Report'})-[:HAS_COLUMN]->(c:Column)
OPTIONAL MATCH (c)-[:MAPS_TO]->(upc:Column)<-[:HAS_COLUMN]-(up:Table)
RETURN c.name AS model_column,
       c.description AS description,
       up.name AS source_table,
       upc.name AS source_column
ORDER BY c.name;
```

### Find JOIN conditions for a model:

```cypher
MATCH (t:Table {name: 't3_delivery_mis_report'})-[:DEPENDS_ON]->(up:Table)
OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)-[:MAPS_TO]->(upc:Column)<-[:HAS_COLUMN]-(up)
RETURN up.name AS upstream_table,
       collect({model_col: c.name, upstream_col: upc.name}) AS join_conditions
ORDER BY upstream_table;
```

### Quick verify from command line:

```bash
make verify
```

---

## 8. All Make Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available targets |
| `make setup` | One-time project setup |
| `make push-lineage` | Push YAML lineage to Neo4j |
| `make push-dry-run` | Dry run (preview only) |
| `make push-summary` | Show lineage summary |
| `make generate-joins` | Generate SQL JOIN queries |
| `make verify` | Show Cypher queries for Neo4j |
| `make push-all` | Full pipeline: push → joins → verify |
| `make run` | PG→Neo4j schema sync (if PG configured) |
| `make dry-run` | PG→Neo4j dry run |
| `make clean-db` | Clear Neo4j database |

---

## 9. Project Structure

```
├── config/
│   ├── tables.yaml              # Tables for PG→Neo4j pipeline
│   ├── settings.yaml            # Pipeline settings
│   ├── model_lineage/           # Lineage YAML files (one per model)
│   │   ├── t3_Eway_Report.yml
│   │   ├── ...
│   │   └── _generated_joins.sql   # Auto-generated SQL joins
│   └── lineage_inspection_queries.cypher  # Reference Cypher queries
│
├── postgres_to_neo4j/           # Neo4j loader pipeline
│   ├── lineage_loader.py        # Reads YAML → writes to Neo4j
│   ├── cli.py                   # PG→Neo4j CLI
│   ├── config.py                # Configuration reader
│   ├── postgres/                # PG schema extractor
│   ├── neo4j/                   # Neo4j writer
│   └── models/                  # Data models
│
├── scripts/
│   ├── sql_generator.py         # Generates SQL JOINs from YAML
│   ├── enrich_lineage.py        # Enriches YAML with CTE resolution
│   ├── patch_lineage_4_models.py # Patches column lineage from SQL
│   ├── validate_all_models.py   # Validates all 14 models
│   ├── audit_dependencies.py    # Audits SQL refs vs YAML upstreams
│   └── fix_source_columns.py    # Fixes source column references
│
├── .env                         # Credentials (DO NOT SHARE)
├── .env.example                 # Template for .env
├── Makefile                     # All commands
├── setup.sh                     # One-time setup script
├── pyproject.toml               # Python package config
└── README.md                    # This file
```

---

## 10. Adding a New Model

1. **Create the model YAML file** in `config/model_lineage/`:
   ```bash
   cp config/model_lineage/t3_Eway_Report.yml config/model_lineage/your_new_model.yml
   ```

2. **Edit the YAML** with the model's:
   - Name, schema, columns (name, description, source_table, source_column)
   - Upstreams and column_lineage entries

3. **Validate**:
   ```bash
   make push-summary
   ```

4. **Push to Neo4j**:
   ```bash
   make push-lineage
   ```

5. **Regenerate SQL joins**:
   ```bash
   make generate-joins
   ```

---

## 11. Running validation (all models)

```bash
.venv/bin/python scripts/validate_all_models.py
```

This checks:
1. Every SQL `{{ ref(...) }}` has a matching YAML upstream entry
2. Every column `source_table/source_column` has a corresponding `column_lineage`
3. All tables are registered in `config/tables.yaml`

---

## 12. Example: LLM Discovery Flow

An LLM can use these Cypher queries to understand the data:

**"What tables are available?"**
```cypher
MATCH (t:Table) RETURN t.name, t.schema ORDER BY t.name;
```

**"What columns does t3_Eway_Report have?"**
```cypher
MATCH (t:Table {name: 't3_Eway_Report'})-[:HAS_COLUMN]->(c:Column)
RETURN c.name, c.description, c.data_type ORDER BY c.name;
```

**"How does t3_Eway_Report join to its upstreams?"**
```cypher
MATCH (t:Table {name: 't3_Eway_Report'})-[:DEPENDS_ON]->(up:Table)
OPTIONAL MATCH (c:Column)-[:MAPS_TO]->(upc:Column)<-[:HAS_COLUMN]-(up)
RETURN up.name AS join_table,
       collect(DISTINCT {this_col: c.name, other_col: upc.name}) AS on_conditions;
```

**"Search all columns by keyword"**
```cypher
MATCH (c:Column) WHERE c.description CONTAINS 'shipment'
RETURN c.table, c.name, c.description LIMIT 20;
```

---

## 13. Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'neo4j'` | Run `make setup` or `pip install -e .` |
| `Connection refused to localhost:7687` | Start Neo4j: `cd /path/to/neo4j/bin && ./neo4j start` |
| `push-lineage` asks "Continue? (y/N)" | Press `y` then Enter |
| Wrong Neo4j password | Edit `.env` → `NEO4J_PASSWORD=correct_password` |
| Need to start fresh | Run `make clean-db` then `make push-lineage` |
| YAML has wrong upstreams | Edit YAML file, run `make push-lineage` again |
