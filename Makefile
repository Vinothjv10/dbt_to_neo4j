.PHONY: help setup venv reinstall
.PHONY: run dry-run tables clean-db
.PHONY: push-lineage push-dry-run push-summary generate-joins patch-lineage validate
.PHONY: manage-add manage-remove manage-list manage-force-add
.PHONY: verify verify-counts push-all push-all-validate howto workflow

SHELL := bash

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────────────────

setup: ## One-time project setup (creates venv, installs deps, copies .env)
	bash setup.sh

venv: ## Recreate Python virtual environment from scratch
	rm -rf .venv
	python3 -m venv .venv
	.venv/bin/pip install --quiet --upgrade pip
	.venv/bin/pip install --quiet -e .

reinstall: ## Reinstall package in existing venv
	.venv/bin/pip install --quiet -e .

# ── PG → Neo4j Schema Sync (optional — requires PostgreSQL) ─────────────

run: ## Run PG→Neo4j schema sync (reads config/tables.yaml)
	.venv/bin/postgres-to-neo4j

dry-run: ## Dry-run PG→Neo4j schema sync (preview only)
	.venv/bin/postgres-to-neo4j --dry-run

tables: ## PG→Neo4j with inline table list: make tables T=table1,table2
	.venv/bin/postgres-to-neo4j --tables "$(T)"

clean-db: ## Clear Neo4j database and re-import from PG
	.venv/bin/postgres-to-neo4j -y

# ── dbt Lineage Pipeline (YAML → Neo4j) ────────────────────────────────

push-lineage: ## Push dbt lineage YAML files to Neo4j (reads config/model_lineage/)
	.venv/bin/python -m postgres_to_neo4j.lineage_loader -y

push-dry-run: ## Dry-run lineage push (summary only, no DB write)
	.venv/bin/python -m postgres_to_neo4j.lineage_loader --dry-run

push-summary: ## Show lineage summary without connecting to Neo4j
	.venv/bin/python -m postgres_to_neo4j.lineage_loader --summary

generate-joins: ## Regenerate SQL JOIN queries from lineage YAML
	.venv/bin/python -m scripts.sql_generator

patch-lineage: ## Recompute column_lineage from SQL for known models
	.venv/bin/python scripts/patch_lineage_4_models.py

validate: ## Validate all models: SQL refs vs YAML, columns vs lineage, tables.yaml
	.venv/bin/python scripts/validate_all_models.py

# ── Model Management ────────────────────────────────────────────────────

manage-add: ## Add a model: make manage-add M=name [DRY_RUN=1] [DBT_PATH=/path/to/dbt]
	.venv/bin/python scripts/manage_models.py add --model $(M) $(if $(DRY_RUN),--dry-run,) $(if $(DBT_PATH),--dbt-path $(DBT_PATH),)

manage-force-add: ## Force-add (overwrite YAML): make manage-force-add M=name [DBT_PATH=/path]
	.venv/bin/python scripts/manage_models.py add --model $(M) --force $(if $(DBT_PATH),--dbt-path $(DBT_PATH),)

manage-remove: ## Remove a model: make manage-remove M=name [DRY_RUN=1]
	.venv/bin/python scripts/manage_models.py remove --model $(M) $(if $(DRY_RUN),--dry-run,)

manage-list: ## List all models with upstream/column counts
	.venv/bin/python scripts/manage_models.py list

# ── Verification ────────────────────────────────────────────────────────

verify: ## Verify Neo4j: counts + all model→upstream joins (requires .env + cypher-shell)
	source .env && cypher-shell -a "$$NEO4J_URI" -u "$$NEO4J_USER" -p "$$NEO4J_PASSWORD" \
		"MATCH (s:Schema) RETURN count(s) AS schemas; \
		 MATCH (t:Table) RETURN count(t) AS tables; \
		 MATCH (c:Column) RETURN count(c) AS columns; \
		 MATCH ()-[d:DEPENDS_ON]->() RETURN count(d) AS depends_on; \
		 MATCH ()-[m:MAPS_TO]->() RETURN count(m) AS maps_to;"
	@echo "── All model→upstream joins ────────────────────────"
	source .env && cypher-shell -a "$$NEO4J_URI" -u "$$NEO4J_USER" -p "$$NEO4J_PASSWORD" \
		"MATCH (t:Table)-[:DEPENDS_ON]->(up:Table) \
		 OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)-[:MAPS_TO]->(upc:Column) \
		 RETURN t.name AS model, up.name AS upstream, \
				collect(DISTINCT {model_col: c.name, upstream_col: upc.name}) AS join_cols \
		 ORDER BY model, upstream;"

verify-counts: ## Quick verify: Neo4j counts only (faster)
	source .env && cypher-shell -a "$$NEO4J_URI" -u "$$NEO4J_USER" -p "$$NEO4J_PASSWORD" \
		"MATCH (s:Schema) RETURN count(s) AS schemas; \
		 MATCH (t:Table) RETURN count(t) AS tables; \
		 MATCH (c:Column) RETURN count(c) AS columns; \
		 MATCH ()-[d:DEPENDS_ON]->() RETURN count(d) AS depends_on; \
		 MATCH ()-[m:MAPS_TO]->() RETURN count(m) AS maps_to;"

# ── Full Pipelines ──────────────────────────────────────────────────────

push-all: push-lineage generate-joins verify ## Standard cycle: push → joins → verify

push-all-validate: push-lineage generate-joins validate verify ## Extended cycle: push → joins → validate → verify

# ── Docs ────────────────────────────────────────────────────────────────

howto: ## List available HOWTO documents
	@echo "Available guides:"
	@echo "  make howto-add     — Add a new model"
	@echo "  make howto-remove  — Remove a model"
	@echo "  make howto-full    — Full combined reference (add + remove)"

howto-add: ## Show the HOWTO for adding a model
	@cat HOWTO_add_model.md | less

howto-remove: ## Show the HOWTO for removing a model
	@cat HOWTO_remove_model.md | less

howto-full: ## Show the full combined HOWTO (add + remove)
	@cat HOWTO_add_remove_models.md | less

workflow: ## Show the internal workflow document (what happens when adding a model)
	@cat WORKFLOW.md | less
