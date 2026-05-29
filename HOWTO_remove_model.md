# HOWTO: Remove a Model

Remove a dbt model from the Neo4j lineage pipeline: delete its YAML file,
clean up orphaned upstream tables from `tables.yaml`, and rebuild the graph.

---

## Quick Reference

```bash
# Preview only (dry run)
make manage-remove M=model_name DRY_RUN=1

# Commit the removal
make manage-remove M=model_name

# Push to Neo4j + verify
make push-all
```

---

## Understanding Orphans

When you remove a model, some upstream tables may become **orphans** — tables
that were only referenced by the removed model and are no longer used by any
remaining model.

The script **automatically removes** orphaned upstreams from `config/tables.yaml`.
If the orphaned table is still useful outside this pipeline (e.g., it is queried
directly in SQL), it's harmless to leave it in `tables.yaml` — it simply won't
create any edges in Neo4j since no model maps to it.

**Note:** If the model being removed is itself an upstream of other models
(inter-model dependency), the script will detect this and NOT remove it.
Only truly orphaned tables (used by zero remaining models) are removed.

---

## Step-by-Step Instructions

### Step 1: Preview (dry run)

```bash
cd /home/ubuntu/neo4j
make manage-remove M=t3_YOUR_MODEL_NAME DRY_RUN=1
```

**Example output (no orphans):**

```
REMOVE MODEL: t3_day_wise_operation_count
  ✓ No orphaned upstreams — all upstream tables are
    still used by other models.

  (dry-run — no files deleted)
  Would remove 't3_day_wise_operation_count' from config/tables.yaml
```

**Example output (with orphans):**

```
REMOVE MODEL: t3_delivery_mis_report
  ⚠ 1 upstream table(s) will become ORPHANED:
    - t2_hub_outscan_wise_awb_level_details

  (dry-run — no files deleted)
  Would remove 't3_delivery_mis_report' from config/tables.yaml
  Would remove orphaned upstreams from tables.yaml: t2_hub_outscan_wise_awb_level_details
```

**Review the orphan list.** If any orphaned tables should be preserved (e.g.,
they're queried directly), you can re-add them to `tables.yaml` after removal.

### Step 2: Commit the removal

```bash
make manage-remove M=t3_YOUR_MODEL_NAME
```

This deletes:
- `config/model_lineage/t3_YOUR_MODEL_NAME.yml`
- Removes `t3_YOUR_MODEL_NAME` from `config/tables.yaml`
- Removes any orphaned upstream tables from `config/tables.yaml`

### Step 3: Push to Neo4j

```bash
make push-all
```

This runs:
1. `make push-lineage` — reloads all remaining YAML files (graph rebuilt from scratch)
2. `make generate-joins` — regenerates SQL JOIN queries
3. `make verify` — shows updated graph counts

After this, the model and its orphaned upstreams are gone from Neo4j.

### Step 4: Verify the model is gone

```bash
source .env
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  "MATCH (t:Table {name: 't3_YOUR_MODEL_NAME'}) RETURN t;"
```

Should return zero rows.

---

## Direct Python Invocation (without Make)

```bash
# Preview
.venv/bin/python scripts/manage_models.py remove --model t3_YOUR_MODEL_NAME --dry-run

# Commit
.venv/bin/python scripts/manage_models.py remove --model t3_YOUR_MODEL_NAME
```

Note: `--dbt-path` is not needed for remove — the dbt project path is only used
when adding models (to find the SQL file). Removal only touches YAML files and
`tables.yaml` in the Neo4j project.

---

## What Happens to Each File

| File | What happens |
|---|---|
| `config/model_lineage/t3_YOUR_MODEL_NAME.yml` | **Deleted** |
| `config/tables.yaml` | Model name removed. Orphaned upstreams removed. |
| Neo4j graph | Model + orphaned upstream tables + columns + edges **removed** on next `make push-lineage` |
| `config/model_lineage/_generated_joins.sql` | **Regenerated** without the removed model's queries |

---

## Re-adding a Removed Model

If you remove a model accidentally, re-add it:

```bash
make manage-add M=t3_YOUR_MODEL_NAME
make push-all
```

The YAML is regenerated from the SQL file. If you had manual `column_lineage`
edits, you'll need to re-apply them.

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| `YAML not found` | Model name is wrong or already removed | Check `ls config/model_lineage/ \| grep NAME` |
| Model still in Neo4j after removal | Haven't run `make push-lineage` yet | Run `make push-all` to rebuild graph |
| Orphaned upstream still in Neo4j | `tables.yaml` still references it | Remove manually from `config/tables.yaml`, then `make push-all` |
| Model still in `tables.yaml` after remove | Script may have been interrupted | Remove manually from `config/tables.yaml` |
| Inter-model dependency not removed as orphan | Correct — another model still needs it | No action needed; this is correct behavior |
