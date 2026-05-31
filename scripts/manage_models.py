#!/usr/bin/env python3
"""
Manage dbt models in the Neo4j lineage pipeline.

Usage:
  # Add a new model (auto-detect upstreams, columns, join keys)
  python scripts/manage_models.py add --model t3_day_wise_operation_count

  # Preview add without writing
  python scripts/manage_models.py add --model t3_day_wise_operation_count --dry-run

  # Remove a model (safely check for orphan upstreams)
  python scripts/manage_models.py remove --model t3_day_wise_operation_count

  # Preview remove without deleting
  python scripts/manage_models.py remove --model t3_day_wise_operation_count --dry-run

  # Push added model to Neo4j (after review)
  make push-lineage
"""
import argparse, json, os, re, sys, yaml
from pathlib import Path

# ── Default Paths ──────────────────────────────────────────────────────
DEFAULT_DBT_ROOT = "/home/ubuntu/smile_dbt_model/smile_dbt_model"
YAML_DIR = Path("/home/ubuntu/neo4j/config/model_lineage")
TABLES_YAML = Path("/home/ubuntu/neo4j/config/tables.yaml")

# ── Helpers ───────────────────────────────────────────────────────────

def find_sql_file(model_name, dbt_root):
    """Find the .sql file for a model in the dbt project."""
    for root, dirs, files in os.walk(Path(dbt_root) / "models"):
        for f in files:
            if f == f"{model_name}.sql":
                return Path(root) / f
    return None

def extract_refs(sql):
    """Extract {{ ref('...') }} calls from raw SQL."""
    return sorted(set(re.findall(r"""ref\s*\(\s*['"]([^'"]+)['"]\s*\)""", sql)))

def strip_jinja(sql):
    sql = re.sub(r'\{%.*?%\}', '', sql, flags=re.DOTALL)
    sql = re.sub(r'\{\{.*?\}\}', '', sql, flags=re.DOTALL)
    return sql

def resolve_refs(sql):
    """Replace {{ ref('name') }} with just 'name' so SQL parsing works."""
    sql = re.sub(r"\{\{\s*ref\s*\(\s*'([^']+)'\s*\)\s*\}\}", r'\1', sql)
    return sql

def extract_alias_map(sql_clean, upstreams):
    """
    Extract table alias mapping from FROM/JOIN clauses.
    E.g., "FROM t2_master_hubops srs" → {'srs': 't2_master_hubops'}
    Also handles upstream names as direct aliases.
    Returns dict: alias → upstream_name
    """
    alias_map = {}
    # Direct: upstream name itself can be used as alias
    for up in upstreams:
        alias_map[up.lower()] = up

    # FROM aliases: "FROM upstream_table alias" or "FROM upstream_table AS alias"
    from_matches = re.findall(
        r'\bFROM\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?',
        sql_clean, re.IGNORECASE
    )
    join_matches = re.findall(
        r'\bJOIN\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?',
        sql_clean, re.IGNORECASE
    )

    for table, alias in from_matches + join_matches:
        table_lower = table.lower()
        if alias:
            alias_lower = alias.lower()
            # If the table name matches an upstream, record the alias mapping
            for up in upstreams:
                if table_lower == up.lower():
                    alias_map[alias_lower] = up
                    break
                # Also try matching by prefix (t2_master → t2_master_hubops)
                if up.lower().startswith(table_lower):
                    alias_map[alias_lower] = up
                    break

    return alias_map


def extract_select_columns(sql, upstreams):
    """
    For a model with a simple SELECT (no CTEs), parse SELECT expressions
    and try to map columns to upstream tables+columns.
    
    Returns list of dicts: {name, description, source_table, source_column}
    """
    sql_clean = resolve_refs(sql)
    sql_clean = strip_jinja(sql_clean)
    sql_clean = re.sub(r"--.*?\n", "\n", sql_clean)
    sql_clean = re.sub(r"'[^']*'", "''", sql_clean)

    columns = []
    
    # Extract table alias mapping (FROM alias → upstream name)
    alias_map = extract_alias_map(sql_clean, upstreams)

    # Find the final SELECT clause
    has_cte = bool(re.search(r'\bWITH\b\s+', sql_clean, re.IGNORECASE))
    
    if has_cte:
        # Remove CTE definitions, keep the final SELECT
        without_ctes = re.sub(
            r'\bWITH\b\s+(\w+\s+AS\s*\(.*?\)\s*,?\s*)+',
            '',
            sql_clean,
            flags=re.IGNORECASE | re.DOTALL
        )
    else:
        without_ctes = sql_clean

    # Now parse the SELECT clause
    select_match = re.search(
        r'\bSELECT\b\s+(.*?)\bFROM\b',
        without_ctes,
        re.IGNORECASE | re.DOTALL
    )
    if not select_match:
        return columns

    select_clause = select_match.group(1).strip()

    # Split by top-level commas (not inside parens)
    parts = split_top_level_commas(select_clause)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        col_info = parse_select_expr(part, upstreams, alias_map)
        if col_info:
            columns.append(col_info)

    return columns


