# Pipeline de Dados em Nuvem para Aprendizagem de Máquina

Projeto Final Integrado - IFG, Pós-Graduação em Inteligência Artificial Aplicada (Módulo 2).
Disciplinas integradas: Modelagem de Dados para IA, Aprendizagem de Máquina e Cloud Computing.

**Entregáveis:** [Apresentação](docs/Apresentacao_Projeto_Final.pptx) · [Relatório](docs/Relatorio_Projeto_Final.docx) · [Dicionário de dados](docs/dicionario_de_dados.md) · [Checklist de requisitos](docs/checklist_requisitos.md)

**Problema:** prever quais chamados de suporte técnico têm maior risco de **violar o SLA de
resolução**, para que o gestor consiga priorizar a fila e realocar agentes antes do prazo estourar.

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
- **ML:** classificação binária (sla_breach), com dois baselines, o mesmo algoritmo (KNN) em versão
  *hard-code* (NumPy) e com biblioteca (scikit-learn), além de um MLP (rede neural) para comparação.
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

## Passo a passo completo, do zero

Numa máquina limpa (só Python 3.10+ e, para o dashboard, Docker):

```bash
# 1. ambiente e dependências
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. pipeline inteiro (ingestão -> atributos -> ML -> warehouse -> dbt -> dashboard)
.venv/bin/python run_pipeline.py            # ~8 s, termina com PASS=22

# 3. dashboard: sobe Postgres + Metabase e roda os mesmos modelos dbt no Postgres
docker compose -f infra/docker-compose.yml up -d
export WAREHOUSE_TARGET=postgres
.venv/bin/python -m src.warehouse.load_warehouse
.venv/bin/python -m src.warehouse.run_dbt
unset WAREHOUSE_TARGET

# 4. crie o admin em http://localhost:3000 e uma API key
#    (Admin -> Authentication -> API keys), salve em .env:  MB_API_KEY=mb_...
.venv/bin/python dashboard/criar_cards_metabase.py     # cria os 10 cards + filtros

# 5. Airflow (ambiente separado — ver a seção "Como executar com Airflow")
.venv-airflow/bin/airflow dags test pipeline_suporte_tecnico 2026-08-14
```

Nada em `data/` precisa ser baixado: o passo 2 regenera tudo com semente fixa, então
os números são idênticos em qualquer máquina.

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
python -m src.ml.train_evaluate             # 3. ML (KNN hard-code + sklearn, MLP)
python -m src.warehouse.load_warehouse      # 4. carga no warehouse
python -m src.warehouse.run_dbt             # 5. dbt build (modelos + testes)
python -m src.warehouse.export_dashboard    # 6. export do dashboard
```

## Como executar com Airflow

A DAG `pipeline_suporte_tecnico` reproduz as mesmas 7 etapas do `run_pipeline.py`, com
dependências explícitas, `retries` e agendamento diário. Evidência da última execução
(7/7 tasks SUCCESS): [`evidencias/airflow_dag_run.log`](evidencias/airflow_dag_run.log).

### Por que dois ambientes virtuais

O Airflow e o projeto têm dependências **incompatíveis nos dois sentidos**:

| pacote | Airflow 2.10 | projeto (dbt/pandas) |
|---|---|---|
| `sqlalchemy` | 1.4.x | 2.0.x |
| `protobuf` | 4.25.x | 6.x (exigido pelo `dbt-core`) |

Não existe ordem de `PYTHONPATH` que satisfaça ambos. Por isso o Airflow vive em
`.venv-airflow` e a DAG usa `BashOperator`: o Airflow **orquestra**, e cada task roda no
interpretador do projeto (`.venv`), em subprocesso isolado — executando exatamente o mesmo
`python -m src.<módulo>` documentado acima.

### Instalação e execução

```bash
python3 -m venv .venv-airflow
.venv-airflow/bin/pip install "apache-airflow==2.10.5" \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt"
```

```bash
export PROJECT_ROOT=$(pwd)
export AIRFLOW_HOME=$PROJECT_ROOT/.airflow
export PATH="$PROJECT_ROOT/.venv-airflow/bin:$PATH"
airflow db migrate
```

Ajuste uma única vez o `.airflow/airflow.cfg` (o padrão vem errado para este projeto):

```ini
dags_folder = /caminho/para/projeto-final-ia-suporte-sla/airflow/dags
load_examples = False
```

Rodar a DAG inteira pela linha de comando:

```bash
airflow dags test pipeline_suporte_tecnico 2026-08-14
```

Abrir a interface web (é o que se mostra na apresentação — o grafo e o histórico):

```bash
airflow standalone
```

Acesse <http://localhost:8080> com o usuário `admin`; a senha é gerada na primeira execução
e fica em `.airflow/standalone_admin_password.txt`.

> O `airflow standalone` chama subcomandos pelo `PATH`; sem o `export PATH` acima ele sobe
> o processo principal e falha nos filhos com `FileNotFoundError: 'airflow'`.

## Ambiente analítico local: Postgres + Metabase (Docker)

O `infra/docker-compose.yml` sobe um **Postgres** (warehouse cliente-servidor) e o
**Metabase** (visualização, driver nativo — sem plugin da comunidade).

```bash
docker compose -f infra/docker-compose.yml up -d

export WAREHOUSE_TARGET=postgres
python -m src.warehouse.load_warehouse   # carrega o schema raw
python -m src.warehouse.run_dbt          # PASS=22 no Postgres
```

Depois abra <http://localhost:3000>, crie o usuário administrador e adicione o banco:

| Campo | Valor |
|---|---|
| Tipo | PostgreSQL |
| Host | `postgres` (de dentro do container) |
| Porta | `5432` (de dentro) · `5433` a partir do host |
| Banco | `suporte_dw` |
| Usuário / Senha | `suporte` / `suporte` |
| Schema | `analytics` |

Com o admin criado, gere uma **API key** (Admin → Authentication → API keys), salve em
`.env` na raiz (`MB_API_KEY=mb_...`) e monte o painel inteiro por script:

```bash
python dashboard/criar_cards_metabase.py
```

Ele cria a conexão, os **10 cards** e o dashboard *Suporte - Apoio a Decisão* com filtros
de prioridade, categoria e canal. É idempotente: rodar de novo atualiza, não duplica.
As mesmas consultas, em SQL puro, estão em
[`dashboard/metabase_queries.sql`](dashboard/metabase_queries.sql).

> **Portabilidade comprovada:** os mesmos 12 modelos e 10 testes rodam com `PASS=22`
> tanto no DuckDB quanto no Postgres, sem alterar uma linha de SQL — só o `--target`.
> Foi esse exercício que revelou o único trecho não portável do projeto: o `cast(... as
> double)` em `stg_predictions`, um atalho que só existe no DuckDB, trocado pelo tipo
> ANSI `double precision`.

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

| Modelo | Acurácia | Precisão | Recall | F1 | ROC-AUC |
|--------|:---:|:---:|:---:|:---:|:---:|
| KNN (hard-code) | 0,838 | 0,762 | 0,421 | 0,542 | 0,882 |
| KNN (scikit-learn) | 0,838 | 0,762 | 0,421 | 0,542 | 0,882 |
| **MLP (produção)** | 0,887 | 0,747 | 0,765 | 0,756 | 0,944 |

O KNN *na mão* e o do scikit-learn ficaram idênticos (concordância de 100% nas predições),
confirmando a corretude da implementação manual. Todos os testes do dbt passaram (PASS=22).
