# README de execução - Projeto Final IA Suporte SLA

## Objetivo

Este projeto implementa um pipeline de dados e aprendizagem de máquina para prever quais chamados
de suporte técnico têm maior risco de violar o SLA de resolução. A previsão apoia o gestor na
priorização da fila e na realocação de agentes antes do prazo estourar.

## O que está incluído

- Dados brutos já materializados em `data/raw/` para execução direta da entrega.
- Três fontes de dados: estruturada (`tickets.csv`), não estruturada (`ticket_messages.jsonl`) e semiestruturada (`ticket_events.json`).
- Processamento e extração de atributos de negócio, texto e logs.
- Modelos de classificação: baseline, KNN hard-code, KNN scikit-learn, SVM e MLP.
- Warehouse local em DuckDB como proxy do Snowflake.
- Projeto dbt com staging, dimensões, fatos, mart analítico e testes.
- DAG do Airflow para orquestração.
- Provisionamento obrigatório de bucket Amazon S3 via CloudFormation.
- Sincronização obrigatória das camadas `raw`, `processed` e `curated` para o Amazon S3.
- Dashboard Metabase por consultas SQL e mockup HTML.

## Requisitos

- Python 3.10 ou superior.
- `pip`.
- Credenciais AWS em `.env-aws`.
- Opcional: Docker, caso queira subir Metabase localmente.

Não é necessário instalar AWS CLI. O provisionamento usa `boto3`, instalado pelo
`requirements.txt`.

## Dados de entrada

Os arquivos usados pela pipeline já estão incluídos no repositório da entrega:

- `data/raw/tickets.csv`
- `data/raw/ticket_messages.jsonl`
- `data/raw/ticket_events.json`

Eles ficam versionados como base de entrada da entrega. Ao executar `run_pipeline.py`, a pipeline valida a existência desses três arquivos e segue para processamento, modelagem, warehouse, dbt e dashboard.

## Arquivo obrigatório `.env-aws`

Antes de executar a pipeline, crie o arquivo `.env-aws` na raiz desta pasta (`codigo/`).
Use o modelo `.env-aws.example`:

```bash
make env
```

Preencha:

```text
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...   # obrigatório no AWS Academy; opcional fora dele
AWS_DEFAULT_REGION=us-east-1
CFN_STACK_NAME=suporte-sla-entrega
PROJECT_NAME=suporte-sla-entrega
S3_PREFIX=suporte-sla
```

Se o arquivo não existir ou estiver incompleto, `python run_pipeline.py` interrompe a execução e
mostra as instruções para criação.

## Permissões AWS necessárias

A credencial usada no `.env-aws` precisa permitir:

- `sts:GetCallerIdentity`
- `cloudformation:CreateStack`
- `cloudformation:UpdateStack`
- `cloudformation:DescribeStacks`
- `cloudformation:DescribeStackEvents`
- `cloudformation:DeleteStack`
- `s3:CreateBucket`
- `s3:PutEncryptionConfiguration`
- `s3:PutBucketPublicAccessBlock`
- `s3:PutObject`
- `s3:ListBucket`
- `s3:GetBucketLocation`
- `s3:DeleteObject`
- `s3:DeleteBucket`

No AWS Academy, copie as credenciais temporárias em **AWS Details > AWS CLI** e cole no `.env-aws`.


Exemplo de policy IAM para anexar ao usuário usado no `.env-aws`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:DeleteStack"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:PutEncryptionConfiguration",
        "s3:PutBucketPublicAccessBlock",
        "s3:PutObject",
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:DeleteObject",
        "s3:DeleteBucket"
      ],
      "Resource": [
        "arn:aws:s3:::suporte-sla-entrega-*",
        "arn:aws:s3:::suporte-sla-entrega-*/*"
      ]
    }
  ]
}
```

## Execução local completa

Forma recomendada:

```bash
make run
```

O `make run` cria `.venv`, instala as dependências e executa `run_pipeline.py`.

Forma manual:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_pipeline.py
```

O comando executa:

1. Leitura obrigatória do `.env-aws`.
2. Criação/atualização da stack CloudFormation.
3. Provisionamento do bucket S3.
4. Validação dos dados brutos existentes em `data/raw/`.
5. Processamento e extração de atributos.
6. Treino e avaliação dos modelos.
7. Carga no warehouse DuckDB.
8. Execução do dbt com modelos e testes.
9. Exportação dos dados do dashboard.
10. Upload obrigatório das camadas `raw`, `processed` e `curated` para o S3.
11. Recursos AWS permanecem ativos para inspeção após a execução.

## Saídas esperadas

Após a execução, ficam disponíveis:

- `data/raw/`: dados brutos de entrada, já incluídos na entrega.
- `data/processed/`: features e predições.
- `data/curated/warehouse.duckdb`: warehouse local.
- `data/curated/dashboard/dashboard_data.json`: dados para o mockup.
- `evidencias/metrics.json`: métricas dos modelos.
- `evidencias/matriz_confusao.png`: matriz de confusão do modelo final.
- `evidencias/curva_roc.png`: curva ROC comparativa.
- `evidencias/dashboard_mockup.png`: imagem do dashboard.

## Execução por etapa

```bash
python -m src.processing.process_features
python -m src.ml.train_evaluate
python -m src.warehouse.load_warehouse
python -m src.warehouse.run_dbt
python -m src.warehouse.export_dashboard
```

A pipeline principal da entrega usa exclusivamente os arquivos versionados em `data/raw/`.

Também é possível usar o Makefile:

```bash
make install
make run
```

## Dashboard

Para uma prévia rápida, abra:

```text
dashboard/mockup.html
```

Para montar no Metabase, use as consultas em:

```text
dashboard/metabase_queries.sql
```

O guia completo está em:

```text
dashboard/README_metabase.md
```

## AWS / S3

O template usado pela execução local é:

```text
infra/cloudformation-s3-pipeline.yaml
```

Ele cria somente um bucket S3, com criptografia SSE-S3 e bloqueio de acesso público. A pipeline
envia as três camadas para prefixos dentro desse bucket:

- `suporte-sla/raw/`
- `suporte-sla/processed/`
- `suporte-sla/curated/`

Ao final da execução, o bucket permanece ativo para validação. Para esvaziar o bucket e remover a stack CloudFormation, execute `make destroy`.

## Resultados principais

Dados da última execução registrada:

| Modelo | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Baseline majoritária | 0.772 | 0.000 | 0.000 | 0.000 | 0.500 |
| Baseline por prioridade | 0.771 | 0.498 | 0.629 | 0.556 | 0.721 |
| KNN hard-code | 0.838 | 0.762 | 0.421 | 0.542 | 0.882 |
| KNN scikit-learn | 0.838 | 0.762 | 0.421 | 0.542 | 0.882 |
| SVM | 0.903 | 0.854 | 0.693 | 0.765 | 0.953 |
| MLP | 0.888 | 0.747 | 0.765 | 0.756 | 0.944 |

O KNN implementado manualmente teve 100% de concordância com o KNN do scikit-learn, validando a
implementação hard-code. O melhor modelo por F1 foi o SVM, selecionado como modelo de produção.

