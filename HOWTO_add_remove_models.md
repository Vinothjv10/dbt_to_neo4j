# HOWTO: Add or Remove a dbt Model

This document covers exactly two operations:

1. **Add a model** – generate its lineage YAML from SQL, push to Neo4j
2. **Remove a model** – delete its YAML, clean up orphan upstreams, push to Neo4j

---

## Table stakes – what the auto-extractor CAN and CANNOT handle

| Situation | Auto-extracts? | What to expect |
|---|---|---|
| Simple `SELECT col1, col2, ...` with aliased columns (`t.col`) | ✅ Yes | `source_table` and `source_column` resolve correctly |
| Bare columns (`status`, `awb_number`) with single upstream | ✅ Yes | Falls back to the first upstream table as source |
| Function-wrapped columns (`DATE(operation_time)`) | ✅ Yes | Extracts the inner column reference |
| `CASE WHEN ... THEN column END` | ✅ Yes | Extracts the column inside the expression |
| Complex expressions (`count(distinct case when ... then col end)`) | ⚠ Partial | Falls back to the column name if it finds one inside the expression |
| CTEs (`WITH cte1 AS (...) SELECT ... FROM cte1`) | ❌ No | Column lineage will be empty. You must write `column_lineage` manually (see Appendix). |
| `SELECT *` | ❌ No | Column names are extracted (from dbt manifest) but no source mapping. Must be filled manually. |
| Multiple upstreams in `FROM`/`JOIN` without explicit source aliases | ⚠ Partial | Each column maps to the first upstream table. Check the YAML after generation. |

After every `add`, review the generated YAML before pushing.

---

## How to add a model

### Step 1: Preview only (dry run)

```bash
cd /home/ubuntu/neo4j
make manage-add M=YOUR_MODEL_NAME DRY_RUN=1
```

Example:

```bash
make manage-add M=t3_day_wise_operation_count DRY_RUN=1
```

The script prints:

- Which `.sql` file it found
- Which `{{ ref() }}` upstreams it detected
- How many columns it found and how many have source mappings
- The full YAML it will generate

**Stop here and read the preview.** If `column_lineage` entries are missing or wrong, you will need to fill them manually. See Appendix below.

### Step 2: Commit the model

```bash
make manage-add M=YOUR_MODEL_NAME
```

This writes two files:

- `config/model_lineage/YOUR_MODEL_NAME.yml` – the lineage definition
- Adds the model name to `config/tables.yaml` – so the pipeline knows about it

### Step 3: Review the generated YAML

```bash
nano config/model_lineage/YOUR_MODEL_NAME.yml
```

Check:

- `columns[].source_table` – does each column point to the right upstream table?
- `columns[].source_column` – does each column point to the right upstream column?
- `upstreams[].column_lineage` – are the from/to column pairs correct?
- `upstreams[]` – does every `{{ ref() }}` in the SQL have a corresponding upstream entry? (The script should catch this, but double-check.)

If something is wrong, edit the YAML by hand. If a column has no source, see Appendix.

### Step 4: Push to Neo4j

```bash
make push-all
```

This runs three things:

1. `make push-lineage` – loads all YAML files into Neo4j (clears and rewrites the graph)
2. `make generate-joins` – regenerates the SQL JOIN queries file
3. `make verify` – prints Neo4j counts and discovery queries

### Step 5: Verify in Neo4j

```bash
source .env
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD"
```

Run these checks:

```cypher
// Does the model table exist?
MATCH (t:Table {name: "YOUR_MODEL_NAME"}) RETURN t;

// Does it depend on the right upstreams?
MATCH (t:Table {name: "YOUR_MODEL_NAME"})-[:DEPENDS_ON]->(up:Table)
RETURN up.name;

// Do columns map correctly?
MATCH (t:Table {name: "YOUR_MODEL_NAME"})-[:HAS_COLUMN]->(c:Column)
OPTIONAL MATCH (c)-[:MAPS_TO]->(upc:Column)
RETURN c.name, c.description, upc.name AS maps_to, upc.source_table;
```

