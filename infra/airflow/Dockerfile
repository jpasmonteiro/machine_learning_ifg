# Imagem do Airflow para o pipeline de suporte tecnico.
#
# ISOLAMENTO DE DEPENDENCIAS
# O Airflow fixa versoes de Jinja2, pandas e afins que conflitam com o dbt-core.
# Por isso o codigo do projeto NAO e' instalado no ambiente do Airflow: ele fica
# em um virtualenv separado (/opt/pipeline-venv) e as tasks o invocam via
# BashOperator. O scheduler so' precisa saber disparar processos; o pipeline roda
# com exatamente as mesmas versoes do requirements.txt usadas fora do Airflow.
FROM apache/airflow:2.10.5-python3.12

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 # /opt pertence ao root; o venv e' criado pelo usuario airflow, entao a pasta
 # precisa existir com o dono certo antes do USER airflow.
 && install -d -o airflow -g root /opt/pipeline-venv

USER airflow

# Virtualenv isolado com as dependencias do pipeline (pandas, sklearn, dbt, boto3).
COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /opt/pipeline-venv \
 && /opt/pipeline-venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/pipeline-venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

# Provider do Postgres para o metadata DB do proprio Airflow.
RUN pip install --no-cache-dir "apache-airflow-providers-postgres==5.14.0"
