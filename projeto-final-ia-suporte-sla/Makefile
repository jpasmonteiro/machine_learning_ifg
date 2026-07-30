.PHONY: install run ingest process ml load dbt dashboard clean

install:
	pip install -r requirements.txt

run:
	python run_pipeline.py

ingest:
	python -m src.ingestion.generate_data
process:
	python -m src.processing.process_features
ml:
	python -m src.ml.train_evaluate
load:
	python -m src.warehouse.load_warehouse
dbt:
	python -m src.warehouse.run_dbt
dashboard:
	python -m src.warehouse.export_dashboard
	python dashboard/gerar_mockup.py

clean:
	rm -rf data/raw/* data/processed/* data/curated/* dbt/target dbt/logs
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