def split_top_level_commas(text):
    """Split text by commas that are not inside parentheses."""
    parts = []
    depth = 0
    current = []
    for ch in text:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)
    parts.append(''.join(current))
    return parts


def parse_select_expr(expr, upstreams, alias_map=None):
    """
    Parse a single SELECT expression like:
      - "col_name"                           → {name: col_name}
      - "t.alias_col AS col_name"           → {name: col_name, source: alias}
      - "COUNT(DISTINCT i.awb) AS total"    → aggregate, no source
      - "DATE(o.operation_time) AS date"    → {name: date, source: o.operation_time}
      - "UPPER(ppm.zone) AS zone"           → {name: zone, source: ppm.zone}
    """
    alias_map = alias_map or {}

    # Handle "expr AS alias" pattern
    as_match = re.search(r'\bAS\s+(\w+)', expr, re.IGNORECASE)
    if as_match:
        alias = as_match.group(1)
        source_expr = expr[:as_match.start()].strip()
    else:
        # No AS clause — use the last word as column name
        words = expr.strip().split()
        alias = words[-1].strip('"`[]') if words else expr.strip()
        source_expr = expr

    # Clean up the alias
    alias = alias.strip('"`[]').strip(',')

    # Try to extract source table.column from the expression
    source_table = None
    source_column = None

    simplified = source_expr
    for func in ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COALESCE', 'DATE', 'UPPER', 'LOWER', 'TRIM']:
        simplified = re.sub(rf'\b{func}\s*\(', '', simplified, flags=re.IGNORECASE)
    simplified = simplified.replace('(', ' ').replace(')', ' ')
    for kw in ['DISTINCT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AND', 'OR', 'NOT', 'IS', 'NULL']:
        simplified = re.sub(rf'\b{kw}\b', ' ', simplified, flags=re.IGNORECASE)
    simplified = re.sub(r"''", '', simplified)
    simplified = re.sub(r"'[^']*'", '', simplified)

    # Find "alias.column" patterns
    refs = re.findall(r'(?<![A-Za-z_])([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)', simplified)

    if refs:
        alias_name, col_name = refs[-1]
        alias_lower = alias_name.lower()
        
        # Check alias_map first (FROM alias → upstream name)
        if alias_lower in alias_map:
            source_table = alias_map[alias_lower]
            source_column = col_name
        else:
            # Direct match against upstream names
            for up in upstreams:
                if alias_lower == up.lower():
                    source_table = up
                    source_column = col_name
                    break

    if not source_table and upstreams:
        # Fallback: bare column names (no alias. prefix).
        # Extract all word tokens that aren't SQL keywords.
        SQL_KW = {'COUNT','SUM','AVG','MIN','MAX','COALESCE','DATE','UPPER','LOWER',
                  'TRIM','DISTINCT','CASE','WHEN','THEN','ELSE','END','AND','OR','NOT',
                  'IS','NULL','AS','IN','BY','ON','DESC','ASC','TRUE','FALSE','SELECT',
                  'FROM','WHERE','GROUP','ORDER','HAVING','LIMIT','OFFSET','BETWEEN',
                  'LIKE','EXISTS','ALL','ANY'}
        tokens = re.findall(r'[a-zA-Z_]\w*', simplified)
        bare = [t for t in tokens if t.upper() not in SQL_KW and not re.match(r'^\d',t)]
        # Remove tokens that are clearly operators or noise
        col_candidate = bare[-1] if bare else None
        if col_candidate:
            source_table = upstreams[0]
            source_column = col_candidate

    return {
        "name": alias,
        "expression": source_expr.strip(),
        "source_table": source_table or "",
        "source_column": source_column or "",
        "description": "",
    }


def generate_column_lineage(columns, upstreams):
    """
    Build column_lineage entries per upstream table from column source info.
    Returns dict: upstream_name → [{column, from_column, expression}]
    """
    lineage_map = {}
    for col in columns:
        src_t = col.get("source_table", "")
        src_c = col.get("source_column", "")
        name = col.get("name", "")
        expr = col.get("expression", "")
        if src_t and src_c:
            if src_t not in lineage_map:
                lineage_map[src_t] = []
            lineage_map[src_t].append({
                "column": name,
                "from_column": src_c,
                "expression": expr,
            })
    return lineage_map


