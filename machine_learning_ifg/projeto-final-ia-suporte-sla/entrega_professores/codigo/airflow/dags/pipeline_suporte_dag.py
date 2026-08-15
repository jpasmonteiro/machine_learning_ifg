"""
DAG do Airflow para o pipeline de suporte tecnico.

Orquestra as mesmas etapas do run_pipeline.py, mas com dependencias explicitas,
re-execucao por task e agendamento diario. Para subir o Airflow localmente,
use o docker-compose em airflow/ (ver README) e aponte o AIRFLOW_HOME para
este projeto, ou copie esta DAG para a pasta dags/ do seu Airflow.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# garante que o pacote do projeto fique visivel para os imports da DAG
PROJECT_ROOT = os.environ.get(
    "PROJECT_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _ingestao():
    from pathlib import Path
    from config.settings import RAW_DIR

    expected = [
        RAW_DIR / "tickets.csv",
        RAW_DIR / "ticket_messages.jsonl",
        RAW_DIR / "ticket_events.json",
    ]
    missing = [str(path) for path in expected if not Path(path).is_file()]
    if missing:
        raise FileNotFoundError("Arquivos brutos ausentes: " + ", ".join(missing))
    print("Arquivos brutos encontrados em data/raw.")


def _processamento():
    from src.processing import process_features
    process_features.run()


def _ml():
    from src.ml import train_evaluate
    train_evaluate.run()


def _carga():
    from src.warehouse import load_warehouse
    load_warehouse.run()


def _dbt_build():
    from src.warehouse import run_dbt
    run_dbt.run()


def _export():
    from src.warehouse import export_dashboard
    export_dashboard.run()


def _upload_s3():
    from src.cloud import s3_sync
    s3_sync.run()


default_args = {
    "owner": "grupo_suporte_ia",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="pipeline_suporte_tecnico",
    description="ELT + ML para previsao de violacao de SLA em chamados de suporte",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["ifg", "pos-ia", "elt", "ml", "suporte"],
) as dag:

    t_ingestao = PythonOperator(task_id="ingestao", python_callable=_ingestao)
    t_processamento = PythonOperator(task_id="processamento_atributos", python_callable=_processamento)
    t_ml = PythonOperator(task_id="treino_avaliacao_ml", python_callable=_ml)
    t_carga = PythonOperator(task_id="carga_warehouse", python_callable=_carga)
    t_dbt = PythonOperator(task_id="dbt_build", python_callable=_dbt_build)
    t_export = PythonOperator(task_id="export_dashboard", python_callable=_export)
    t_s3 = PythonOperator(task_id="upload_s3", python_callable=_upload_s3)

    # ingestao -> processamento -> ML -> carga -> dbt -> export
    t_ingestao >> t_processamento >> t_ml >> t_carga >> t_dbt >> t_export >> t_s3