---

## How to remove a model

### Step 1: Preview only (dry run)

```bash
cd /home/ubuntu/neo4j
make manage-remove M=YOUR_MODEL_NAME DRY_RUN=1
```

Example:

```bash
make manage-remove M=t3_day_wise_operation_count DRY_RUN=1
```

The script reports:

- Which upstreams (if any) would become **orphans** – tables no longer referenced by any remaining model
- **Orphan handling**: The script **automatically removes** orphaned upstreams from `tables.yaml`. If an orphaned table is still useful outside this pipeline, you can re-add it later.

Example output:

```
  ✓ No orphaned upstreams — all upstream tables are
    still used by other models.
```

### Step 2: Remove the model

```bash
make manage-remove M=YOUR_MODEL_NAME
```

This deletes:

- `config/model_lineage/YOUR_MODEL_NAME.yml` – the lineage YAML
- Removes `YOUR_MODEL_NAME` from `config/tables.yaml`
- Removes any orphaned upstream tables from `config/tables.yaml`

### Step 3: Push to Neo4j

```bash
make push-all
```

This clears the graph and reloads only the remaining models. Orphan tables (and their columns) are removed from Neo4j automatically since the graph is rebuilt from scratch.

### Step 4: Verify

```bash
source .env
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "MATCH (t:Table {name: 'YOUR_MODEL_NAME'}) RETURN t;"
```

Should return zero rows.

---

## Appendix: Filling column lineage manually

If the auto-extractor couldn't determine where a column comes from (CTEs, `SELECT *`, complex expressions), edit the YAML directly.

Open the file:

```bash
nano config/model_lineage/YOUR_MODEL_NAME.yml
```

Find the `upstreams` section and add or fix `column_lineage` entries:

```yaml
upstreams:
  - name: t2_master_hubops
    schema: silver_layer
    column_lineage:
      - column: shipments
        from_column: awb_number
      - column: date
        from_column: operation_time
```

Each entry means: "this model's column X comes from upstream table's column Y."

After editing, run:

```bash
make push-all
```

### Re-running the patch script for known-broken models

Four models previously required post-generation patching. If you add a model that uses CTEs or complex JOINs, you can run the patch script which re-extracts column lineage from SQL for those models:

```bash
.venv/bin/python scripts/patch_lineage_4_models.py
```

This only patches the four hard-coded models (`t3_Eway_Report`, `t3_master_booking_hubops_delivery`, `t3_rpt_delivery_channel_analysis`, `t3_shipments_inscan_vs_outscan_report`). To add your model to the patch list, edit the script and add its name to the `MODELS` list.

### Quick reference: YAML structure

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
      source_table: upstream_table_name    # ← which upstream table
      source_column: upstream_column_name  # ← which upstream column
  upstreams:
    - name: upstream_table_name
      schema: silver_layer
      column_lineage:
        - column: column_name              # ← model column
          from_column: upstream_column_name # ← upstream column
```

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `make push-lineage` says "Found 0 models" | `.env` not sourced or YAML dir wrong | Run `source .env && make push-lineage` |
| Columns have empty `source_table`/`source_column` | Auto-extractor couldn't determine source (CTE, `SELECT *`, complex expr) | Fill `column_lineage` manually in YAML, then `make push-all` |
| `make push-all` shows wrong counts | `clear_before_write: true` in settings.yaml is required for clean rebuilds | Check `config/settings.yaml` has `clear_before_write: true` |
| `make manage-add M=X` says model not found | Wrong model name or wrong dbt project path | Check model name or pass `DBT_PATH=/path/to/dbt` |
| Orphan upstream still in Neo4j after remove | `tables.yaml` still references it | Either remove it from `tables.yaml` or ignore it (it does no harm) |
