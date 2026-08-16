PYTHON := .venv/bin/python
PIP := .venv/bin/pip
COMPOSE := docker compose -f infra/docker-compose.yml

.PHONY: help env venv install run destroy validate-raw process ml load dbt dashboard clean \
        stack-up stack-down stack-reset stack-ps publish-bi metabase prints bi airflow-run airflow-logs

help:
	@echo "Comandos principais:"
	@echo "  make env         cria .env-aws a partir de .env-aws.example, se ainda nao existir"
	@echo "  make run         pipeline completo: dados -> ML -> dbt -> Postgres -> Metabase -> S3"
	@echo "  make destroy     esvazia o bucket S3 e remove a stack CloudFormation"
	@echo "  make clean       remove artefatos locais da execucao, mantendo data/raw"
	@echo ""
	@echo "Ambiente local (Docker):"
	@echo "  make stack-up    sobe Postgres (5433), Metabase (3000) e Airflow (8081)"
	@echo "  make stack-down  para os containers, preservando os dados"
	@echo "  make stack-reset apaga tudo e recria do zero (inclusive o Metabase)"
	@echo "  make stack-ps    mostra o estado dos containers"
	@echo ""
	@echo "Camada de BI e orquestracao:"
	@echo "  make bi          publica no Postgres e provisiona o painel do Metabase"
	@echo "  make airflow-run dispara a DAG e grava evidencias/airflow_dag_run.log"
	@echo "  make airflow-logs  acompanha os logs do container do Airflow"
	@echo ""
	@echo "Antes de make run, preencha .env-aws com as credenciais AWS."

env:
	@if [ ! -f .env-aws ]; then \
		cp .env-aws.example .env-aws; \
		echo ".env-aws criado. Edite o arquivo com as credenciais AWS antes de rodar make run."; \
	else \
		echo ".env-aws ja existe."; \
	fi

venv:
	@test -x $(PYTHON) || python3 -m venv .venv

install: venv
	$(PIP) install -r requirements.txt

run: install
	$(PYTHON) run_pipeline.py

destroy: install
	$(PYTHON) -m src.cloud.destroy_aws

# ---------------------------------------------------------------- ambiente local
stack-up:
	$(COMPOSE) up -d --wait
	@echo "Postgres :5433 | Metabase :3000 | Airflow :8081 (admin/admin)"

stack-down:
	$(COMPOSE) down

# Apaga tambem os volumes: o Postgres e o Metabase voltam ao estado inicial.
# Use quando quiser provar a reprodutibilidade da entrega do zero.
stack-reset:
	$(COMPOSE) down -v
	$(COMPOSE) up -d --wait
	@echo "Stack recriada do zero. Rode: make bi"

stack-ps:
	$(COMPOSE) ps

# --------------------------------------------------------------------------- BI
publish-bi:
	$(PYTHON) -m src.bi.publish_bi

metabase:
	$(PYTHON) -m src.bi.metabase_setup

prints:
	$(PYTHON) -m src.bi.capturar_prints

bi: publish-bi metabase prints

# -------------------------------------------------------------------- orquestracao
# `dags test` executa a DAG inteira em primeiro plano, sem depender do scheduler:
# e' a forma mais direta de gerar evidencia reproduzivel da orquestracao.
airflow-run:
	$(PYTHON) -m src.orchestration.run_dag

airflow-logs:
	$(COMPOSE) logs -f airflow

# ------------------------------------------------------------------ etapas soltas
validate-raw:
	test -f data/raw/tickets.csv
	test -f data/raw/ticket_messages.jsonl
	test -f data/raw/ticket_events.json
process:
	$(PYTHON) -m src.processing.process_features
ml:
	$(PYTHON) -m src.ml.train_evaluate
load:
	$(PYTHON) -m src.warehouse.load_warehouse
dbt:
	$(PYTHON) -m src.warehouse.run_dbt
dashboard:
	$(PYTHON) -m src.warehouse.export_dashboard

clean:
	rm -rf data/processed/* data/curated/* dbt/target dbt/logs
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
