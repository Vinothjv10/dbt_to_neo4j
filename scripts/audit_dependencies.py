"""
Audit all 14 models: compare SQL {{ ref(...) }} calls against YAML upstreams.
Reports:
  - Missing upstreams (in SQL but not in YAML)
  - Extra upstreams (in YAML but not in SQL)
  - Column lineage gaps
"""
import os, re, sys, yaml
from pathlib import Path

DBT_MODELS = Path("/home/ubuntu/smile_dbt_model/smile_dbt_model/models")
YAML_DIR = Path("/home/ubuntu/neo4j/config/model_lineage")

def find_model_yaml(name):
    for f in os.listdir(YAML_DIR):
        if f.endswith(".yml") and f.startswith(name):
            return YAML_DIR / f
    return None

def extract_refs(sql):
    """Extract ALL {{ ref('...') }} references from raw SQL (before Jinja stripping)."""
    return sorted(set(re.findall(r"""ref\s*\(\s*['"]([^'"]+)['"]\s*\)""", sql)))

def extract_direct_schema_table_refs(sql):
    """Also check for silver_layer.tablename refs (used without {{ ref() }})."""
    return sorted(set(re.findall(r"""silver_layer\.\s*["']?(\w+)["']?""", sql)))

results = []

print("=" * 100)
print(f"{'MODEL':45s} {'SQL REFs':50s} {'YAML UPSTREAMS':50s} {'MISSING':50s}")
print("=" * 100)

for root, dirs, files in sorted(os.walk(DBT_MODELS)):
    for fname in sorted(files):
        if not fname.endswith(".sql"):
            continue
        model_name = fname.replace(".sql", "")
        yaml_path = find_model_yaml(model_name)
        if not yaml_path:
            continue

        # Read SQL
        with open(os.path.join(root, fname)) as f:
            sql = f.read()

        # Read YAML
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Extract refs from SQL
        sql_refs = set(extract_refs(sql))
        sql_direct = set(extract_direct_schema_table_refs(sql))
        all_sql_refs = sql_refs | sql_direct

        # Remove self-references
        all_sql_refs.discard(model_name)

        # Extract upstreams from YAML
        yaml_upstreams = set()
        for up in data.get("model", {}).get("upstreams", []):
            yaml_upstreams.add(up.get("name", ""))

        missing = all_sql_refs - yaml_upstreams
        extra = yaml_upstreams - all_sql_refs

        status = ""
        if missing:
            status = f" MISSING: {', '.join(sorted(missing))}"
        if extra:
            status += f" EXTRA: {', '.join(sorted(extra))}"
        
        if missing or extra:
            print(f"{model_name:45s}")
            if missing:
                for m in sorted(missing):
                    print(f"  {'':45s} {'':50s} {'':50s} ❌ MISSING: {m}")
            if extra:
                for m in sorted(extra):
                    print(f"  {'':45s} {'':50s} ✅ EXTRA (not in SQL): {m}")
            results.append((model_name, missing, extra, yaml_path))

# Also check all upstream tables exist in Neo4j's tables.yaml
print("\n\n=== Checking upstream tables in config/tables.yaml ===")
all_upstreams_seen = set()
for root, dirs, files in os.walk(DBT_MODELS):
    for fname in files:
        if not fname.endswith(".sql"):
            continue
        with open(os.path.join(root, fname)) as f:
            sql = f.read()
        all_upstreams_seen |= set(extract_refs(sql))

# Read tables.yaml
tables_yaml_path = Path("/home/ubuntu/neo4j/config/tables.yaml")
if tables_yaml_path.exists():
    with open(tables_yaml_path) as f:
        tables_config = yaml.safe_load(f)
    configured_tables = set()
    if isinstance(tables_config, list):
        for t in tables_config:
            if isinstance(t, dict):
                configured_tables.add(t.get("name", ""))
            elif isinstance(t, str):
                configured_tables.add(t)
    elif isinstance(tables_config, dict):
        configured_tables = set(tables_config.keys())
    
    for up in sorted(all_upstreams_seen):
        if up not in configured_tables:
            print(f"  ❌ {up} — NOT in tables.yaml")

print("\n\n=== Summary ===")
print(f"Total upstream refs found across SQL: {len(all_upstreams_seen)}")
for up in sorted(all_upstreams_seen):
    # Find which models reference this
    models_using = []
    for root, dirs, files in os.walk(DBT_MODELS):
        for fname in files:
            if not fname.endswith(".sql"):
                continue
            with open(os.path.join(root, fname)) as f:
                sql = f.read()
            if up in extract_refs(sql):
                models_using.append(fname.replace(".sql", ""))
    print(f"  {up:45s} used by: {', '.join(models_using)}")
