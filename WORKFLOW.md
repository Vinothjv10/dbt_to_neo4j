# Workflow: What Happens When You Add a Model

This document explains the internal flow — step by step — from the moment you
run `make manage-add M=model_name` to the final Neo4j graph. Each section
describes what the scripts actually do, how they determine lineage, and how
JOIN columns are discovered.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  make manage-add M=t3_X                                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Extract SQL refs  ──►  detect upstream tables             │  │
│  │ 2. Parse SELECT      ──►  resolve aliases, extract columns   │  │
│  │ 3. Map to upstream   ──►  determine source_table/source_col  │  │
│  │ 4. Build column_lineage  ►  group by upstream table           │  │
│  │ 5. Generate YAML     ──►  write model_lineage/t3_X.yml       │  │
│  │ 6. Update tables.yaml   ►  register model + new upstreams    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  make push-all                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 7. push-lineage    ──►  read YAML → create Neo4j nodes/edges │  │
│  │ 8. generate-joins  ──►  build SQL JOINs from column lineage  │  │
│  │ 9. verify          ──►  run Cypher counts against Neo4j      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Find the SQL File (`find_sql_file`)

**Script:** `scripts/manage_models.py` → `cmd_add()` → `find_sql_file()`

```
def find_sql_file(model_name, dbt_root):
    for root, dirs, files in os.walk(Path(dbt_root) / "models"):
        for f in files:
            if f == f"{model_name}.sql":
                return Path(root) / f
    return None
```

Walks the dbt project's `models/` directory tree looking for a file whose name
matches the model name exactly (e.g., `t3_delivery_mis_report.sql`). If not
found, the script exits with an error.

---

## Step 2: Extract Upstream Tables (`extract_refs`)

**Script:** `manage_models.py` → `extract_refs()`

Reads the raw SQL and finds all `{{ ref('table_name') }}` patterns:

```python
def extract_refs(sql):
    return sorted(set(re.findall(
        r"""ref\s*\(\s*['"]([^'"]+)['"]\s*\)""", sql
    )))
```

**Regex in plain English:** Find `ref(` followed by an optional quote,
capture the table name, followed by an optional close quote and `)`.

Self-references (`ref('t3_X')` where the model references its own name)
are filtered out.

**Example:** Given this SQL:
```sql
SELECT ...
FROM {{ ref('t2_master_hubops') }} srs
LEFT JOIN {{ ref('t1_prs_premise_master_hubops') }} ppm
  ON srs.awb_number = ppm.awb_number
```

The extracted upstreams are:
```
["t1_prs_premise_master_hubops", "t2_master_hubops"]
```

---

## Step 3: Resolve Jinja & Clean SQL (`resolve_refs` + `strip_jinja`)

**Script:** `manage_models.py` → `resolve_refs()` and `strip_jinja()`

Two cleanup steps before column parsing:

1. **`resolve_refs()`** — replaces `{{ ref('name') }}` with just `name`
   so the SQL parser sees plain table names:
   ```
   FROM t2_master_hubops srs
   ```

2. **`strip_jinja()`** — removes any remaining `{% ... %}` blocks
   (dbt control flow like `{% if ... %}`) and `{{ ... }}` variables.

3. Strip single-line SQL comments (`-- this is a comment`).

4. Strip string literals (`'some value'` → `''`) so they don't confuse
   the column parser.

---

## Step 4: Build Alias Map (`extract_alias_map`)

**Script:** `manage_models.py` → `extract_alias_map()`

To understand which table a column like `srs.awb_number` comes from,
the script builds an alias-to-table-name mapping from `FROM` and `JOIN` clauses:

```python
def extract_alias_map(sql_clean, upstreams):
    alias_map = {}
    # Each upstream name is a valid alias too
    for up in upstreams:
        alias_map[up.lower()] = up

    # FROM aliases: "FROM table_name alias" or "FROM table_name AS alias"
    from_matches = re.findall(
        r'\bFROM\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?',
        sql_clean, re.IGNORECASE
    )
    # JOIN aliases: same pattern for JOIN clauses
    join_matches = re.findall(
        r'\bJOIN\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?',
        sql_clean, re.IGNORECASE
    )
    ...
```

**Example output for this SQL:**
```sql
FROM t2_master_hubops srs
JOIN t1_prs_premise_master_hubops ppm
```

```
alias_map = {
    "t2_master_hubops": "t2_master_hubops",   # direct name
    "srs": "t2_master_hubops",                 # alias
    "t1_prs_premise_master_hubops": "t1_prs_premise_master_hubops",
    "ppm": "t1_prs_premise_master_hubops",
}
```

