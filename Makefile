PYTHON := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: help env venv install run destroy validate-raw process ml load dbt dashboard clean

help:
	@echo "Comandos principais:"
	@echo "  make env      cria .env-aws a partir de .env-aws.example, se ainda nao existir"
	@echo "  make run      cria .venv, instala dependencias e executa a pipeline completa"
	@echo "  make destroy  esvazia o bucket S3 e remove a stack CloudFormation"
	@echo "  make clean    remove artefatos locais da execucao, mantendo data/raw"
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
