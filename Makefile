.PHONY: setup run dry-run clean-db push-lineage push-dry-run verify venv help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## One-time project setup (venv + install + .env)
	bash setup.sh

run: ## Run PostgreSQL→Neo4j pipeline (reads config/tables.yaml)
	.venv/bin/postgres-to-neo4j

dry-run: ## Dry run — show what would be written, don't touch Neo4j
	.venv/bin/postgres-to-neo4j --dry-run

tables: ## Run with inline table list override
	.venv/bin/postgres-to-neo4j --tables "$(T)"

push-lineage: ## Push dbt lineage YAML → Neo4j (reads config/model_lineage/)
	.venv/bin/python -m postgres_to_neo4j.lineage_loader -y

push-dry-run: ## Dry-run for lineage push (summary only)
	.venv/bin/python -m postgres_to_neo4j.lineage_loader --dry-run

push-summary: ## Show lineage summary without connecting to Neo4j
	.venv/bin/python -m postgres_to_neo4j.lineage_loader --summary

verify: ## Verify Neo4j data with Cypher queries
	@echo "Run these in Neo4j Browser or via cypher-shell:"
	@echo ""
	@echo "  # ── Counts ──────────────────────────────────────────────"
	@echo "  MATCH (s:Schema) RETURN count(s) AS schemas;"
	@echo "  MATCH (t:Table) RETURN count(t) AS tables;"
	@echo "  MATCH (c:Column) RETURN count(c) AS columns;"
	@echo "  MATCH ()-[d:DEPENDS_ON]->() RETURN count(d) AS depends_on;"
	@echo "  MATCH ()-[m:MAPS_TO]->() RETURN count(m) AS maps_to;"
	@echo ""
	@echo "  # ── LLM Discovery Queries ───────────────────────────────"
	@echo ""
	@echo "  # 1. ALL tables and their columns (for LLM schema context)"
	@echo '  MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)'
	@echo '  RETURN t.name AS table, collect(c.name) AS columns'
	@echo '  ORDER BY table;'
	@echo ""
	@echo "  # 2. Given a report model, find its upstream tables + joinable columns"
	@echo '  MATCH (t:Table {name: "t3_delivery_mis_report"})'
	@echo '  OPTIONAL MATCH (t)-[:DEPENDS_ON]->(up:Table)'
	@echo '  OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)-[:MAPS_TO]->(upc:Column)<-[:HAS_COLUMN]-(up:Table)'
	@echo '  RETURN t.name AS model, up.name AS upstream,'
	@echo '         collect(DISTINCT {model_col: c.name, upstream_col: upc.name}) AS join_cols'
	@echo '  ORDER BY upstream;'
	@echo ""
	@echo "  # 3. ALL available model→upstream joins (for report→table routing)"
	@echo '  MATCH (t:Table)-[:DEPENDS_ON]->(up:Table)'
	@echo '  OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)-[:MAPS_TO]->(upc:Column)'
	@echo '  RETURN t.name AS model, up.name AS upstream,'
	@echo '         collect(DISTINCT {model_col: c.name, upstream_col: upc.name}) AS join_cols'
	@echo '  ORDER BY model, upstream;'
	@echo ""
	@echo "  # 4. For each model, which upstream tables connect (DEPENDS_ON)"
	@echo '  MATCH (t:Table)-[:DEPENDS_ON]->(up:Table)'
	@echo '  RETURN t.name AS model, collect(up.name) AS upstreams'
	@echo '  ORDER BY model;'
	@echo ""
	@echo "  # 5. Find the shortest JOIN path between two tables"
	@echo '  MATCH path = shortestPath((a:Table {name: "t3_Eway_Report"})-[:DEPENDS_ON*]->(b:Table {name: "t1_prs_premise_master_hubops"}))'
	@echo '  RETURN [n IN nodes(path) | n.name] AS tables;'

clean-db: ## Clear Neo4j database and re-import from PG
	@echo "Skipping confirmation with -y"
	.venv/bin/postgres-to-neo4j -y

venv: ## Recreate virtual environment
	rm -rf .venv
	python3 -m venv .venv
	.venv/bin/pip install --quiet --upgrade pip
	.venv/bin/pip install --quiet -e .

reinstall: ## Reinstall package in venv
	.venv/bin/pip install --quiet -e .

generate-joins: ## Regenerate SQL JOIN queries from lineage YAML
	.venv/bin/python -m scripts.sql_generator

patch-lineage: ## Recompute column_lineage from SQL for all models
	.venv/bin/python scripts/patch_lineage_4_models.py

push-all: push-lineage generate-joins verify ## Full pipeline: push → joins → verify
