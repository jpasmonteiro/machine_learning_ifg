"""
DAG do Airflow para o pipeline de suporte tecnico.

Orquestra as mesmas 7 etapas do run_pipeline.py, com dependencias explicitas,
re-execucao por task e agendamento diario.

POR QUE BashOperator E NAO PythonOperator
-----------------------------------------
O Airflow e o projeto tem dependencias INCOMPATIVEIS entre si:

    pacote       Airflow 2.10   projeto (dbt/pandas)
    sqlalchemy   1.4.x          2.0.x
    protobuf     4.25.x         6.x  (exigido pelo dbt-core)

Nao existe ordem de PYTHONPATH que satisfaca os dois: se o projeto vence, o
Airflow nao sobe; se o Airflow vence, o dbt quebra. A solucao e' isolamento por
processo: o Airflow apenas ORQUESTRA, e cada task executa no interpretador do
proprio projeto (.venv), num subprocesso separado.

Isso tambem preserva o principio de nao duplicar logica: cada task roda
exatamente o mesmo comando documentado no README (`python -m src.<modulo>`),
que e' o mesmo codigo chamado pelo run_pipeline.py.

CONFIGURACAO
    PROJECT_ROOT     raiz do projeto (default: dois niveis acima deste arquivo)
    PROJECT_PYTHON   interpretador do projeto (default: $PROJECT_ROOT/.venv/bin/python)
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_ROOT = os.environ.get(
    "PROJECT_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)
PROJECT_PYTHON = os.environ.get(
    "PROJECT_PYTHON", os.path.join(PROJECT_ROOT, ".venv", "bin", "python")
)

ETAPAS = [
    ("ingestao",                "src.ingestion.generate_data"),
    ("processamento_atributos", "src.processing.process_features"),
    ("treino_avaliacao_ml",     "src.ml.train_evaluate"),
    ("carga_warehouse",         "src.warehouse.load_warehouse"),
    ("dbt_build",               "src.warehouse.run_dbt"),
    ("export_dashboard",        "src.warehouse.export_dashboard"),
    ("upload_s3",               "src.cloud.s3_sync"),
]

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

    anterior = None
    for task_id, modulo in ETAPAS:
        # PYTHONPATH e' zerado de proposito: impede que os pacotes do Airflow
        # vazem para o subprocesso e conflitem com os do projeto.
        atual = BashOperator(
            task_id=task_id,
            bash_command=f"cd {PROJECT_ROOT} && PYTHONPATH= {PROJECT_PYTHON} -m {modulo}",
        )
        if anterior:
            anterior >> atual
        anterior = atual
