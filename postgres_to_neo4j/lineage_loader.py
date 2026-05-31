"""
Load dbt lineage YAML files into Neo4j.

Reads all model YAML files from config/model_lineage/ and creates:
  - Schema, Table, Column nodes with properties
  - HAS_TABLE, HAS_COLUMN relationships
  - DEPENDS_ON (table-level lineage) relationships  
  - MAPS_TO (column-level lineage) relationships
"""

import json
import os
import sys
from pathlib import Path
from collections import OrderedDict

import yaml

try:
    from dotenv import load_dotenv
    from neo4j import GraphDatabase
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install: pip install neo4j python-dotenv pyyaml")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
YAML_DIR = PROJECT_ROOT / "config" / "model_lineage"

# ── Cypher statements ─────────────────────────────────────────────────────────

CYPHER_CLEAN = "MATCH (n) DETACH DELETE n"

CYPHER_MERGE_SCHEMA = """
    MERGE (s:Schema {name: $name})
    RETURN s
"""

CYPHER_MERGE_TABLE = """
    MERGE (t:Table {name: $table_name, schema: $schema_name})
    SET t.type = $table_type,
        t.description = $description
    WITH t
    MATCH (s:Schema {name: $schema_name})
    MERGE (s)-[:HAS_TABLE]->(t)
    RETURN t
"""

CYPHER_MERGE_COLUMN = """
    MERGE (c:Column {name: $col_name, table: $table_name, schema: $schema_name})
    SET c.data_type = $data_type,
        c.ordinal_position = $ordinal_position,
        c.description = $description
    WITH c
    MATCH (t:Table {name: $table_name, schema: $schema_name})
    MERGE (t)-[:HAS_COLUMN]->(c)
    RETURN c
"""

CYPHER_DEPENDS_ON = """
    MATCH (src:Table {schema: $src_schema, name: $src_table})
    MATCH (tgt:Table {schema: $tgt_schema, name: $tgt_table})
    MERGE (src)-[r:DEPENDS_ON]->(tgt)
    SET r.source = $source
    RETURN r
"""

