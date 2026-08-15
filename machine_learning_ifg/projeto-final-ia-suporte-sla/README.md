# Pipeline de Dados em Nuvem para Aprendizagem de Máquina

Projeto Final Integrado - IFG, Pós-Graduação em Inteligência Artificial Aplicada (Módulo 2).
Disciplinas integradas: Modelagem de Dados para IA, Aprendizagem de Máquina e Cloud Computing.

**Entregáveis:** [Apresentação](docs/Apresentacao_Projeto_Final.pptx) · [Relatório](docs/Relatorio_Projeto_Final.docx) · [Dicionário de dados](docs/dicionario_de_dados.md) · [Checklist de requisitos](docs/checklist_requisitos.md)

**Problema:** Prever quais chamados de suporte técnico têm maior risco de **violar o SLA de
resolução,** para que o gestor consiga priorizar a fila e realocar agentes antes do prazo estourar.

## Integrantes

- João Paulo Monteiro
- Pedro Felipe De Moraes Carrijo
- Rogério dos Anjos

> Substitua os nomes acima pelos integrantes reais do grupo.

## Visão geral da solução

Pipeline ELT completo, do dado bruto até o dashboard de decisão:

```
ingestão  ->  processamento/atributos  ->  ML (treino+avaliação)  ->  carga no warehouse
   ->  dbt (staging/dims/facts + testes)  ->  export  ->  dashboard (Metabase)
```

- **Dados (3 fontes):** estruturada (CSV de tickets), não estruturada (texto livre, JSONL) e
  semiestruturada (logs de eventos, JSON).
- **Warehouse:** DuckDB local como *proxy* do Snowflake (a mesma modelagem dbt roda nos dois).
- **ML:** classificação binária (sla_breach), com baseline, versão *hard-code* (NumPy) e versão
  com biblioteca (scikit-learn), além de Random Forest.
- **Nuvem:** Amazon S3 + template CloudFormation (infra/cloudformation.yaml) e diagrama 100% AWS.
- **Dashboard:** Metabase (queries em dashboard/) + mockup navegável (dashboard/mockup.html).

## Estrutura do repositório

```
.
├── config/                 # configuração central (caminhos, constantes, SLA)
├── src/
│   ├── ingestion/          # geração/ingestão dos dados brutos
│   ├── processing/         # limpeza e extração de atributos
│   ├── ml/                 # knn_scratch (hard-code), features, train_evaluate
│   ├── warehouse/          # carga (DuckDB/Snowflake), execução dbt, export
│   └── cloud/              # upload das camadas para o Amazon S3 (boto3)
├── dbt/                    # projeto dbt (models staging + marts, testes, macros)
├── airflow/dags/           # DAG do Airflow
├── infra/                  # CloudFormation, diagrama AWS, custos
├── dashboard/              # queries Metabase, guia e mockup
├── docs/                   # relatório (.docx), apresentação (.pptx), dicionário de dados
├── evidencias/             # prints/saídas (métricas, matriz de confusão, ROC, dashboard)
├── run_pipeline.py         # roda o pipeline inteiro localmente
└── requirements.txt
```

## Como executar (local, sem nuvem)

Requisitos: Python 3.10+.

```bash
pip install -r requirements.txt
python run_pipeline.py
```

Isso executa todas as etapas e gera:

- `data/raw/`, `data/processed/` e `data/curated/warehouse.duckdb`;
- `evidencias/metrics.json`, `matriz_confusao.png`, `curva_roc.png`, `dashboard_mockup.png`;
- `data/curated/dashboard/dashboard_data.json` (alimenta o mockup do dashboard).

Para rodar etapas isoladas:

```bash
python -m src.ingestion.generate_data       # 1. ingestão
python -m src.processing.process_features   # 2. processamento/atributos
python -m src.ml.train_evaluate             # 3. ML (hard-code + sklearn + RF)
python -m src.warehouse.load_warehouse      # 4. carga no warehouse
python -m src.warehouse.run_dbt             # 5. dbt build (modelos + testes)
python -m src.warehouse.export_dashboard    # 6. export do dashboard
```