---

## Step 5: Parse SELECT Columns (`extract_select_columns`)

**Script:** `manage_models.py` → `extract_select_columns()`

### 5a. Find the SELECT clause

If the SQL has CTEs (`WITH ... AS (...)`), they are stripped first,
leaving only the final `SELECT ... FROM ...` query.

A regex finds everything between `SELECT` and `FROM`:

```python
select_match = re.search(
    r'\bSELECT\b\s+(.*?)\bFROM\b',
    without_ctes, re.IGNORECASE | re.DOTALL
)
```

### 5b. Split by top-level commas

The SELECT clause is split by commas that are NOT inside parentheses
(`split_top_level_commas`), yielding individual column expressions.

For example:
```sql
SELECT srs.awb_number,
       DATE(srs.operation_time) AS date,
       status,
       COUNT(DISTINCT srs.awb_number) AS total
```

Becomes four expressions:
1. `srs.awb_number`
2. `DATE(srs.operation_time) AS date`
3. `status`
4. `COUNT(DISTINCT srs.awb_number) AS total`

### 5c. Parse each expression (`parse_select_expr`)

Each expression goes through this pipeline:

**Step 1: Extract the column alias.**
- If `AS alias` is present, the alias is the column name.
- If no `AS`, the last word is treated as the column name.

**Step 2: Simplify the expression.**
- Strip function wrappers: `COUNT(...)`, `SUM(...)`, `DATE(...)`, `UPPER(...)`, etc.
- Remove SQL keywords: `DISTINCT`, `CASE`, `WHEN`, `THEN`, `ELSE`, `END`, etc.
- Remove string literals.

**Step 3: Find `alias.column` references.**
The simplified expression is scanned for `word.word` patterns:

```python
refs = re.findall(r'(?<![A-Za-z_])([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)', simplified)
```

The last such reference found is used as the source.

**Step 4: Resolve alias to table name.**
The alias prefix is looked up in the `alias_map` built in Step 4.
If found, `source_table` = mapped table name, `source_column` = column name.

**Step 5: Fallback for bare columns.**
If no `alias.column` pattern was found (e.g., just `status`), the
expression is scanned for bare word tokens (excluding SQL keywords).
The last non-keyword token is used as the column name, and the
**first upstream table** is assigned as the source.

This fallback is imperfect but works for models with a single upstream.

### Worked example

For `DATE(srs.operation_time) AS date`:
```
alias = "date"
simplified = "srs.operation_time"        (DATE() stripped)
refs found = [("srs", "operation_time")]
alias_map["srs"] = "t2_master_hubops"
→ source_table = "t2_master_hubops"
→ source_column = "operation_time"
```

For `COUNT(DISTINCT srs.awb_number) AS total`:
```
alias = "total"
simplified = "srs.awb_number"            (COUNT, DISTINCT stripped)
refs found = [("srs", "awb_number")]
alias_map["srs"] = "t2_master_hubops"
→ source_table = "t2_master_hubops"
→ source_column = "awb_number"
```

For `status` (bare, no alias):
```
alias = "status"
simplified = "status"                     (no function wrappers)
refs found = []                           (no dot notation)
fallback: bare column token = "status"
→ source_table = "t2_master_hubops"      (first upstream)
→ source_column = "status"
```

---

## Step 6: Build Column Lineage (`generate_column_lineage`)

**Script:** `manage_models.py` → `generate_column_lineage()`

Groups the parsed columns by their `source_table`, producing a
`column_lineage` list per upstream:

```python
lineage_map = {}
for col in columns:
    src_t = col.get("source_table", "")
    src_c = col.get("source_column", "")
    if src_t and src_c:
        lineage_map.setdefault(src_t, []).append({
            "column": col["name"],
            "from_column": src_c,
        })
```

**Example output:**
```yaml
upstreams:
  - name: t2_master_hubops
    schema: silver_layer
    column_lineage:
      - column: date
        from_column: operation_time
      - column: status
        from_column: status
      - column: shipments
        from_column: awb_number
      - column: bags
        from_column: awb_number
```

Each `column_lineage` entry means: "the model's column X is sourced from
the upstream table's column Y." This is what the `MAPS_TO` edge in Neo4j
represents.

---

## Step 7: Generate YAML & Update tables.yaml

**Script:** `manage_models.py` → `generate_model_yaml()` + `add_to_tables_yaml()`

