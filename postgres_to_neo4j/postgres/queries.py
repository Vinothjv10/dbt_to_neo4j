RESOLVE_TABLES_ALL = """
    SELECT t.table_schema, t.table_name, t.table_type,
           pg_catalog.obj_description(c.oid, 'pg_class') AS description
    FROM information_schema.tables t
    LEFT JOIN pg_catalog.pg_class c ON c.relname = t.table_name
    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
    WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema')
    ORDER BY t.table_schema, t.table_name
"""

RESOLVE_TABLES_BY_SCHEMA = """
    SELECT t.table_schema, t.table_name, t.table_type,
           pg_catalog.obj_description(c.oid, 'pg_class') AS description
    FROM information_schema.tables t
    LEFT JOIN pg_catalog.pg_class c ON c.relname = t.table_name
    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
    WHERE t.table_schema = %s
    ORDER BY t.table_name
"""

RESOLVE_TABLES_FULLY_QUALIFIED = """
    SELECT t.table_schema, t.table_name, t.table_type,
           pg_catalog.obj_description(c.oid, 'pg_class') AS description
    FROM information_schema.tables t
    LEFT JOIN pg_catalog.pg_class c ON c.relname = t.table_name
    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
    WHERE t.table_schema = %s AND t.table_name = %s
"""

RESOLVE_TABLES_UNQUALIFIED = """
    SELECT t.table_schema, t.table_name, t.table_type,
           pg_catalog.obj_description(c.oid, 'pg_class') AS description
    FROM information_schema.tables t
    LEFT JOIN pg_catalog.pg_class c ON c.relname = t.table_name
    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
    WHERE t.table_name = %s
    ORDER BY t.table_schema
"""

COLUMNS_WITH_PK = """
    SELECT
        c.column_name,
        c.data_type,
        c.is_nullable,
        c.column_default,
        c.ordinal_position,
        CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END AS is_primary_key
    FROM information_schema.columns c
    LEFT JOIN (
        SELECT ku.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage ku
            ON tc.constraint_name = ku.constraint_name
            AND tc.table_schema = ku.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = %s
          AND tc.table_name = %s
    ) pk USING (column_name)
    WHERE c.table_schema = %s AND c.table_name = %s
    ORDER BY c.ordinal_position
"""

FOREIGN_KEYS = """
    SELECT
        tc.constraint_name,
        kcu.column_name AS fk_column,
        ccu.table_schema AS ref_schema,
        ccu.table_name AS ref_table,
        ccu.column_name AS ref_column
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        USING (constraint_name, table_schema, table_name)
    JOIN information_schema.constraint_column_usage ccu
        USING (constraint_name)
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_schema = %s
      AND tc.table_name = %s
    ORDER BY kcu.ordinal_position
"""

VIEW_DEPS_PGDEPEND = """
    SELECT
        ns.nspname AS ref_schema,
        c.relname AS ref_table
    FROM pg_depend d
    JOIN pg_rewrite rw ON d.objid = rw.oid
    JOIN pg_class c ON c.oid = d.refobjid
    JOIN pg_namespace ns ON ns.oid = c.relnamespace
    JOIN pg_class base ON base.oid = rw.ev_class
    JOIN pg_namespace base_ns ON base_ns.oid = base.relnamespace
    WHERE base.relname = %s
      AND base_ns.nspname = %s
      AND d.deptype = 'n'
      AND c.relkind IN ('r', 'v', 'm')
"""

VIEW_DEFINITION = """
    SELECT pg_get_viewdef(%s::regclass, true) AS def
"""
