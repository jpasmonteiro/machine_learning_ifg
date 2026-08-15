"""
DAG do Airflow para o pipeline de suporte tecnico.

Orquestra as MESMAS etapas do run_pipeline.py, com dependencias explicitas,
re-execucao por task e agendamento diario.

COMO RODAR
    make stack-up        # sobe Postgres + Metabase + Airflow (infra/docker-compose.yml)
    make airflow-run     # dispara a DAG e grava evidencias/airflow_dag_run.log
    # interface: http://localhost:8081  (usuario airflow / senha airflow)

POR QUE BashOperator E NAO PythonOperator
O Airflow fixa versoes de Jinja2/pandas que conflitam com as do dbt-core. Por
isso o codigo do projeto vive em um virtualenv separado (/opt/pipeline-venv,
criado em infra/airflow/Dockerfile) e cada task o invoca como subprocesso. O
scheduler so' orquestra; o pipeline roda exatamente com as versoes do
requirements.txt. Isso tambem isola falhas: uma task que quebra nao derruba o
processo do scheduler.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

# Dentro do container estas variaveis vem do docker-compose; fora dele, os
# defaults apontam para o repositorio e a .venv locais.
PROJECT_ROOT = os.environ.get("PROJECT_ROOT", "/opt/project")
PYTHON = os.environ.get("PIPELINE_PYTHON", "/opt/pipeline-venv/bin/python")


def etapa(modulo: str) -> str:
    """Comando bash que roda um modulo do projeto no venv isolado."""
    return f"cd {PROJECT_ROOT} && {PYTHON} -m {modulo}"


# A validacao dos brutos e' a unica etapa sem modulo proprio: a entrega ja' traz
# os arquivos materializados em data/raw, entao aqui so' conferimos a presenca.
VALIDA_BRUTOS = f"""
cd {PROJECT_ROOT}
for f in data/raw/tickets.csv data/raw/ticket_messages.jsonl data/raw/ticket_events.json; do
    if [ ! -f "$f" ]; then echo "[ingestao] ARQUIVO AUSENTE: $f"; exit 1; fi
    echo "[ingestao] ok: $f ($(wc -l < "$f") linhas)"
done
"""

# A etapa de nuvem depende de credenciais que nem sempre existem na maquina do
# avaliador. Sem .env-aws a task encerra com sucesso e uma mensagem clara, para
# a DAG poder ficar verde de ponta a ponta sem AWS.
UPLOAD_S3 = f"""
cd {PROJECT_ROOT}
if [ ! -f .env-aws ] && [ "${{AWS_STEP_OPTIONAL:-0}}" = "1" ]; then
    echo "[s3] .env-aws ausente -> etapa de nuvem pulada (AWS_STEP_OPTIONAL=1)."
    echo "[s3] Para exercitar a AWS, crie o .env-aws (make env) e redispare a DAG."
    exit 0
fi
{PYTHON} -m src.cloud.provision_and_upload
"""

default_args = {
    "owner": "grupo_suporte_ia",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="pipeline_suporte_tecnico",
    description="ELT + ML + BI para previsao de violacao de SLA em chamados de suporte",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["ifg", "pos-ia", "elt", "ml", "suporte"],
) as dag:

    t_ingestao = BashOperator(task_id="ingestao", bash_command=VALIDA_BRUTOS)

    t_processamento = BashOperator(
        task_id="processamento_atributos",
        bash_command=etapa("src.processing.process_features"))

    t_ml = BashOperator(
        task_id="treino_avaliacao_ml",
        bash_command=etapa("src.ml.train_evaluate"))

    t_carga = BashOperator(
        task_id="carga_warehouse",
        bash_command=etapa("src.warehouse.load_warehouse"))

    t_dbt = BashOperator(
        task_id="dbt_build",
        bash_command=etapa("src.warehouse.run_dbt"))

    t_export = BashOperator(
        task_id="export_dashboard",
        bash_command=etapa("src.warehouse.export_dashboard"))

    # Camada de BI: republica a modelagem no Postgres e provisiona o painel.
    t_bi = BashOperator(
        task_id="publicar_bi_postgres",
        bash_command=etapa("src.bi.publish_bi"))

    t_metabase = BashOperator(
        task_id="dashboard_metabase",
        bash_command=etapa("src.bi.metabase_setup"))

    t_s3 = BashOperator(task_id="upload_s3", bash_command=UPLOAD_S3)

    (t_ingestao >> t_processamento >> t_ml >> t_carga >> t_dbt
     >> t_export >> t_bi >> t_metabase >> t_s3)