The YAML file is written to `config/model_lineage/t3_X.yml`:

```yaml
model:
  name: t3_X
  schema: silver_layer
  materialized: table
  file_path: models/SomeFolder/t3_X.sql
  columns:
    - name: column_name
      expression: original SQL expression
      description: ''
      source_table: upstream_table
      source_column: upstream_column
  upstreams:
    - name: upstream_table
      schema: silver_layer
      column_lineage:
        - column: model_col
          from_column: upstream_col
```

And the model name + any new upstream table names are appended to
`config/tables.yaml` (which was originally the table list for the
PG→Neo4j schema sync pipeline, now reused for table registration).

---

## Step 8: Push to Neo4j (`make push-lineage`)

**Script:** `postgres_to_neo4j/lineage_loader.py` → reads YAML, writes Cypher

### 8a. Clear the graph

If `config/settings.yaml` has `clear_before_write: true`, all existing
nodes and relationships are deleted first:

```cypher
MATCH (n) DETACH DELETE n
```

This ensures the graph always reflects the current YAML state.

### 8b. Create Schema node

```cypher
MERGE (s:Schema {name: "silver_layer"})
```

### 8c. Create Table nodes

For each model YAML file and each upstream, a Table node is created:

```cypher
MERGE (t:Table {name: "table_name", schema: "silver_layer"})
MERGE (s:Schema {name: "silver_layer"})-[:HAS_TABLE]->(t)
```

### 8d. Create Column nodes

For each column listed in the YAML's `columns:` section:

```cypher
MERGE (c:Column {name: "column_name", table: "table_name"})
SET c.description = COALESCE(c.description, "description_from_yaml")
SET c.data_type = "..."
MERGE (t:Table {name: "table_name"})-[:HAS_COLUMN]->(c)
```

`MERGE` + `COALESCE` on description means: if the column already exists
(from a previous push), keep the existing description unless the new one
is non-empty. This preserves descriptions from upstream models.

### 8e. Create DEPENDS_ON edges

For each upstream listed in the YAML:

```cypher
MATCH (t:Table {name: "model_name"})
MATCH (up:Table {name: "upstream_name"})
MERGE (t)-[:DEPENDS_ON]->(up)
```

This creates the table-level dependency graph that Neo4j can traverse
(useful for finding join paths between tables).

### 8f. Create MAPS_TO edges (column-level lineage)

For each `column_lineage` entry in the YAML:

```cypher
MATCH (t:Table {name: "model_name"})-[:HAS_COLUMN]->(c:Column {name: "model_col"})
MERGE (up:Table {name: "upstream_name"})-[:HAS_COLUMN]->(upc:Column {name: "upstream_col"})
SET upc.description = COALESCE(upc.description, c.description)
MERGE (c)-[:MAPS_TO]->(upc)
```

Key details:
- `MATCH` on the model's own column (must exist, created in step 8d)
- `MERGE` on the upstream column (may not exist yet — creates it if needed)
- `SET ... COALESCE` — propagates the model's column description to the
  upstream column if the upstream column doesn't have one yet
- `MERGE` on MAPS_TO — ensures no duplicate edges

This is the core lineage: every `MAPS_TO` edge says "this model column
is derived from that upstream column."

### Neo4j graph after push

```
(:Schema {name: "silver_layer"})
    │
    ├──[:HAS_TABLE]──►(:Table {name: "t3_X"})
    │                      │
    │                      ├──[:HAS_COLUMN]──►(:Column {name: "date"})
    │                      ├──[:HAS_COLUMN]──►(:Column {name: "status"})
    │                      ├──[:HAS_COLUMN]──►(:Column {name: "shipments"})
    │                      │
    │                      ├──[:DEPENDS_ON]──►(:Table {name: "t2_master_hubops"})
    │                      │                       │
    │                      │                       ├──[:HAS_COLUMN]──►(:Column {name: "operation_time"})
    │                      │                       ├──[:HAS_COLUMN]──►(:Column {name: "status"})
    │                      │                       ├──[:HAS_COLUMN]──►(:Column {name: "awb_number"})
    │                      │
    │                      └── (column MAPS_TO edges)
    │                           date ──MAPS_TO──► operation_time
    │                           status─MAPS_TO──► status
    │                           shipments─MAPS_TO─► awb_number
    │
    └──[:HAS_TABLE]──►(:Table {name: "t2_master_hubops"})
                               ...
```

---

