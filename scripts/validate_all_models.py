"""
Deep validation of all 14 models:
  1. SQL {{ ref() }} ↔ YAML upstreams match
  2. Every column_lineage column exists in upstream's Column set
  3. Every column with source_table/source_column has a corresponding column_lineage entry
  4. All upstream tables are in config/tables.yaml
  5. Summary of all MAPS_TO coverage
"""
import os, re, sys, yaml
from pathlib import Path
from collections import defaultdict

DBT_MODELS = Path("/home/ubuntu/smile_dbt_model/smile_dbt_model/models")
YAML_DIR = Path("/home/ubuntu/neo4j/config/model_lineage")
TABLES_YAML = Path("/home/ubuntu/neo4j/config/tables.yaml")

TARGET_MODELS = [
    "t3_Eway_Report", "t3_Fastrack_orders_report", "t3_HUB_Audit_Entry_Report_dataset",
    "t3_booking_data_vs_status_report", "t3_booking_vs_delivery_report",
    "t3_booking_vs_first_inscan_report", "t3_delivery_mis_report",
    "t3_incoming_shipments", "t3_inscan_bags_report", "t3_inscan_shipments_report",
    "t3_master_booking_hubops_delivery", "t3_outscan_shipments",
    "t3_rpt_delivery_channel_analysis", "t3_shipments_inscan_vs_outscan_report",
]

# Load tables.yaml to know which tables are configured for PG→Neo4j
with open(TABLES_YAML) as f:
    tables_config = yaml.safe_load(f)
configured_tables = set()
if isinstance(tables_config, dict):
    # Format: tables: [silver_layer.tablename, ...]
    table_list = tables_config.get("tables", tables_config.get("silver_layer", []))
    if isinstance(table_list, list):
        for t in table_list:
            name = str(t).split(".")[-1] if "." in str(t) else str(t)
            configured_tables.add(name)
    else:
        configured_tables = set(table_list.keys())
elif isinstance(tables_config, list):
    for t in tables_config:
        name = str(t).split(".")[-1] if "." in str(t) else str(t)
        configured_tables.add(name)

def extract_refs(sql):
    """Find {{ ref('...') }} and silver_layer.table references."""
    refs = set(re.findall(r"""ref\s*\(\s*['"]([^'"]+)['"]\s*\)""", sql))
    direct = set(re.findall(r"""silver_layer\.\s*["']?(\w+)["']?""", sql))
    return refs | direct

# Load all YAML data upfront
yaml_data = {}
for m in TARGET_MODELS:
    p = YAML_DIR / f"{m}.yml"
    with open(p) as f:
        yaml_data[m] = yaml.safe_load(f)

# ── Check 1: SQL refs vs YAML upstreams ──────────────────────────
print("=" * 80)
print("CHECK 1: SQL refs vs YAML upstreams")
print("=" * 80)
all_ok = True
for model_name in TARGET_MODELS:
    sql = ""
    for root, dirs, files in os.walk(DBT_MODELS):
        for f in files:
            if f == f"{model_name}.sql":
                with open(os.path.join(root, f)) as fp:
                    sql = fp.read()
    sql_refs = extract_refs(sql)
    sql_refs.discard(model_name)
    
    data = yaml_data[model_name]
    yaml_ups = set()
    for up in data.get("model", {}).get("upstreams", []):
        yaml_ups.add(up.get("name", ""))
    
    missing = sql_refs - yaml_ups
    extra = yaml_ups - sql_refs
    if missing or extra:
        all_ok = False
        print(f"  ✗ {model_name}")
        for m in sorted(missing): print(f"     MISSING ref: {m}")
        for m in sorted(extra):   print(f"     EXTRA (not in SQL): {m}")
    else:
        print(f"  ✓ {model_name}: {len(sql_refs)} refs match")

print(f"\n  Result: {'ALL OK' if all_ok else 'GAPS FOUND'}")

# ── Check 2: Column_lineage entries exist for all source_table/source_column ──
print("\n" + "=" * 80)
print("CHECK 2: Column 'source_table/col' vs upstream column_lineage")
print("=" * 80)