CYPHER_MAPS_TO = """
    MATCH (src:Column {schema: $schema, table: $src_table, name: $src_col})
    MATCH (tgt:Column {schema: $schema, table: $tgt_table, name: $tgt_col})
    MERGE (src)-[r:MAPS_TO]->(tgt)
    SET r.expression = $expression
    RETURN r
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_env():
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)

def connect_neo4j():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    return GraphDatabase.driver(uri, auth=(user, password))

def run_tx(tx, cypher, params=None):
    tx.run(cypher, parameters=params or {})

# ── Loader ────────────────────────────────────────────────────────────────────

class LineageLoader:
    def __init__(self, driver, dry_run=False):
        self.driver = driver
        self.dry_run = dry_run

    def log(self, msg):
        prefix = "[DRY-RUN] " if self.dry_run else ""
        print(f"  {prefix}{msg}")

    def exec(self, cypher, params=None):
        if self.dry_run:
            self.log(f"{cypher[:100]}… params={json.dumps(params)[:120]}")
            return
        with self.driver.session() as session:
            session.execute_write(run_tx, cypher, params)

    def clean(self):
        if self.dry_run:
            self.log("CLEAN — would delete all nodes")
            return
        with self.driver.session() as session:
            session.execute_write(run_tx, CYPHER_CLEAN)

    def load_yaml(self, yaml_path: str) -> dict:
        with open(yaml_path) as f:
            return yaml.safe_load(f)

    def process_model(self, data: dict):
        model = data.get("model", {})
        name = model.get("name", "")
        schema = model.get("schema", "silver_layer")
        file_path = model.get("file_path", "")
        materialized = model.get("materialized", "table")
        description = model.get("description", "")

        if not name:
            return

        self.log(f"Processing model: {schema}.{name}")

        # 1. Schema node
        self.exec(CYPHER_MERGE_SCHEMA, {"name": schema})

        # 2. Table node
        self.exec(CYPHER_MERGE_TABLE, {
            "schema_name": schema,
            "table_name": name,
            "table_type": materialized,
            "description": description,
        })

        # 3. Column nodes
        columns = model.get("columns", [])
        for idx, col in enumerate(columns):
            col_name = col.get("name", "")
            data_type = col.get("data_type", "")
            source_table_val = col.get("source_table", "")
            source_column_val = col.get("source_column", "")
            description_val = col.get("description", "")
            self.exec(CYPHER_MERGE_COLUMN, {
                "schema_name": schema,
                "table_name": name,
                "col_name": col_name,
                "data_type": data_type,
                "ordinal_position": idx + 1,
                "description": description_val,
            })
            # Store lineage source info on the Column node
            if source_table_val and source_column_val:
                self.exec("""
                    MATCH (c:Column {schema: $schema, table: $table, name: $col})
                    SET c.source_table = $src_table, c.source_column = $src_col
                    RETURN c
                """, {
                    "schema": schema,
                    "table": name,
                    "col": col_name,
                    "src_table": source_table_val,
                    "src_col": source_column_val,
                })

        # 4. Upstream DEPENDS_ON relationships (table-level)
        upstreams = model.get("upstreams", [])
        for up in upstreams:
            up_name = up.get("name", "")
            up_schema = up.get("schema", "silver_layer")
            if not up_name:
                continue

            # Ensure upstream table node exists
            self.exec(CYPHER_MERGE_SCHEMA, {"name": up_schema})
            self.exec(CYPHER_MERGE_TABLE, {
                "schema_name": up_schema,
                "table_name": up_name,
                "table_type": "table",
                "description": "",
            })

            # DEPENDS_ON relationship
            self.exec(CYPHER_DEPENDS_ON, {
                "src_schema": schema,
                "src_table": name,
                "tgt_schema": up_schema,
                "tgt_table": up_name,
                "source": "dbt_lineage_yml",
            })

            # 5. Column-level MAPS_TO relationships
            # Build a lookup: model_col_name → description from the model's columns list
            col_desc_map = {c.get("name", ""): c.get("description", "") for c in columns}

            col_lineage = up.get("column_lineage", [])
            for cl in col_lineage:
                src_col = cl.get("column", "")
                tgt_col = cl.get("from_column", "")
                expr = cl.get("expression", "")

                if src_col and tgt_col:
                    # Find the model column's description to propagate to upstream
                    src_desc = col_desc_map.get(src_col, "")

                    # Ensure upstream Column node exists (MERGE, not MATCH),
                    # and set description if one was provided by the model column
                    self.exec("""
                        MERGE (tgt:Column {schema: $schema, table: $up_table, name: $tgt_col})
                        SET tgt.description = COALESCE(tgt.description, $description)
                        WITH tgt
                        MATCH (t:Table {schema: $schema, name: $up_table})
                        MERGE (t)-[:HAS_COLUMN]->(tgt)
                        RETURN tgt
                    """, {
                        "schema": schema,
                        "up_table": up_name,
                        "tgt_col": tgt_col,
                        "description": src_desc,
                    })
                    self.exec(CYPHER_MAPS_TO, {
                        "schema": schema,
                        "src_table": name,
                        "src_col": src_col,
                        "tgt_table": up_name,
                        "tgt_col": tgt_col,
                        "expression": expr,
                    })

    def load_all(self, yaml_dir: str):
        yaml_files = sorted([
            f for f in os.listdir(yaml_dir)
            if f.endswith(".yml") and not f.startswith("_")
        ])
        self.log(f"Found {len(yaml_files)} model YAML files in {yaml_dir}")
        for fname in yaml_files:
            fpath = os.path.join(yaml_dir, fname)
            data = self.load_yaml(fpath)
            self.process_model(data)

    def print_summary(self, yaml_dir: str):
        """Print what would be loaded without writing to Neo4j."""
        total_tables = 0
        total_cols = 0
        total_upstreams = 0
        total_col_lineage = 0

        yaml_files = sorted([
            f for f in os.listdir(yaml_dir)
            if f.endswith(".yml") and not f.startswith("_")
        ])

        for fname in yaml_files:
            fpath = os.path.join(yaml_dir, fname)
            data = self.load_yaml(fpath)
            m = data.get("model", {})
            cols = len(m.get("columns", []))
            ups = len(m.get("upstreams", []))
            cl = sum(len(u.get("column_lineage", [])) for u in m.get("upstreams", []))

            total_tables += 1
            total_cols += cols
            total_upstreams += ups
            total_col_lineage += cl

            print(f"  {m['name']:50s}  cols={cols:2d}  upstreams={ups:2d}  col_lineage={cl:2d}")

        print(f"\n  Total: {total_tables} tables, {total_cols} columns, "
              f"{total_upstreams} DEPENDS_ON, {total_col_lineage} MAPS_TO")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="push-lineage",
        description="Load dbt lineage YAML files into Neo4j.",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be loaded without writing to Neo4j")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Skip confirmation prompt")
    parser.add_argument("--yaml-dir", default=str(YAML_DIR),
                        help=f"Directory with YAML files (default: {YAML_DIR})")
    parser.add_argument("--summary", action="store_true",
                        help="Only print summary, don't connect to Neo4j")
    args = parser.parse_args()

    load_env()
    yaml_dir = args.yaml_dir

    if not os.path.isdir(yaml_dir):
        print(f"Error: YAML directory not found: {yaml_dir}", file=sys.stderr)
        sys.exit(1)

    loader = LineageLoader(driver=None, dry_run=True)

    print("Reading YAML lineage files...")
    print()

    if args.summary:
        loader.print_summary(yaml_dir)
        return

    # Connect to Neo4j
    print("Connecting to Neo4j...")
    driver = connect_neo4j()
    loader = LineageLoader(driver, dry_run=args.dry_run)

    try:
        if not args.dry_run and not args.yes:
            confirm = input("This will CLEAR the Neo4j database. Continue? (y/N): ")
            if confirm.lower() != "y":
                print("Aborted.")
                return

        if not args.dry_run:
            loader.clean()

        loader.load_all(yaml_dir)

        print("\nDone!")
        print(f"Loaded lineage from {yaml_dir}")

    finally:
        if not args.dry_run:
            driver.close()


if __name__ == "__main__":
    main()
