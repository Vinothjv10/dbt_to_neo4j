# dbt Lineage → Neo4j Pipeline

Extract table and column-level lineage from dbt models and store it in Neo4j as a property graph.
An LLM or any application can query Neo4j to discover tables, columns, and JOIN paths.

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
|---|---|---|
| `(:Schema)` | Database schema | `silver_layer` |
| `(:Table)` | A table or dbt model | `t3_Eway_Report`, `t2_master_hubops` |
| `(:Column)` | A column with name, data_type, description | `awb_number`, `booking_date` |
| `(:Schema)-[:HAS_TABLE]->(:Table)` | Schema contains table | |
| `(:Table)-[:HAS_COLUMN]->(:Column)` | Table contains column | |
| `(:Table)-[:DEPENDS_ON]->(:Table)` | Model depends on upstream table | `t3_Eway_Report` → `t2_master_hubops_bk` |
| `(:Column)-[:MAPS_TO]->(:Column)` | Column sourced from upstream column | `booking_cp_id` → `origin_cp_id` |

---

## 2. Prerequisites

- **Python 3.11+** installed (`python3 --version`)
- **Neo4j Database** running (local or remote) — [Download Neo4j](https://neo4j.com/download/)
- **cypher-shell** installed (for `make verify`) — included with Neo4j, or `pip install neo4j`
- **dbt project** with compiled `manifest.json` at `target/manifest.json`
- **PostgreSQL database** (optional — only needed for the PG schema sync pipeline)

---

## 3. One-Time Setup

### Step 1: Navigate to the Project

```bash
cd /home/ubuntu/neo4j
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

```bash
nano .env
```

Required variables:

```env
# ── Neo4j ─────────────────────────────────────────────────────
NEO4J_URI=bolt://localhost:7687        # Neo4j connection address
NEO4J_USER=neo4j                       # Neo4j username
NEO4J_PASSWORD=your_neo4j_password     # Neo4j password

# ── Database (only needed for PG→Neo4j schema sync) ──────────
PG_DSN=postgresql://user:pass@localhost:5432/your_database

# ── Paths (optional overrides) ───────────────────────────────
TABLES_CONFIG=config/tables.yaml
```

> **Neo4j not installed?** Download from [neo4j.com/download](https://neo4j.com/download/),
> extract, run `bin/neo4j start`, and set password at `http://localhost:7474`.

---

## 4. Data Flow

```
Step 1: YAML lineage files (config/model_lineage/)
         ├── t3_Eway_Report.yml       ← one per dbt model
         ├── t3_delivery_mis_report.yml
         ├── ...
         └── _generated_joins.sql     ← auto-generated SQL JOINs

Step 2: Push to Neo4j
         └── make push-lineage

Step 3: Generate SQL JOIN queries
         └── make generate-joins

Step 4: Verify in Neo4j
         └── make verify
```

---

## 5. Push Lineage to Neo4j

### Push all models:

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

Creates `config/model_lineage/_generated_joins.sql` with SELECT + LEFT JOIN
queries for every model, using the column lineage to build ON conditions.

---

## 7. Model Management

### List all models

```bash
make manage-list
```

Shows every model with its number of upstreams, columns, and column mappings.

### Add a new model

#### Preview only (dry run):

```bash
make manage-add M=t3_day_wise_operation_count DRY_RUN=1
```

The script:
- Finds the `.sql` file in the dbt project
- Extracts `{{ ref() }}` upstream table names
- Parses SELECT columns with source mappings
- Prints the full YAML it will generate

**Review the output carefully.** If `column_lineage` entries are missing (CTEs, `SELECT *`, complex expressions), you will need to fill them manually after generation. See `make howto` for details.

#### Commit the model:

```bash
make manage-add M=t3_day_wise_operation_count
```

This:
- Writes `config/model_lineage/t3_YOUR_MODEL.yml`
- Adds the model and any new upstream tables to `config/tables.yaml`

#### Review the generated YAML:

```bash
nano config/model_lineage/t3_day_wise_operation_count.yml
```

Check that `source_table`, `source_column`, and `column_lineage` are correct.

#### Push and verify:

```bash
make push-all
```

### Remove a model

#### Preview only (dry run):

```bash
make manage-remove M=t3_day_wise_operation_count DRY_RUN=1
```

Reports which upstream tables (if any) would become orphans — tables used only by this model and no longer referenced by any remaining model.

#### Remove and clean up:

```bash
make manage-remove M=t3_day_wise_operation_count
```

This:
- Deletes `config/model_lineage/t3_YOUR_MODEL.yml`
- Removes the model from `config/tables.yaml`
- Removes any orphaned upstream tables from `config/tables.yaml`

#### Push and verify:

```bash
make push-all
```

### When column lineage can't be auto-extracted

The auto-extractor handles:
- Simple columns (`status`, `t.alias_col`)
- Function-wrapped columns (`DATE(operation_time)`)
- CASE expressions (`CASE WHEN ... THEN t.col END`)
- Bare column names with a single upstream

It does NOT handle:
- CTEs (`WITH cte AS (...) SELECT ...`)
- `SELECT *`
- Multiple upstreams without explicit alias prefixes

If your model uses these patterns, add `column_lineage` manually in the YAML,
then run `make push-all`. See `make howto-add` for a detailed guide.

### Custom dbt project path

If your dbt project is not at the default path, pass `DBT_PATH`:

```bash
make manage-add M=t3_YOUR_MODEL_NAME DBT_PATH=/path/to/dbt_project
make manage-add M=t3_YOUR_MODEL_NAME DRY_RUN=1 DBT_PATH=/path/to/dbt_project
```

---

## 8. Verify in Neo4j

### Auto-verify (requires cypher-shell + .env):

```bash
make verify
```

This runs two Cypher queries against Neo4j:
1. Node/edge counts (Schema, Table, Column, DEPENDS_ON, MAPS_TO)
2. All model→upstream joins with column-level mappings

### Quick counts only:

```bash
make verify-counts
```

### Manual checks via cypher-shell:

```bash
source .env
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD"
```

**Expected counts (13 models after removing `t3_delivery_mis_report`):**

| Item | Count |
|------|-------|
| Schemas | 1 |
| Tables | 29 |
| Columns | 476 |
| DEPENDS_ON | 37 |
| MAPS_TO | 222 |

**Check a specific model:**

```cypher
MATCH (t:Table {name: 't3_Eway_Report'})-[:DEPENDS_ON]->(up:Table)
RETURN up.name AS upstreams;

MATCH (t:Table {name: 't3_Eway_Report'})-[:HAS_COLUMN]->(c:Column)
OPTIONAL MATCH (c)-[:MAPS_TO]->(upc:Column)<-[:HAS_COLUMN]-(up:Table)
RETURN c.name AS column, c.description,
       up.name AS source_table, upc.name AS source_column
ORDER BY c.name;
```

**Find JOIN conditions for a model:**

```cypher
MATCH (t:Table {name: 't3_delivery_mis_report'})-[:DEPENDS_ON]->(up:Table)
OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)-[:MAPS_TO]->(upc:Column)<-[:HAS_COLUMN]-(up)
RETURN up.name AS upstream_table,
       collect({model_col: c.name, upstream_col: upc.name}) AS join_conditions
ORDER BY upstream_table;
```

---

## 9. All Make Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available targets |
| `make setup` | One-time project setup (venv + install + .env) |
| `make venv` | Recreate virtual environment from scratch |
| `make reinstall` | Reinstall package in existing venv |
| **Lineage Pipeline** | |
| `make push-lineage` | Push YAML lineage files to Neo4j |
| `make push-dry-run` | Dry-run lineage push (preview only) |
| `make push-summary` | Show lineage summary without connecting to Neo4j |
| `make generate-joins` | Regenerate SQL JOIN queries from lineage YAML |
| `make patch-lineage` | Recompute column_lineage from SQL for known models |
| `make validate` | Validate all models (refs, columns, tables.yaml) |
| **Model Management** | |
| `make manage-add M=name` | Add a new model (use `DRY_RUN=1` for preview, `DBT_PATH=/path` for custom dbt) |
| `make manage-force-add M=name` | Force-add a model (overwrite existing YAML; also supports `DBT_PATH`) |
| `make manage-remove M=name` | Remove a model (use `DRY_RUN=1` for preview) |
| `make manage-list` | List all models with upstream/column counts |
| **Verification** | |
| `make verify` | Verify Neo4j: counts + all model→upstream joins |
| `make verify-counts` | Quick verify: Neo4j counts only |
| **Full Pipelines** | |
| `make push-all` | Standard cycle: push → joins → verify |
| `make push-all-validate` | Extended: push → joins → validate → verify |
| **PG→Neo4j (optional)** | |
| `make run` | Run PG→Neo4j schema sync |
| `make dry-run` | PG→Neo4j dry run |
| `make tables T=a,b` | PG→Neo4j with inline table list |
| `make clean-db` | Clear Neo4j database |
| **Docs** | |
| `make howto` | List available HOWTO documents |
| `make howto-add` | Show the HOWTO for adding a model |
| `make howto-remove` | Show the HOWTO for removing a model |
| `make howto-full` | Show the full combined HOWTO (add + remove) |
| `make workflow` | Show the internal workflow (what happens when adding a model) |

---

## 10. Project Structure

```
├── config/
│   ├── tables.yaml                    # Tables registered for the pipeline
│   ├── settings.yaml                  # Pipeline settings (clear_before_write, etc.)
│   ├── model_lineage/                 # Lineage YAML files (one per model)
│   │   ├── t3_Eway_Report.yml
│   │   ├── t3_*.yml                      # one per model
│   │   └── _generated_joins.sql       # Auto-generated SQL JOINs
│   └── lineage_inspection_queries.cypher  # Reference Cypher queries
│
├── postgres_to_neo4j/                 # Neo4j loader pipeline
│   ├── lineage_loader.py              # Reads YAML → writes to Neo4j
│   ├── cli.py                         # PG→Neo4j CLI
│   ├── config.py                      # Configuration reader
│   ├── postgres/                      # PG schema extractor
│   ├── neo4j/                         # Neo4j writer
│   └── models/                        # Data models
│
├── scripts/
│   ├── manage_models.py               # Add/remove/list models (auto YAML generation)
│   ├── sql_generator.py               # Generates SQL JOINs from YAML
│   ├── validate_all_models.py         # Validates all models against SQL + YAML
│   ├── patch_lineage_4_models.py      # Patches column lineage from SQL
│   ├── enrich_lineage.py              # Enriches YAML with CTE resolution
│   ├── audit_dependencies.py          # Audits SQL refs vs YAML upstreams
│   └── fix_source_columns.py          # Fixes stale source column references
│
├── .env                               # Credentials (DO NOT SHARE)
├── .env.example                       # Template for .env
├── Makefile                           # All commands
├── setup.sh                           # One-time setup script
├── pyproject.toml                     # Python package config
├── README.md                          # This file
├── HOWTO_add_model.md                 # Standalone guide: adding a model
├── HOWTO_remove_model.md              # Standalone guide: removing a model
├── HOWTO_add_remove_models.md         # Combined guide (add + remove)
└── WORKFLOW.md                        # Internal workflow: what happens when adding a model
```

---

## 11. Validation

Validate all models against their SQL source:

```bash
make validate
```

This checks:
1. Every SQL `{{ ref(...) }}` has a matching YAML upstream entry
2. Every column `source_table/source_column` has a corresponding `column_lineage`
3. All tables are registered in `config/tables.yaml`

To also patch column lineage from SQL for known models:

```bash
make patch-lineage
```

---

## 12. LLM Discovery Flow

An LLM can use these Cypher queries to understand the data. You can also
run `make verify` to see the live graph state.

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

**"Find the shortest path between two tables"**

```cypher
MATCH path = shortestPath(
  (a:Table {name: "t3_Eway_Report"})-[:DEPENDS_ON*]->(b:Table {name: "t1_prs_premise_master_hubops"})
)
RETURN [n IN nodes(path) | n.name] AS tables;
```

**"What are all available model→upstream joins?"**

```cypher
MATCH (t:Table)-[:DEPENDS_ON]->(up:Table)
OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)-[:MAPS_TO]->(upc:Column)
RETURN t.name AS model, up.name AS upstream,
       collect(DISTINCT {model_col: c.name, upstream_col: upc.name}) AS join_cols
ORDER BY model, upstream;
```

---

## 13. Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'neo4j'` | Run `make setup` or `make reinstall` |
| `Connection refused to localhost:7687` | Start Neo4j: `cd /path/to/neo4j/bin && ./neo4j start` |
| `cypher-shell: command not found` | Install neo4j client or use `pip install neo4j` |
| Wrong Neo4j password | Edit `.env` → `NEO4J_PASSWORD=correct_password` |
| `push-lineage` says "Found 0 models" | `.env` not sourced or YAML dir wrong — run `source .env && make push-lineage` |
| Columns have empty `source_table`/`source_column` | Auto-extractor couldn't determine source (CTE, `SELECT *`, complex expr) |
| `make verify` shows wrong counts | Run `make push-all` to rebuild graph; confirm `clear_before_write: true` in `config/settings.yaml` |
| YAML has wrong upstreams | Edit YAML file, run `make push-all` again |
| Need to start fresh | Run `make push-lineage` (clears graph and rewrites from YAML) |
| `manage-add` says model not found | Wrong model name or wrong dbt project path — check `ls /models/**/NAME.sql` or pass `DBT_PATH=/path` |
| Orphan upstream still in Neo4j after remove | `tables.yaml` still references it — remove manually or ignore (does no harm) |
| `manage-add` produces empty `column_lineage` | Model uses CTEs or `SELECT *` — fill `column_lineage` manually (see `make howto`) |
