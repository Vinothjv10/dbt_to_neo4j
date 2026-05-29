-- ═══════════════════════════════════════════════════════════════════
-- Neo4j Lineage Mapping Inspection Queries
-- ═══════════════════════════════════════════════════════════════════

-- 1. OVERVIEW: Node & relationship counts
MATCH (s:Schema) RETURN 'Schemas' AS item, count(s) AS count
UNION ALL MATCH (t:Table) RETURN 'Tables', count(t)
UNION ALL MATCH (c:Column) RETURN 'Columns', count(c)
UNION ALL MATCH ()-[r:DEPENDS_ON]->() RETURN 'DEPENDS_ON edges', count(r)
UNION ALL MATCH ()-[r:MAPS_TO]->() RETURN 'MAPS_TO edges', count(r)
UNION ALL MATCH ()-[r:HAS_COLUMN]->() RETURN 'HAS_COLUMN edges', count(r);

-- 2. TABLE-LEVEL: Which report models exist and what they depend on
MATCH (t:Table)
WHERE t.name STARTS WITH 't3_'
OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(up:Table)
RETURN t.name AS model,
       count(DISTINCT up.name) AS upstream_count,
       collect(DISTINCT up.name) AS upstreams,
       count(DISTINCT c.name) AS column_count
ORDER BY model;

-- 3. COLUMN-LEVEL: For each model, how many columns have MAPS_TO lineage resolved
MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)
WHERE t.name STARTS WITH 't3_'
OPTIONAL MATCH (c)-[:MAPS_TO]->(upc:Column)
RETURN t.name AS model,
       count(DISTINCT c.name) AS total_columns,
       count(DISTINCT upc) AS mapped_columns,
       count(DISTINCT c.name) - count(DISTINCT upc) AS unmapped,
       round(100.0 * count(DISTINCT upc) / count(DISTINCT c.name), 1) AS coverage_pct
ORDER BY coverage_pct DESC;

-- 4. DETAILED: Show every model column that HAS a MAPS_TO, and where it maps to
MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)-[:MAPS_TO]->(upc:Column)<-[:HAS_COLUMN]-(up:Table)
WHERE t.name STARTS WITH 't3_'
RETURN t.name AS model,
       c.name AS model_column,
       up.name AS upstream_table,
       upc.name AS upstream_column
ORDER BY model, model_column;

-- 5. DETAILED: Show every model column that LACKS a MAPS_TO (unresolved)
MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)
WHERE t.name STARTS WITH 't3_'
  AND NOT (c)-[:MAPS_TO]->(:Column)
RETURN t.name AS model,
       c.name AS unresolved_column
ORDER BY model, unresolved_column;

-- 6. UPSTREAM PERSPECTIVE: For each upstream table, which models use it
MATCH (t:Table)-[:DEPENDS_ON]->(up:Table)
RETURN up.name AS upstream_table,
       count(t.name) AS used_by_count,
       collect(t.name) AS used_by_models
ORDER BY used_by_count DESC;

-- 7. COLUMN JOIN KEYS: For a specific model, what JOIN conditions can be built
MATCH (t:Table {name: 't3_delivery_mis_report'})-[:DEPENDS_ON]->(up:Table)
OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)-[:MAPS_TO]->(upc:Column)<-[:HAS_COLUMN]-(up)
RETURN up.name AS upstream,
       collect(DISTINCT {model_col: c.name, upstream_col: upc.name}) AS join_conditions
ORDER BY upstream;

-- 8. SEARCH: Find all paths from any t3 model to any upstream table
MATCH path = (t:Table)-[:HAS_COLUMN]->(c:Column)-[:MAPS_TO]->(upc:Column)
WHERE t.name STARTS WITH 't3_'
RETURN t.name AS model,
       c.name AS column,
       labels(upc) AS target_labels,
       properties(upc) AS target_properties
LIMIT 20;

-- 9. CROSS-MODEL visibility: Which upstream columns have MAPS_TO back to them?
MATCH (upc:Column)<-[:MAPS_TO]-(c:Column)-[:HAS_COLUMN]-(t:Table)
RETURN upc.table AS upstream_table,
       upc.name AS upstream_column,
       count(DISTINCT t.name) AS mapped_from_models,
       collect(DISTINCT t.name + '.' + c.name) AS source_paths
ORDER BY mapped_from_models DESC;

-- 10. COMPLETE INVENTORY: Every relationship path from Schema → Column
MATCH path = (s:Schema)-[:HAS_TABLE]->(t:Table)-[:HAS_COLUMN]->(c:Column)
OPTIONAL MATCH (c)-[m:MAPS_TO]->(upc:Column)
RETURN s.name AS schema,
       t.name AS table,
       collect({column: c.name, maps_to: upc.name}) AS columns_with_lineage
ORDER BY table;
