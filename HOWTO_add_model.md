# HOWTO: Add a New Model

Add a dbt model to the Neo4j lineage pipeline: auto-detect its upstream tables,
parse SELECT columns, generate the YAML lineage file, and push to Neo4j.

---

## Quick Reference

```bash
# Preview only (dry run)
make manage-add M=model_name DRY_RUN=1

# Preview with custom dbt project path
make manage-add M=model_name DRY_RUN=1 DBT_PATH=/path/to/dbt_project

# Commit the model
make manage-add M=model_name

# Push to Neo4j + verify
make push-all
```

---

## Step-by-Step Instructions

### Step 1: Preview (dry run)

```bash
cd /home/ubuntu/neo4j
make manage-add M=t3_YOUR_MODEL_NAME DRY_RUN=1
```

**Example output:**

```
ADD MODEL: t3_day_wise_operation_count
  ✓ Found SQL: .../models/HubOps_Dashboard/t3_day_wise_operation_count.sql
  ✓ Upstream tables (1): t2_master_hubops
  ✓ Columns (4 total, 4 with source mapping)

  ── Preview ──────────────────────────────────
  model:
    name: t3_day_wise_operation_count
    schema: silver_layer
    materialized: table
    ...
  ──────────────────────────────────────────────
  (dry-run — no files written)
```

**Check these things in the preview:**
- Are all upstream tables detected? (every `{{ ref() }}` in the SQL should appear)
- Does every column have `source_table` and `source_column` filled in?
- Does the `column_lineage` look correct?

If columns have empty `source_table`/`source_column`, see section below on
[When auto-extraction fails](#when-the-auto-extractor-cant-determine-column-lineage).

### Step 2: Commit the model

```bash
make manage-add M=t3_YOUR_MODEL_NAME
```

This writes:
- `config/model_lineage/t3_YOUR_MODEL_NAME.yml` — the lineage YAML
- Adds the model **and any new upstream tables** to `config/tables.yaml`

**If the YAML already exists**, use `--force` to overwrite:

```bash
make manage-force-add M=t3_YOUR_MODEL_NAME
```

### Step 3: Review the YAML

```bash
nano config/model_lineage/t3_YOUR_MODEL_NAME.yml
```

Verify:
- `columns[].source_table` — does each column come from the right upstream?
- `columns[].source_column` — does each column map to the right upstream column?
- `upstreams[].column_lineage` — are the from/to pairs correct?
- Are any `{{ ref() }}` calls missing from the upstreams list?

Fix any issues by editing the YAML directly, then run `make push-all`.

### Step 4: Push to Neo4j

```bash
make push-all
```

This runs:
1. `make push-lineage` — loads all YAML files into Neo4j (clears & rewrites graph)
2. `make generate-joins` — regenerates the SQL JOIN queries
3. `make verify` — shows graph counts and all model→upstream joins

### Step 5: Verify in Neo4j

```bash
source .env
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD"
```

Run these checks:

```cypher
// Does the model table exist?
MATCH (t:Table {name: 't3_YOUR_MODEL_NAME'}) RETURN t;

// Does it depend on the right upstreams?
MATCH (t:Table {name: 't3_YOUR_MODEL_NAME'})-[:DEPENDS_ON]->(up:Table)
RETURN up.name;

// Do columns map correctly?
MATCH (t:Table {name: 't3_YOUR_MODEL_NAME'})-[:HAS_COLUMN]->(c:Column)
OPTIONAL MATCH (c)-[:MAPS_TO]->(upc:Column)
RETURN c.name, c.description, upc.name AS maps_to, upc.source_table;
```

---

## Using a Custom dbt Project Path

By default, the script looks for models in:
`/home/ubuntu/smile_dbt_model/smile_dbt_model`

If your dbt project lives elsewhere, pass `--dbt-path` (or `-d` for short):

```bash
# Via Makefile
make manage-add M=t3_YOUR_MODEL_NAME DBT_PATH=/path/to/dbt_project

# Direct python invocation
python scripts/manage_models.py add --model t3_YOUR_MODEL_NAME --dbt-path /path/to/dbt_project

# With dry-run
python scripts/manage_models.py add --model t3_YOUR_MODEL_NAME --dry-run -d /path/to/dbt_project
```

---

## Direct Python Invocation (without Make)

```bash
# Preview
python scripts/manage_models.py add --model t3_YOUR_MODEL_NAME --dry-run

# Preview with custom dbt path
python scripts/manage_models.py add --model t3_YOUR_MODEL_NAME --dry-run -d /path/to/dbt

# Commit
python scripts/manage_models.py add --model t3_YOUR_MODEL_NAME

# Force overwrite
python scripts/manage_models.py add --model t3_YOUR_MODEL_NAME --force
```

---

## When the Auto-Extractor Can't Determine Column Lineage

The script handles these SQL patterns automatically:

| Pattern | Auto-detected? |
|---|---|
| `SELECT t.col1, t.col2` (aliased columns) | Yes |
| `SELECT col1, col2` (bare columns, single upstream) | Yes |
| `SELECT DATE(operation_time)` (function-wrapped) | Yes |
| `SELECT CASE WHEN ... THEN t.col END` (CASE expressions) | Yes |
| `SELECT count(distinct ... t.col ...)` (aggregate, single column ref) | Yes |

It does **NOT** handle:

| Pattern | What happens | Fix |
|---|---|---|
| CTEs (`WITH cte AS (...) SELECT ...`) | No column mapping | Add `column_lineage` manually |
| `SELECT *` | Column names extracted, no source mapping | Add `column_lineage` manually |
| Multiple upstreams, no alias prefix on columns | Maps all to first upstream | Fix `source_table` manually |

To fix a column manually, edit the YAML and add entries to `column_lineage`:

```yaml
upstreams:
  - name: t2_master_hubops
    schema: silver_layer
    column_lineage:
      - column: shipments       # ← model column name
        from_column: awb_number # ← upstream table column name
      - column: date
        from_column: operation_time
```

Then run `make push-all`.

---

## YAML Structure Reference

```yaml
model:
  name: t3_YOUR_MODEL
  schema: silver_layer
  materialized: table
  file_path: models/YourFolder/t3_YOUR_MODEL.sql
  columns:
    - name: column_name
      expression: SQL expression (original)
      description: ''
      source_table: upstream_table_name
      source_column: upstream_column_name
  upstreams:
    - name: upstream_table_name
      schema: silver_layer
      column_lineage:
        - column: column_name
          from_column: upstream_column_name
```

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| `SQL file not found` | Wrong model name or wrong dbt path | Use correct model name or pass `DBT_PATH=...` |
| `YAML already exists` | Model was previously added | Use `make manage-force-add M=name` to overwrite |
| Columns have empty source | CTE / `SELECT *` / complex expression | Fill `column_lineage` manually in YAML |
| Upstream missing from YAML | SQL uses `{{ ref() }}` not detected | Check SQL syntax, add upstream entry manually |
| `make push-all` shows wrong counts | `clear_before_write: false` in settings | Check `config/settings.yaml` |
| Wrong upstream table detected | Alias resolution failed | Edit `source_table` in YAML directly |
