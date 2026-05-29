#!/usr/bin/env python3
"""
Generate SQL JOIN queries from Neo4j lineage graph.

Reads lineage from YAML files and generates SELECT + JOIN SQL
for each target model showing how upstream tables connect.
"""
import os, sys, yaml
from collections import OrderedDict

yml_dir = '/home/ubuntu/neo4j/config/model_lineage'


def load_model(name):
    path = os.path.join(yml_dir, f'{name}.yml')
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return yaml.safe_load(f)


def generate_join_sql(model_name):
    """Generate a SQL query showing how a model joins to its upstreams."""
    data = load_model(model_name)
    if not data:
        return f"-- Model '{model_name}' not found"

    m = data.get('model', {})
    name = m.get('name', model_name)
    schema = m.get('schema', 'silver_layer')
    columns = m.get('columns', [])
    upstreams = m.get('upstreams', [])

    sql_parts = [f"-- ═══════════════════════════════════════════════"]
    sql_parts.append(f"-- Model: {schema}.{name}")
    sql_parts.append(f"-- File: {m.get('file_path', '')}")
    sql_parts.append(f"-- Columns: {len(columns)} | Upstreams: {len(upstreams)}")
    sql_parts.append(f"-- ═══════════════════════════════════════════════")
    sql_parts.append("")

    # Collect all column-level JOIN keys from upstreams
    all_join_keys = []  # [(model_col, upstream_table, upstream_col)]
    for up in upstreams:
        up_name = up.get('name', '')
        up_schema = up.get('schema', schema)
        col_lineage = up.get('column_lineage', [])
        for cl in col_lineage:
            all_join_keys.append({
                'model_col': cl.get('column', ''),
                'up_table': up_name,
                'up_schema': up_schema,
                'up_col': cl.get('from_column', ''),
            })

    # If no column lineage, try to infer from shared column names
    has_lineage = bool(all_join_keys)

    # Build a lookup: model_col_name → (up_table, up_col) from column_lineage
    col_lineage_lookup = {}
    for up in upstreams:
        up_name = up.get('name', '')
        for cl in up.get('column_lineage', []):
            mc = cl.get('column', '')
            uc = cl.get('from_column', '')
            if mc:
                col_lineage_lookup[mc] = (up_name, uc)

    # Build SELECT clause
    sql_parts.append(f"SELECT")
    col_lines = []
    for i, col in enumerate(columns):
        col_name = col.get('name', '')
        is_manifest = col.get('source') == 'manifest_only'

        # Use column_lineage for comment if available (more accurate than source_column)
        comment = ""
        if col_name in col_lineage_lookup:
            src_tbl, src_col = col_lineage_lookup[col_name]
            comment = f"  -- {src_tbl}.{src_col}"
        elif is_manifest:
            comment = "  -- manifest_only"

        comma = "," if i < len(columns) - 1 else ""
        col_lines.append(f"  t.{col_name}{comma}{comment}")

    sql_parts.append("\n".join(col_lines))

    # Build FROM clause
    sql_parts.append(f"FROM {schema}.{name} t")

    # Build JOIN clauses with column-level keys
    if has_lineage:
        # Group join keys by upstream table
        from collections import defaultdict
        joins_by_table = defaultdict(list)
        for jk in all_join_keys:
            joins_by_table[(jk['up_schema'], jk['up_table'])].append(jk)

        for (up_schema, up_table), keys in joins_by_table.items():
            alias = up_table[:20]
            conditions = []
            for k in keys:
                conditions.append(f"    t.{k['model_col']} = {alias}.{k['up_col']}")

            sql_parts.append(f"LEFT JOIN {up_schema}.{up_table} {alias}")
            sql_parts.append(f"  ON")
            sql_parts.append(" AND\n".join(conditions))
    else:
        # No column-level keys — show upstreams as comments
        for up in upstreams:
            up_name = up.get('name', '')
            up_schema = up.get('schema', schema)
            sql_parts.append(f"-- JOIN {up_schema}.{up_name} up ON t.<key> = up.<key>  -- (key unknown)")

    # WHERE clause hint
    sql_parts.append("")
    sql_parts.append("-- WHERE 1=1")
    sql_parts.append("--   AND t.<column> = '<value>'")

    return "\n".join(sql_parts)