## Como executar com Airflow

Copie `airflow/dags/pipeline_suporte_dag.py` para a pasta `dags/` do seu Airflow (ou use o
docker-compose oficial do Airflow) e defina `PROJECT_ROOT` apontando para esta pasta. A DAG
`pipeline_suporte_tecnico` reproduz as mesmas etapas do `run_pipeline.py`.

## Como apontar para Snowflake (produção)

A modelagem dbt é a mesma. Exporte as variáveis e troque o alvo:

```bash
export WAREHOUSE_TARGET=snowflake
export SNOWFLAKE_ACCOUNT=... SNOWFLAKE_USER=... SNOWFLAKE_PASSWORD=...
export SNOWFLAKE_DATABASE=SUPORTE_DW SNOWFLAKE_WAREHOUSE=COMPUTE_WH
python -m src.warehouse.load_warehouse
python -m src.warehouse.run_dbt
```

## Como provisionar a infraestrutura AWS

```bash
aws cloudformation deploy \
  --template-file infra/cloudformation.yaml \
  --stack-name suporte-ia-dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides ProjectName=suporte-ia Environment=dev
```

## Enviar os dados para o S3 (uso real de serviço AWS)

A etapa `src/cloud/s3_sync.py` envia as camadas `raw/processed/curated` para o bucket
(via boto3). Ela roda automaticamente no fim do `run_pipeline.py` quando o bucket está
definido; sem `S3_BUCKET`, é pulada e a execução continua local.

```bash
export S3_BUCKET=$(aws cloudformation describe-stacks --stack-name suporte-ia-dev \
  --query "Stacks[0].Outputs[?OutputKey=='RawBucketName'].OutputValue" --output text)
export S3_PREFIX=suporte-sla
pip install boto3
python -m src.cloud.s3_sync     # ou rode o pipeline inteiro: python run_pipeline.py
```

> A lógica de upload foi validada localmente com um S3 simulado (biblioteca `moto`).

## Rodando na AWS Academy (Learner Lab)

O Learner Lab bloqueia a criacao de IAM Roles. Use o template
`infra/cloudformation-academy.yaml` (que reutiliza o `LabRole` em vez de criar um) e o
upload S3, que nao exige role. Passo a passo completo em `docs/aws_academy.md`.

```bash
export AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...  AWS_SESSION_TOKEN=...
export AWS_DEFAULT_REGION=us-east-1
aws cloudformation deploy --template-file infra/cloudformation-academy.yaml --stack-name suporte-ia
export S3_BUCKET=$(aws cloudformation describe-stacks --stack-name suporte-ia \
  --query "Stacks[0].Outputs[?OutputKey=='RawBucketName'].OutputValue" --output text)
python -m src.cloud.s3_sync
```

## Dashboard (Metabase)

Veja `dashboard/README_metabase.md`. As consultas de cada card estão em
`dashboard/metabase_queries.sql`. Para uma prévia rápida sem instalar nada, abra
`dashboard/mockup.html` no navegador.

## Resultados (resumo)

| Modelo             | Acurácia | Precisão | Recall |  F1  | ROC-AUC |
| ------------------ | :-------: | :-------: | :----: | :---: | :-----: |
| KNN (hard-code)    |   0,838   |   0,762   | 0,421 | 0,542 |  0,882  |
| KNN (scikit-learn) |   0,838   |   0,762   | 0,421 | 0,542 |  0,882  |
| SVM (produção)   |   0,903   |   0,854   | 0,693 | 0,765 |  0,953  |
| MLP                |   0,888   |   0,747   | 0,765 | 0,756 |  0,944  |

O KNN *na mão* e o do scikit-learn ficaram idênticos (concordância de 100% nas predições),
confirmando a corretude da implementação manual. Todos os testes do dbt passaram (PASS=22).