## Step 9: Generate SQL JOINs (`make generate-joins`)

**Script:** `scripts/sql_generator.py`

Reads the YAML lineage files and generates a SQL file at
`config/model_lineage/_generated_joins.sql`.

### How join columns are determined

For each model and each of its upstreams:

1. Look at the `column_lineage` entries for that upstream.
2. Each entry `{column: X, from_column: Y}` tells you:
   - `X` is a column in the model
   - `Y` is a column in the upstream table
3. These matching column pairs become the `ON` conditions:

```sql
-- Model: t3_X → Upstream: t2_master_hubops
SELECT
    t3_X.date,
    t3_X.status,
    t3_X.shipments,
    t2_master_hubops.operation_time,   -- column lineage source
    t2_master_hubops.status,            -- column lineage source
    t2_master_hubops.awb_number         -- column lineage source
FROM silver_layer.t3_X
LEFT JOIN silver_layer.t2_master_hubops
    ON t3_X.date = t2_master_hubops.operation_time   -- from column_lineage
    AND t3_X.status = t2_master_hubops.status         -- from column_lineage
    -- shipments → awb_number intentionally omitted
    -- (aggregate columns are skipped in join conditions)
```

**Which columns become JOIN conditions:** Non-aggregate columns with
a direct 1:1 column-lineage mapping. Aggregate columns like
`COUNT(DISTINCT ...)` are listed in SELECT but skipped in ON clauses.

### What the generated SQL is used for

An LLM (or any query tool) can use this file to understand:
- Which tables join to which other tables
- Which column pairs form the join conditions
- The exact SELECT columns available per model

---

## Step 10: Verify (`make verify`)

**Script:** `Makefile` → `cypher-shell`

Runs two queries:

**Counts:**
```cypher
MATCH (s:Schema) RETURN count(s);     -- expected: 1
MATCH (t:Table) RETURN count(t);      -- all upstreams + models
MATCH (c:Column) RETURN count(c);     -- all columns
MATCH ()-[d:DEPENDS_ON]->() RETURN count(d);  -- table-level deps
MATCH ()-[m:MAPS_TO]->() RETURN count(m);     -- column-level lineage
```

**All model→upstream joins (for LLM discovery):**
```cypher
MATCH (t:Table)-[:DEPENDS_ON]->(up:Table)
OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)-[:MAPS_TO]->(upc:Column)
RETURN t.name AS model, up.name AS upstream,
       collect(DISTINCT {model_col: c.name, upstream_col: upc.name}) AS join_cols
ORDER BY model, upstream;
```

This returns a machine-readable list of every join path in the graph.

---

## Summary: Where Each Piece of Information Comes From

| Information | Source | How it's determined |
|---|---|---|
| **Model name** | `--model` CLI arg | Direct user input |
| **SQL file path** | dbt project `models/` tree | Walks directories matching `model_name.sql` |
| **Upstream tables** | SQL `{{ ref('...') }}` calls | Regex capture from raw SQL |
| **Table aliases** | `FROM t AS a` / `JOIN t a` | Regex on cleaned SQL |
| **Column names** | SELECT clause (after `AS`) | Strip functions, extract alias |
| **Source table per column** | `alias.column` prefix + alias map | Match prefix to `FROM`/`JOIN` aliases |
| **Source column per column** | Column reference after alias | The column name in `alias.col` |
| **Column descriptions** | YAML `columns[].description` | Set in YAML, propagated to upstreams |
| **DEPENDS_ON edges** | YAML `upstreams[].name` | One edge per upstream table |
| **MAPS_TO edges** | YAML `upstreams[].column_lineage` | One edge per column mapping |
| **JOIN conditions** | `column_lineage` pairs | Model column = upstream column used as ON clause |

---

## When Things Can Go Wrong

| Stage | Failure mode | Root cause |
|---|---|---|
| Step 2 (refs) | Wrong upstream list | Regex misses `ref('name')` if SQL uses unusual quoting |
| Step 4 (alias map) | Wrong `source_table` | JOIN has no alias or uses subquery alias |
| Step 5c (parse) | Empty `source_column` | Expression is too complex (`COUNT(DISTINCT CASE WHEN ...`) |
| Step 5c (fallback) | Wrong `source_table` | Bare columns with multiple upstreams — always picks first |
| Step 8f (MAPS_TO) | No MAPS_TO edges | Upstream column name doesn't match any in Neo4j |
| Step 9 (joins) | Wrong JOIN conditions | `column_lineage` has incorrect from_column |
