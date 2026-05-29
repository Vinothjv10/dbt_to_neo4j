"""
Fix stale source_table/source_column in t3_shipments_inscan_vs_outscan_report.yml
to match the correct column_lineage entries.
"""
import yaml
from pathlib import Path

path = Path("/home/ubuntu/neo4j/config/model_lineage/t3_shipments_inscan_vs_outscan_report.yml")
with open(path) as f:
    data = yaml.safe_load(f)

# Correct source_table/source_column based on SQL analysis (matching column_lineage)
fixed = {
    "date":                        ("t2_master_hubops", "operation_time"),
    "hub_id":                      ("t2_master_hubops", "premise_id"),
    "hub":                         ("t1_prs_premise_master_hubops", "premise_name"),
    "zone":                        ("t1_prs_premise_master_hubops", "zone"),
    "state":                       ("t1_prs_premise_master_hubops", "state"),
    "total_inscan_shipments":      ("t2_master_hubops", "awb_number"),
    "total_inscan_shipments_weight": ("t1_ss_shipment_dimentions_hubops_6M", "weight"),
    "total_outscan_shipments":     ("t2_master_hubops", "awb_number"),
    "pending_shipments":           ("t2_master_hubops", "awb_number"),
}

for col in data["model"]["columns"]:
    name = col["name"]
    if name in fixed:
        col["source_table"], col["source_column"] = fixed[name]

with open(path, "w") as f:
    yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120)

print(f"Fixed {len(fixed)} column entries in {path.name}")