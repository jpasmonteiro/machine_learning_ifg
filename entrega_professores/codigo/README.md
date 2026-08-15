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

Pipeline ELT completo, dos dados brutos versionados até o dashboard de decisão:

```
dados raw  ->  processamento/atributos  ->  ML (treino+avaliação)  ->  carga no warehouse
   ->  dbt (staging/dims/facts + testes)  ->  export  ->  dashboard (Metabase)
```

- **Dados (3 fontes em `data/raw/`):** estruturada (CSV de tickets), não estruturada (texto livre, JSONL) e
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
│   ├── ingestion/          # script usado para gerar a base raw versionada
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
├── run_pipeline.py         # roda o pipeline inteiro com CloudFormation + S3
└── requirements.txt
```

## Como executar

Requisitos: Python 3.10+ e credenciais AWS em `.env-aws`.

```bash
make env
# edite .env-aws com as credenciais AWS
make run
```

Esta entrega já inclui os arquivos de entrada em `data/raw/`. O comando provisiona o bucket S3 via
CloudFormation, valida esses arquivos e executa as demais etapas:

- `data/raw/` como entrada versionada;
- `data/processed/` e `data/curated/warehouse.duckdb`;
- `evidencias/metrics.json`, `matriz_confusao.png`, `curva_roc.png`, `dashboard_mockup.png`;
- `data/curated/dashboard/dashboard_data.json` (alimenta o mockup do dashboard).
- upload obrigatório das camadas para o S3;
- limpeza final do bucket e da stack CloudFormation.

Para rodar etapas isoladas:

```bash
python -m src.processing.process_features   # 2. processamento/atributos
python -m src.ml.train_evaluate             # 3. ML (hard-code + sklearn + RF)
python -m src.warehouse.load_warehouse      # 4. carga no warehouse
python -m src.warehouse.run_dbt             # 5. dbt build (modelos + testes)
python -m src.warehouse.export_dashboard    # 6. export do dashboard
```

O script `src.ingestion.generate_data` permanece no repositório para rastrear como a base foi
produzida, mas não é chamado pelo `run_pipeline.py` da entrega.

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

## AWS obrigatória na execução local

Na entrega, o uso de AWS não é opcional. Antes de rodar `python run_pipeline.py`, crie
`.env-aws` a partir de `.env-aws.example` com as credenciais AWS.

O próprio `run_pipeline.py`:

- lê obrigatoriamente o `.env-aws`;
- provisiona um bucket S3 com `infra/cloudformation-s3-pipeline.yaml`;
- executa processamento, ML, warehouse, dbt e export do dashboard;
- envia `raw`, `processed` e `curated` para o S3;
- esvazia o bucket e destrói a stack CloudFormation no final.

Se `.env-aws` não existir ou estiver incompleto, o script interrompe a execução e imprime o modelo
do arquivo e as permissões AWS necessárias.

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
