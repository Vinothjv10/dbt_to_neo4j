import re

from postgres_to_neo4j.models.schemas import (
    TableInfo,
    ColumnInfo,
    ForeignKeyInfo,
    ViewDepInfo,
    TableData,
)
from postgres_to_neo4j.postgres.queries import (
    RESOLVE_TABLES_ALL,
    RESOLVE_TABLES_BY_SCHEMA,
    RESOLVE_TABLES_FULLY_QUALIFIED,
    RESOLVE_TABLES_UNQUALIFIED,
    COLUMNS_WITH_PK,
    FOREIGN_KEYS,
    VIEW_DEPS_PGDEPEND,
    VIEW_DEFINITION,
)


class PostgresExtractor:
    def __init__(self, connection):
        self.conn = connection

    # ── Table resolution ─────────────────────────────────────────────────

    def resolve_tables(self, patterns: list[str]) -> list[TableInfo]:
        seen: set[tuple[str, str]] = set()
        results: list[TableInfo] = []

        for pattern in patterns:
            for row in self._resolve_one_pattern(pattern):
                key = (row["table_schema"], row["table_name"])
                if key not in seen:
                    seen.add(key)
                    results.append(TableInfo(
                        table_schema=row["table_schema"],
                        table_name=row["table_name"],
                        table_type=row["table_type"],
                        description=row.get("description") or "",
                    ))
        return results

    def _resolve_one_pattern(self, pattern: str) -> list[dict]:
        cur = self.conn.cursor()
        pattern = pattern.strip()

        if pattern == "*":
            cur.execute(RESOLVE_TABLES_ALL)
        elif pattern.endswith(".*"):
            cur.execute(RESOLVE_TABLES_BY_SCHEMA, (pattern[:-2],))
        elif "." in pattern:
            schema, tbl = pattern.split(".", 1)
            cur.execute(RESOLVE_TABLES_FULLY_QUALIFIED, (schema, tbl))
        else:
            cur.execute(RESOLVE_TABLES_UNQUALIFIED, (pattern,))

        return [dict(r) for r in cur.fetchall()]

    # ── Per-table extraction ──────────────────────────────────────────────

    def extract_columns(self, schema: str, table: str) -> list[ColumnInfo]:
        cur = self.conn.cursor()
        cur.execute(COLUMNS_WITH_PK, (schema, table, schema, table))
        return [
            ColumnInfo(
                column_name=r["column_name"],
                data_type=r["data_type"],
                is_nullable=r["is_nullable"] == "YES",
                is_primary_key=r["is_primary_key"],
                default=r["column_default"],
                ordinal_position=r["ordinal_position"],
            )
            for r in cur.fetchall()
        ]

    def extract_foreign_keys(self, schema: str, table: str) -> list[ForeignKeyInfo]:
        cur = self.conn.cursor()
        cur.execute(FOREIGN_KEYS, (schema, table))
        return [
            ForeignKeyInfo(
                constraint_name=r["constraint_name"],
                fk_column=r["fk_column"],
                ref_schema=r["ref_schema"],
                ref_table=r["ref_table"],
                ref_column=r["ref_column"],
            )
            for r in cur.fetchall()
        ]

    def extract_view_deps(self, schema: str, view_name: str) -> list[ViewDepInfo]:
        cur = self.conn.cursor()

        cur.execute(VIEW_DEPS_PGDEPEND, (view_name, schema))
        rows = cur.fetchall()
        if rows:
            return [ViewDepInfo(ref_schema=r["ref_schema"], ref_table=r["ref_table"]) for r in rows]

        cur.execute(VIEW_DEFINITION, (f"{schema}.{view_name}",))
        row = cur.fetchone()
        if not row or not row[0]:
            return []

        return self._parse_view_definition(row[0], schema, view_name)

    @staticmethod
    def _parse_view_definition(def_text: str, default_schema: str, view_name: str) -> list[ViewDepInfo]:
        deps: list[ViewDepInfo] = []
        lowered = def_text.lower()
        for m in re.finditer(
            r'(?:from|join)\s+(?:only\s+)?(?:"?(\w+)"?\.)?(?:"?(\w+)"?)',
            lowered,
        ):
            ref_schema = m.group(1) or default_schema
            ref_table = m.group(2)
            if ref_table and ref_table != view_name.lower():
                deps.append(ViewDepInfo(ref_schema=ref_schema, ref_table=ref_table))
        return deps

    # ── Full extraction for one table ─────────────────────────────────────

    def extract_table(self, table_info: TableInfo) -> TableData:
        data = TableData(table=table_info)
        data.columns = self.extract_columns(table_info.table_schema, table_info.table_name)
        data.foreign_keys = self.extract_foreign_keys(table_info.table_schema, table_info.table_name)

        if table_info.table_type in ("VIEW", "MATERIALIZED VIEW"):
            data.view_depends_on = self.extract_view_deps(
                table_info.table_schema, table_info.table_name
            )

        return data

    # ── Bulk extraction ───────────────────────────────────────────────────

    def extract_all(self, patterns: list[str]) -> list[TableData]:
        tables = self.resolve_tables(patterns)
        return [self.extract_table(t) for t in tables]