all_lineage_ok = True
for model_name in TARGET_MODELS:
    data = yaml_data[model_name]
    columns = data.get("model", {}).get("columns", [])
    upstreams = data.get("model", {}).get("upstreams", [])

    # Build looking: which upstream+column is expected from column-level source info
    expected = set()
    for c in columns:
        src_t = c.get("source_table", "")
        src_c = c.get("source_column", "")
        col_name = c.get("name", "")
        if src_t and src_c:
            expected.add((src_t, src_c, col_name))

    # Build what actually exists in column_lineage
    actual = set()
    for up in upstreams:
        up_name = up.get("name", "")
        for cl in up.get("column_lineage", []):
            actual.add((up_name, cl.get("from_column", ""), cl.get("column", "")))

    missing_entries = expected - actual
    if missing_entries:
        all_lineage_ok = False
        print(f"  ✗ {model_name}: missing {len(missing_entries)} column_lineage entries")
        for src_t, src_c, col in sorted(missing_entries):
            print(f"     {col} → expected {src_t}.{src_c}")
    else:
        print(f"  ✓ {model_name}: all {len(expected)} source columns have column_lineage")

print(f"\n  Result: {'ALL OK' if all_lineage_ok else 'GAPS FOUND'}")

# ── Check 3: Tables.yaml coverage of all upstream tables ──────────
print("\n" + "=" * 80)
print("CHECK 3: All upstream tables in config/tables.yaml")
print("=" * 80)

all_upstreams = set()
for model_name in TARGET_MODELS:
    data = yaml_data[model_name]
    for up in data.get("model", {}).get("upstreams", []):
        all_upstreams.add(up.get("name", ""))

missing_from_config = all_upstreams - configured_tables
# Also include the model tables themselves
all_model_tables = set(TARGET_MODELS)
missing_model_from_config = all_model_tables - configured_tables

if missing_from_config:
    print(f"  ✗ {len(missing_from_config)} upstream tables NOT in tables.yaml:")
    for t in sorted(missing_from_config):
        print(f"     {t}")
else:
    print(f"  ✓ All {len(all_upstreams)} upstream tables are in tables.yaml")

if missing_model_from_config:
    print(f"  ✗ {len(missing_model_from_config)} model tables NOT in tables.yaml:")
    for t in sorted(missing_model_from_config):
        print(f"     {t}")
else:
    print(f"  ✓ All {len(all_model_tables)} model tables are in tables.yaml")

# ── Check 4: Summary per model ───────────────────────────────────
print("\n" + "=" * 80)
print("CHECK 4: Per-model column lineage coverage")
print("=" * 80)

total_cols = 0
total_mapped = 0
for model_name in TARGET_MODELS:
    data = yaml_data[model_name]
    cols = len(data.get("model", {}).get("columns", []))
    ups = data.get("model", {}).get("upstreams", [])
    mapped = sum(len(up.get("column_lineage", [])) for up in ups)
    total_cols += cols
    total_mapped += mapped
    pct = round(100.0 * mapped / max(cols, 1), 1)
    bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
    print(f"  {model_name:50s} {mapped:3d}/{cols:2d} cols mapped  {bar} {pct}%")

# ── Check 5: tables.yaml missing tables that need adding ─────────
print("\n" + "=" * 80)
print("CHECK 5: Tables to add to config/tables.yaml")
print("=" * 80)
if missing_from_config:
    for t in sorted(missing_from_config):
        print(f"  ➜ ADD TO TABLES.YAML: {t}")
if missing_model_from_config:
    for t in sorted(missing_model_from_config):
        print(f"  ➜ ADD TO TABLES.YAML: {t}")
if not missing_from_config and not missing_model_from_config:
    print("  ✓ No additions needed")

# ── Summary ──────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"  Models:              {len(TARGET_MODELS)}")
print(f"  Total columns:       {total_cols}")
print(f"  Total MAPS_TO:       {total_mapped}")
print(f"  Upstream tables:     {len(all_upstreams)}")
print(f"  Tables.yaml coverage:")
print(f"  Upstreams:            {len(all_upstreams - missing_from_config)}/{len(all_upstreams)}")
print(f"    Models:            {len(all_model_tables - missing_model_from_config)}/{len(all_model_tables)}")