def load_manifest(dbt_root):
    with open(Path(dbt_root) / "target" / "manifest.json") as f:
        return json.load(f)


def extract_model_description(manifest, model_name):
    """Extract model-level description from dbt manifest.json."""
    prefix = f"model.{manifest.get('metadata', {}).get('project_name', 'smile_dbt_model')}."
    node = manifest.get("nodes", {}).get(f"{prefix}{model_name}", {})
    if not node:
        # Try alternate: model.{project_name}.{model_name} with the name from the YAML dir
        for key, n in manifest.get("nodes", {}).items():
            if n.get("name") == model_name and n.get("resource_type") == "model":
                node = n
                break
    return (node.get("description") or "") if node else ""


def extract_column_descriptions(manifest, model_name):
    """Extract column-level descriptions from dbt manifest.json.
    Returns dict: column_name → description
    """
    prefix = f"model.{manifest.get('metadata', {}).get('project_name', 'smile_dbt_model')}."
    node = manifest.get("nodes", {}).get(f"{prefix}{model_name}", {})
    if not node:
        for key, n in manifest.get("nodes", {}).items():
            if n.get("name") == model_name and n.get("resource_type") == "model":
                node = n
                break
    if not node:
        return {}
    cols = node.get("columns", {})
    return {name: info.get("description", "") for name, info in cols.items()}


def generate_model_yaml(model_name, columns, upstreams, dbt_root=None, model_description="", col_descriptions=None):
    """Generate a complete YAML data structure for a model."""
    dbt_root = dbt_root or DEFAULT_DBT_ROOT
    col_descriptions = col_descriptions or {}
    # Build upstreams with column_lineage
    lineage_by_upstream = generate_column_lineage(columns, upstreams)

    upstream_entries = []
    for up_name in upstreams:
        entry = {
            "name": up_name,
            "schema": "silver_layer",
        }
        cl = lineage_by_upstream.get(up_name, [])
        if cl:
            entry["column_lineage"] = []
            for c in cl:
                entry["column_lineage"].append({
                    "column": c["column"],
                    "from_column": c["from_column"],
                })
        upstream_entries.append(entry)

    # Build columns list with descriptions from manifest
    col_entries = []
    for c in columns:
        desc = col_descriptions.get(c["name"]) or c.get("description") or ""
        entry = {"name": c["name"], "expression": c["expression"], "description": desc}
        if c.get("source_table") and c.get("source_column"):
            entry["source_table"] = c["source_table"]
            entry["source_column"] = c["source_column"]
        col_entries.append(entry)

    data = {
        "model": {
            "name": model_name,
            "schema": "silver_layer",
            "materialized": "table",
            "file_path": f"models/{find_model_folder(model_name, dbt_root)}/{model_name}.sql",
            "description": model_description,
            "columns": col_entries,
            "upstreams": upstream_entries,
        }
    }
    return data


def find_model_folder(model_name, dbt_root):
    """Find the subfolder (relative to models/) where the model's SQL lives."""
    for root, dirs, files in os.walk(Path(dbt_root) / "models"):
        for f in files:
            if f == f"{model_name}.sql":
                rel = Path(root).relative_to(Path(dbt_root) / "models")
                return str(rel)
    return "unknown"


