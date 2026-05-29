import json

from postgres_to_neo4j.models.schemas import TableData, ForeignKeyInfo, ViewDepInfo

CYPHER_CLEAN = "MATCH (n) DETACH DELETE n"

CYPHER_MERGE_SCHEMA = """
    MERGE (s:Schema {name: $name})
    RETURN s
"""

CYPHER_MERGE_TABLE = """
    MATCH (s:Schema {name: $schema_name})
    MERGE (t:Table {name: $table_name, schema: $schema_name})
    SET t.type = $table_type
    MERGE (s)-[:HAS_TABLE]->(t)
    RETURN t
"""

CYPHER_MERGE_COLUMN = """
    MATCH (t:Table {name: $table_name, schema: $schema_name})
    MERGE (c:Column {name: $col_name, table: $table_name, schema: $schema_name})
    SET c.data_type = $data_type,
        c.is_nullable = $is_nullable,
        c.is_primary_key = $is_pk,
        c.default = $default_value,
        c.ordinal_position = $ordinal_position
    MERGE (t)-[:HAS_COLUMN {ordinal_position: $ordinal_position}]->(c)
    RETURN c
"""

CYPHER_FK_TABLE = """
    MATCH (src:Table {schema: $src_schema, name: $src_table})
    MATCH (tgt:Table {schema: $tgt_schema, name: $tgt_table})
    MERGE (src)-[r:FK_CONSTRAINT {name: $constraint_name}]->(tgt)
    RETURN r
"""

CYPHER_FK_COLUMN = """
    MATCH (src:Column {schema: $src_schema, table: $src_table, name: $src_col})
    MATCH (tgt:Column {schema: $tgt_schema, table: $tgt_table, name: $tgt_col})
    MERGE (src)-[r:FK_REFERENCE {constraint_name: $constraint_name}]->(tgt)
    RETURN r
"""

CYPHER_VIEW_DEP = """
    MATCH (v:Table {schema: $view_schema, name: $view_name})
    MATCH (t:Table {schema: $ref_schema, name: $ref_table})
    MERGE (v)-[r:VIEW_DEPENDS_ON]->(t)
    RETURN r
"""


class Neo4jWriter:
    def __init__(self, connection, dry_run: bool = False):
        self.conn = connection
        self.dry_run = dry_run

    def _log(self, cypher: str, params: dict):
        if self.dry_run:
            print(f"  [DRY-RUN] {cypher[:90]}… params={json.dumps(params)[:100]}")

    def clean(self):
        if self.dry_run:
            print("  [DRY-RUN] CLEAN — MATCH (n) DETACH DELETE n")
            return
        self.conn.run(CYPHER_CLEAN)

    def write_schema(self, name: str):
        self._log(CYPHER_MERGE_SCHEMA, {"name": name})
        if not self.dry_run:
            self.conn.run(CYPHER_MERGE_SCHEMA, {"name": name})

    def write_table(self, schema: str, table: str, table_type: str):
        params = {"schema_name": schema, "table_name": table, "table_type": table_type.lower()}
        self._log(CYPHER_MERGE_TABLE, params)
        if not self.dry_run:
            self.conn.run(CYPHER_MERGE_TABLE, params)

    def write_column(self, schema: str, table: str, col) -> None:
        params = {
            "schema_name": schema,
            "table_name": table,
            "col_name": col.column_name,
            "data_type": col.data_type,
            "is_nullable": col.is_nullable,
            "is_pk": col.is_primary_key,
            "default_value": col.default,
            "ordinal_position": col.ordinal_position,
        }
        self._log(CYPHER_MERGE_COLUMN, params)
        if not self.dry_run:
            self.conn.run(CYPHER_MERGE_COLUMN, params)

    def write_fk(self, schema: str, table: str, fk: ForeignKeyInfo) -> None:
        table_params = {
            "src_schema": schema,
            "src_table": table,
            "tgt_schema": fk.ref_schema,
            "tgt_table": fk.ref_table,
            "constraint_name": fk.constraint_name,
        }
        col_params = {
            "src_schema": schema,
            "src_table": table,
            "src_col": fk.fk_column,
            "tgt_schema": fk.ref_schema,
            "tgt_table": fk.ref_table,
            "tgt_col": fk.ref_column,
            "constraint_name": fk.constraint_name,
        }
        self._log(CYPHER_FK_TABLE, table_params)
        self._log(CYPHER_FK_COLUMN, col_params)
        if not self.dry_run:
            self.conn.run(CYPHER_FK_TABLE, table_params)
            self.conn.run(CYPHER_FK_COLUMN, col_params)

    def write_view_dep(self, view_schema: str, view_name: str, dep: ViewDepInfo) -> None:
        params = {
            "view_schema": view_schema,
            "view_name": view_name,
            "ref_schema": dep.ref_schema,
            "ref_table": dep.ref_table,
        }
        self._log(CYPHER_VIEW_DEP, params)
        if not self.dry_run:
            self.conn.run(CYPHER_VIEW_DEP, params)

    def write_table_data(self, data: TableData) -> None:
        t = data.table
        self.write_table(t.table_schema, t.table_name, t.table_type)

        for col in data.columns:
            self.write_column(t.table_schema, t.table_name, col)

        for fk in data.foreign_keys:
            self.write_fk(t.table_schema, t.table_name, fk)

        for dep in data.view_depends_on:
            self.write_view_dep(t.table_schema, t.table_name, dep)