def generate_all_sqls():
    """Generate SQL for all models and write to a file."""
    model_files = sorted([
        f.replace('.yml', '') for f in os.listdir(yml_dir)
        if f.endswith('.yml') and not f.startswith('_')
    ])

    output_path = os.path.join(yml_dir, '_generated_joins.sql')
    lines = []
    lines.append("-- ═══════════════════════════════════════════════════════════════")
    lines.append("-- Auto-generated SQL JOIN queries from dbt lineage YAML")
    lines.append("-- Generated for silver_layer models with Neo4j lineage mapping")
    lines.append("-- ═══════════════════════════════════════════════════════════════")
    lines.append("")

    for model_name in model_files:
        sql = generate_join_sql(model_name)
        lines.append(sql)
        lines.append("")
        lines.append("")

    with open(output_path, 'w') as f:
        f.write("\n".join(lines))

    print(f"Generated SQL queries for {len(model_files)} models")
    print(f"Output: {output_path}")
    return output_path


def generate_neo4j_verify_queries():
    """Generate Cypher queries to verify the graph in Neo4j."""
    return """
-- ═══════════════════════════════════════════════════════════════
-- Neo4j Verification Queries
-- Run these in Neo4j Browser (bolt://localhost:7687)
-- ═══════════════════════════════════════════════════════════════

-- 1. Node counts
MATCH (s:Schema) RETURN 'Schemas' AS type, count(s) AS count
UNION ALL
MATCH (t:Table) RETURN 'Tables' AS type, count(t) AS count
UNION ALL
MATCH (c:Column) RETURN 'Columns' AS type, count(c) AS count;

-- 2. Relationship counts
MATCH ()-[r:DEPENDS_ON]->() RETURN 'DEPENDS_ON' AS type, count(r) AS count
UNION ALL
MATCH ()-[r:MAPS_TO]->() RETURN 'MAPS_TO' AS type, count(r) AS count
UNION ALL
MATCH ()-[r:HAS_TABLE]->() RETURN 'HAS_TABLE' AS type, count(r) AS count
UNION ALL
MATCH ()-[r:HAS_COLUMN]->() RETURN 'HAS_COLUMN' AS type, count(r) AS count;

-- 3. Full lineage chain for each target model
MATCH path = (t:Table)-[:DEPENDS_ON*]->(up:Table)
WHERE t.schema = 'silver_layer'
RETURN t.name AS model,
       [n IN nodes(path) WHERE n:Table | n.name] AS lineage_chain,
       length(path) AS depth
ORDER BY depth DESC;

-- 4. Column-level lineage (which columns connect to which)
MATCH (c:Column)-[:MAPS_TO]->(up:Column)
RETURN c.schema + '.' + c.table + '.' + c.name AS source_column,
       up.schema + '.' + up.table + '.' + up.name AS target_column
LIMIT 50;

-- 5. Find models with column lineage to specific upstream table
MATCH (c:Column)-[:MAPS_TO]->(up:Column)
WHERE up.table = 't2_master_hubops'
RETURN c.table AS model, c.name AS column,
       up.name AS upstream_column
ORDER BY model, column;

-- 6. Generate SQL JOIN clause from lineage
MATCH (t:Table)-[:DEPENDS_ON]->(up:Table)
OPTIONAL MATCH (c:Column)-[:MAPS_TO]->(uc:Column)
WHERE c.table = t.name AND uc.table = up.name
WITH t, up, collect(DISTINCT {
  source: c.name,
  target: uc.name
}) AS join_keys
WHERE size(join_keys) > 0
RETURN t.name + ' LEFT JOIN ' + up.name + ' ON ' +
       reduce(s = '', x IN join_keys |
         s + 't.' + x.source + ' = ' + up.name + '.' + x.target + ' AND '
       ) AS join_clause
LIMIT 20;

-- 7. All models with complete column-to-upstream mapping
MATCH (t:Table)
WHERE t.schema = 'silver_layer'
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(up:Table)
OPTIONAL MATCH (c:Column)-[:MAPS_TO]->(uc:Column)
WHERE c.table = t.name AND uc.table = up.name
RETURN t.name AS model,
       count(DISTINCT up) AS upstream_count,
       count(DISTINCT c) AS mapped_columns,
       count(DISTINCT uc) AS upstream_columns
ORDER BY model;
"""


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate SQL JOIN queries from lineage YAML')
    parser.add_argument('--model', '-m', help='Generate for a specific model only')
    parser.add_argument('--all', '-a', action='store_true', help='Generate for all models')
    parser.add_argument('--verify', '-v', action='store_true',
                        help='Print Neo4j verification Cypher queries')
    args = parser.parse_args()

    if args.verify:
        print(generate_neo4j_verify_queries())
    elif args.model:
        print(generate_join_sql(args.model))
    else:
        generate_all_sqls()