def add_to_tables_yaml(table_name):
    """Add a table to config/tables.yaml if not already present."""
    with open(TABLES_YAML) as f:
        data = yaml.safe_load(f) or {"tables": []}

    tables = data.get("tables", [])
    # Extract bare names (strip silver_layer. prefix if present)
    existing = set()
    for t in tables:
        name = str(t).split(".")[-1] if "." in str(t) else str(t)
        existing.add(name)

    if table_name not in existing:
        tables.append(f"silver_layer.{table_name}")
        data["tables"] = tables
        with open(TABLES_YAML, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return True
    return False


def remove_from_tables_yaml(table_name):
    """Remove a table from config/tables.yaml."""
    with open(TABLES_YAML) as f:
        data = yaml.safe_load(f) or {"tables": []}

    tables = data.get("tables", [])
    new_tables = []
    removed = False
    for t in tables:
        name = str(t).split(".")[-1] if "." in str(t) else str(t)
        if name == table_name:
            removed = True
        else:
            new_tables.append(t)

    if removed:
        data["tables"] = new_tables
        with open(TABLES_YAML, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return removed


def find_orphan_upstreams(removed_model):
    """
    Find upstream tables that were only used by the removed model.
    Returns list of table names that are now orphaned.
    """
    # Get all YAML files
    yaml_files = sorted([
        f for f in os.listdir(YAML_DIR)
        if f.endswith(".yml") and not f.startswith("_")
    ])

    # Collect ALL upstream references from ALL models (except the removed one)
    all_upstreams = set()
    for fname in yaml_files:
        model_name = fname.replace(".yml", "")
        if model_name == removed_model:
            continue
        with open(YAML_DIR / fname) as f:
            data = yaml.safe_load(f)
        for up in data.get("model", {}).get("upstreams", []):
            all_upstreams.add(up.get("name", ""))

    # Find upstreams that belonged to the removed model
    removed_yml = YAML_DIR / f"{removed_model}.yml"
    if not removed_yml.exists():
        return []

    with open(removed_yml) as f:
        data = yaml.safe_load(f)

    orphaned = []
    for up in data.get("model", {}).get("upstreams", []):
        up_name = up.get("name", "")
        if up_name not in all_upstreams:
            orphaned.append(up_name)

    return orphaned


# ── Commands ──────────────────────────────────────────────────────────

def cmd_add(args):
    """Add a new model: scan SQL → generate YAML → update tables.yaml."""
    model_name = args.model
    dry_run = args.dry_run
    dbt_root = args.dbt_path

    print(f"\n{'='*60}")
    print(f"ADD MODEL: {model_name}")
    print(f"{'='*60}")

    # 1. Find SQL file
    sql_path = find_sql_file(model_name, dbt_root)
    if not sql_path:
        print(f"  ✗ SQL file not found for model '{model_name}'")
        sys.exit(1)
    print(f"  ✓ Found SQL: {sql_path}")

    # 2. Check if YAML already exists
    yaml_path = YAML_DIR / f"{model_name}.yml"
    if yaml_path.exists() and not args.force:
        print(f"  ✗ YAML already exists: {yaml_path}")
        print(f"    Use --force to overwrite")
        sys.exit(1)

    with open(sql_path) as f:
        sql = f.read()

    # 3. Extract upstream refs
    upstreams = extract_refs(sql)
    upstreams = [u for u in upstreams if u != model_name]  # self-refs
    print(f"  ✓ Upstream tables ({len(upstreams)}): {', '.join(upstreams) if upstreams else '(none)'}")

    # 4. Extract columns with lineage
    columns = extract_select_columns(sql, upstreams)
    if not columns:
        print(f"  ⚠ Could not parse SELECT columns from SQL")
        print(f"    YAML will be created without column entries.")
    else:
        mapped = sum(1 for c in columns if c.get("source_table"))
        print(f"  ✓ Columns ({len(columns)} total, {mapped} with source mapping)")

    # 5. Extract descriptions from dbt manifest.json
    model_description = ""
    col_descriptions = {}
    manifest_path = Path(dbt_root) / "target" / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = load_manifest(dbt_root)
            model_description = extract_model_description(manifest, model_name)
            col_descriptions = extract_column_descriptions(manifest, model_name)
            if model_description:
                print(f"  ✓ Model description: {model_description[:80]}...")
            if col_descriptions:
                filled = sum(1 for c in columns if col_descriptions.get(c["name"]))
                print(f"  ✓ Column descriptions: {filled}/{len(columns)} columns have descriptions from manifest")
        except Exception as e:
            print(f"  - Could not read manifest.json: {e}")

    data = generate_model_yaml(model_name, columns, upstreams, dbt_root,
                                model_description=model_description,
                                col_descriptions=col_descriptions)

    if dry_run:
        print(f"\n  ── Preview ──────────────────────────────────")
        print(yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120))
        print(f"  ──────────────────────────────────────────────")
        print(f"  (dry-run — no files written)")
        return

    # 5. Write YAML
    with open(yaml_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120)
    print(f"  ✓ YAML written: {yaml_path}")

    # 7. Add to tables.yaml
    added_model = add_to_tables_yaml(model_name)
    if added_model:
        print(f"  ✓ Added '{model_name}' to config/tables.yaml")
    else:
        print(f"  - '{model_name}' already in config/tables.yaml")

    # 8. Add upstreams to tables.yaml
    added_count = 0
    for up in upstreams:
        if add_to_tables_yaml(up):
            added_count += 1
    if added_count:
        print(f"  ✓ Added {added_count} new upstream table(s) to config/tables.yaml")

    print(f"\n  ✅ Model '{model_name}' added successfully!")
    print(f"  Next steps:")
    print(f"    1. Push to Neo4j:    make push-lineage")
    print(f"    2. Generate SQL:     make generate-joins")
    print(f"    3. Verify:           make verify")


def cmd_remove(args):
    """Remove a model: check for orphans, remove YAML, update tables.yaml."""
    model_name = args.model
    dry_run = args.dry_run

    print(f"\n{'='*60}")
    print(f"REMOVE MODEL: {model_name}")
    print(f"{'='*60}")

    yaml_path = YAML_DIR / f"{model_name}.yml"
    if not yaml_path.exists():
        print(f"  ✗ YAML not found: {yaml_path}")
        print(f"    Nothing to remove.")
        sys.exit(1)

    # 1. Find orphan upstreams
    orphaned = find_orphan_upstreams(model_name)

    if orphaned:
        print(f"  ⚠ {len(orphaned)} upstream table(s) will become ORPHANED:")
        for up in orphaned:
            print(f"    - {up}")
    else:
        print(f"  ✓ No orphaned upstreams — all upstream tables are")
        print(f"    still used by other models.")

    if dry_run:
        print(f"\n  (dry-run — no files deleted)")
        print(f"  Would remove '{model_name}' from config/tables.yaml")
        if orphaned:
            print(f"  Would remove orphaned upstreams from tables.yaml: {', '.join(orphaned)}")
        return

    # 2. Remove YAML
    os.remove(yaml_path)
    print(f"  ✓ Removed YAML: {yaml_path}")

    # 3. Remove model's own entry from tables.yaml
    if remove_from_tables_yaml(model_name):
        print(f"  ✓ Removed '{model_name}' from config/tables.yaml")

    # 4. Optionally remove orphaned upstreams from tables.yaml
    removed_from_config = 0
    for up in orphaned:
        if remove_from_tables_yaml(up):
            removed_from_config += 1
            print(f"  ✓ Removed orphaned '{up}' from config/tables.yaml")

    if orphaned and removed_from_config == 0:
        print(f"  - Orphaned tables not in config/tables.yaml (already clean)")

    print(f"\n  ✅ Model '{model_name}' removed successfully!")
    print(f"  Next steps:")
    print(f"    1. Push to Neo4j:       make push-lineage")
    print(f"    2. Regenerate SQL:      make generate-joins")


def cmd_list(args):
    """List all models and their upstream tables."""
    yaml_files = sorted([
        f for f in os.listdir(YAML_DIR)
        if f.endswith(".yml") and not f.startswith("_")
    ])

    print(f"\n{'='*60}")
    print(f"ALL MODELS IN LINEAGE ({len(yaml_files)} total)")
    print(f"{'='*60}")

    all_upstreams = set()
    for fname in yaml_files:
        model_name = fname.replace(".yml", "")
        with open(YAML_DIR / fname) as f:
            data = yaml.safe_load(f)
        ups = []
        for up in data.get("model", {}).get("upstreams", []):
            up_name = up.get("name", "")
            ups.append(up_name)
            all_upstreams.add(up_name)
        cols = len(data.get("model", {}).get("columns", []))
        mapped = sum(len(u.get("column_lineage", [])) for u in data.get("model", {}).get("upstreams", []))
        print(f"  {model_name:50s} {len(ups)} upstreams, {cols} cols, {mapped} mappings")

    # Find upstreams that are ALSO models (inter-model dependencies)
    model_names = {f.replace(".yml", "") for f in yaml_files}
    inter_model = all_upstreams & model_names
    if inter_model:
        print(f"\n  Inter-model dependencies (model→model):")
        for m in sorted(inter_model):
            print(f"    {m}")

    print(f"\n  Total models: {len(yaml_files)}")
    print(f"  Total unique upstreams: {len(all_upstreams)}")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Manage dbt models in the Neo4j lineage pipeline."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="Add a new model to the lineage")
    p_add.add_argument("--model", "-m", required=True, help="Model name (from dbt project)")
    p_add.add_argument("--dry-run", "-n", action="store_true", help="Preview only, don't write")
    p_add.add_argument("--force", "-f", action="store_true", help="Overwrite existing YAML")
    p_add.add_argument("--dbt-path", "-d", default=DEFAULT_DBT_ROOT,
                       help=f"Path to dbt project root (default: {DEFAULT_DBT_ROOT})")

    # remove
    p_rm = sub.add_parser("remove", help="Remove a model from the lineage")
    p_rm.add_argument("--model", "-m", required=True, help="Model name to remove")
    p_rm.add_argument("--dry-run", "-n", action="store_true", help="Preview only, don't delete")

    # list
    p_list = sub.add_parser("list", help="List all models in the lineage")

    args = parser.parse_args()

    if args.command == "add":
        cmd_add(args)
    elif args.command == "remove":
        cmd_remove(args)
    elif args.command == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
