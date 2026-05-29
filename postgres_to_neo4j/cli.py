import argparse
import sys

from postgres_to_neo4j.config import (
    PostgresConfig,
    Neo4jConfig,
    TablesConfig,
    PipelineSettings,
)
from postgres_to_neo4j.postgres import PostgresConnection, PostgresExtractor
from postgres_to_neo4j.neo4j import Neo4jConnection, Neo4jWriter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="postgres-to-neo4j",
        description="Extract PostgreSQL table schemas & lineage and store in Neo4j.",
    )
    parser.add_argument(
        "--tables",
        help="Override: comma-separated table patterns "
             "(e.g. 'public.sales,public.orders' or 'public.*')",
    )
    parser.add_argument("--pg-dsn", help="Override PostgreSQL DSN")
    parser.add_argument("--neo4j-uri", help="Override Neo4j bolt URI")
    parser.add_argument("--neo4j-user", help="Override Neo4j user")
    parser.add_argument("--neo4j-password", help="Override Neo4j password")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print extracted data without writing to Neo4j")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Skip confirmation prompt before clearing Neo4j")
    parser.add_argument("--no-clear", action="store_true",
                        help="Don't clear Neo4j before writing (append mode)")
    return parser


def main():
    args = build_parser().parse_args()

    # ── Load configs ───────────────────────────────────────────────────
    pg_cfg = PostgresConfig.from_env()
    neo4j_cfg = Neo4jConfig.from_env()
    settings = PipelineSettings.from_env()
    tables_cfg = TablesConfig.from_env() if not args.tables else None

    # CLI overrides
    if args.pg_dsn:
        pg_cfg.dsn = args.pg_dsn
    if args.neo4j_uri:
        neo4j_cfg.uri = args.neo4j_uri
    if args.neo4j_user:
        neo4j_cfg.user = args.neo4j_user
    if args.neo4j_password:
        neo4j_cfg.password = args.neo4j_password

    table_patterns = (
        [t.strip() for t in args.tables.split(",")]
        if args.tables
        else tables_cfg.patterns
    )

    dry_run = args.dry_run
    clear_db = settings.neo4j_write.clear_before_write and not args.no_clear

    # ── Extract from PostgreSQL ────────────────────────────────────────
    print("Connecting to PostgreSQL...")
    try:
        with PostgresConnection(pg_cfg.dsn) as pg:
            extractor = PostgresExtractor(pg)
            tables = extractor.resolve_tables(table_patterns)
    except Exception as e:
        print(f"PostgreSQL error: {e}", file=sys.stderr)
        sys.exit(1)

    if not tables:
        print("No matching tables found. Exiting.")
        sys.exit(0)

    print(f"Found {len(tables)} table(s):")
    for t in tables:
        print(f"  {t.table_schema}.{t.table_name} ({t.table_type})")

    print("Extracting schema & lineage...")
    with PostgresConnection(pg_cfg.dsn) as pg:
        extractor = PostgresExtractor(pg)
        all_data = extractor.extract_all(table_patterns)

    # ── Write to Neo4j ─────────────────────────────────────────────────
    schemas = sorted({d.table.table_schema for d in all_data})

    print("Connecting to Neo4j...")
    try:
        with Neo4jConnection(neo4j_cfg.uri, neo4j_cfg.user, neo4j_cfg.password) as n4j_conn:
            writer = Neo4jWriter(n4j_conn, dry_run=dry_run)

            if clear_db and not dry_run and not args.yes:
                confirm = input("This will CLEAR the Neo4j database. Continue? (y/N): ")
                if confirm.lower() != "y":
                    print("Aborted.")
                    return

            if clear_db:
                writer.clean()

            for schema in schemas:
                writer.write_schema(schema)

            for data in all_data:
                writer.write_table_data(data)

    except Exception as e:
        print(f"Neo4j error: {e}", file=sys.stderr)
        sys.exit(1)

    print("Done!")
    print(f"  Schemas: {len(schemas)}")
    print(f"  Tables:  {len(all_data)}")
