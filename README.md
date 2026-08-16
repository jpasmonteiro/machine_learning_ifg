# Projeto Final - IA para Suporte e SLA

Projeto Final Integrado - IFG, Pós-Graduação em Inteligência Artificial Aplicada.

Este repositório contém a entrega final do projeto: código executável, dados de entrada, relatório, apresentação, evidências e instruções completas de execução.

## Objetivo

O projeto implementa um pipeline de dados e aprendizagem de máquina para prever quais chamados de suporte técnico têm maior risco de violar o SLA de resolução. A previsão apoia o gestor de suporte na priorização da fila e na realocação de agentes antes que o prazo seja estourado.

A variável-alvo é `sla_breach`, que indica se o chamado violou ou não o SLA de resolução definido pela prioridade.

| Prioridade | SLA de resolução |
| ---------- | -----------------: |
| Crítica   |            240 min |
| Alta       |            480 min |
| Média     |           1440 min |
| Baixa      |           2880 min |

## Entregáveis

- Escopo do projeto PDF: [relatorio/Projeto_Final.pdf](relatorio/Projeto_Final.pdf)
- Relatório editável: [relatorio/Relatorio_Projeto_Final.docx](relatorio/Relatorio_Projeto_Final.docx)
- Apresentação: [apresentacao/Apresentacao_Projeto_Final.pdf](apresentacao/Apresentacao_Projeto_Final.pdf)
- Código executável e dados de entrada na raiz do repositório
- Dashboard no Metabase: provisionado por `make run`, em http://localhost:3000
- Detalhamento das últimas adições: [docs/ADICOES_ENTREGA.md](docs/ADICOES_ENTREGA.md)

---

## Início rápido

### Pré-requisitos

- **Python 3.10+** e **Docker Desktop aberto** (o Docker sobe o Postgres, o Metabase e o Airflow).
- Credenciais AWS no arquivo `.env-aws` (veja o passo 1).

### Passo 1 — credenciais AWS

```bash
make env
```

Cria o `.env-aws` a partir do modelo. **Abra o arquivo e preencha** com as credenciais
da AWS (no AWS Academy: *AWS Details → AWS CLI*). Sem isso o pipeline para no início.

### Passo 2 — rodar o pipeline completo

```bash
make run
```

Um comando só: cria a `.venv`, instala as dependências, sobe os containers, executa
ingestão → atributos → ML → dbt → Postgres → Metabase → S3.

> A **primeira** execução leva de 8 a 12 minutos, porque baixa as dependências e
> constrói a imagem do Airflow. As seguintes levam cerca de 100 segundos.

### Passo 3 — executar a DAG do Airflow

```bash
make airflow-run
```

Roda a DAG de ponta a ponta e grava o resultado em `evidencias/airflow_dag_run.log`.

### Acessos

| Serviço      | Endereço                | Usuário                | Senha          |
| ------------ | ----------------------- | ---------------------- | -------------- |
| **Metabase** | http://localhost:3000   | `admin@suporte.local`  | `Suporte@2026` |
| **Airflow**  | http://localhost:8081   | `admin`                | `admin`        |
| Postgres     | `localhost:5433`        | `suporte`              | `suporte`      |

No Metabase, o painel é **"Suporte - Apoio a Decisao"**, com os filtros de
prioridade, categoria e canal no topo. No Airflow, a DAG é **`pipeline_suporte_tecnico`**.

> São credenciais de desenvolvimento local, versionadas de propósito para facilitar
> a avaliação. Não servem a nenhum ambiente real.

### Comandos úteis

```bash
make help          # lista todos os comandos
make stack-up      # sobe Postgres + Metabase + Airflow
make stack-down    # para os containers, preservando os dados
make stack-reset   # apaga containers e volumes e recria do zero
make destroy       # esvazia o bucket S3 e remove a stack CloudFormation
make clean         # remove artefatos locais, mantendo data/raw
```

### Se não tiver Docker

O pipeline **não quebra**: as etapas de Postgres e Metabase são puladas com aviso e
o restante (ingestão, ML, dbt, S3) roda normalmente. Nesse caso, o dashboard pode ser
conferido pelos prints em `evidencias/metabase_dashboard.png` e
`evidencias/metabase_dashboard_filtro.png`.

---

## Estrutura principal

```text
.
├── README.md                         # guia principal da entrega
├── Makefile                          # make run, stack-up, bi, airflow-run, destroy
├── .env-aws.example                  # modelo de credenciais AWS
├── requirements.txt                  # dependências Python
├── run_pipeline.py                   # orquestrador principal
├── data/
│   ├── raw/                          # dados brutos já materializados
│   ├── processed/                    # saídas processadas/features
│   └── curated/                      # warehouse DuckDB e dados do dashboard
├── src/
│   ├── processing/                   # limpeza e extração de atributos
│   ├── ml/                           # KNN hard-code, sklearn, SVM e MLP
│   ├── warehouse/                    # carga no warehouse, dbt e export de dados
│   ├── bi/                           # Postgres, Metabase e controle dos containers
│   ├── orchestration/                # disparo da DAG e evidência
│   └── cloud/                        # CloudFormation e S3
├── config/                           # configurações do projeto
├── dbt/                              # modelos e testes dbt (duckdb/postgres/snowflake)
├── dashboard/                        # guia e consultas SQL do Metabase
├── infra/                            # CloudFormation, docker-compose, custos e diagrama
├── docs/                             # dicionário de dados e adições da entrega
├── evidencias/                       # métricas, gráficos, DAG e prints do Metabase
├── relatorio/                        # relatório final
├── apresentacao/                     # slides da apresentação
└── airflow/dags/                     # DAG do pipeline
```

## Visão geral da solução

Fluxo principal:

```text
dados raw -> processamento/features -> machine learning -> warehouse DuckDB -> dbt
   -> Postgres (BI) -> dashboard no Metabase -> S3
```

O projeto inclui:

- Dados brutos já materializados em `data/raw/`.
- Três fontes: estruturada (`tickets.csv`), não estruturada (`ticket_messages.jsonl`) e semiestruturada (`ticket_events.json`).
- Processamento e extração de atributos de negócio, texto e logs.
- Modelos de classificação: baseline, KNN hard-code, KNN scikit-learn, SVM e MLP.
- Warehouse local em DuckDB como proxy de Snowflake.
- Modelagem dbt com staging, dimensões, fatos, mart de ML, mart de decisão e testes.
- Republicação da mesma modelagem dbt em Postgres, sem alterar SQL (portabilidade).
- Dashboard no **Metabase** com 10 cards e filtros de prioridade, categoria e canal,
  provisionado por script via API.
- Orquestração pela **DAG do Airflow** (9 tasks), em container.
- Provisionamento obrigatório de bucket Amazon S3 via CloudFormation.
- Upload das camadas `raw`, `processed` e `curated` para o S3.

### Serviços locais

`make run` sobe os containers automaticamente (`infra/docker-compose.yml`):

| Serviço  | Endereço                | Credenciais                             |
| -------- | ----------------------- | --------------------------------------- |
| Metabase | http://localhost:3000   | `admin@suporte.local` / `Suporte@2026`  |
| Airflow  | http://localhost:8081   | `admin` / `admin`                       |
| Postgres | `localhost:5433`        | `suporte` / `suporte`                   |

Sem Docker na máquina, as etapas de BI são puladas com aviso e o restante do
pipeline roda normalmente (`SKIP_BI=1` força o pulo).

## Como executar

### 1. Criar o arquivo de credenciais AWS

```bash
make env
```

Esse comando cria `.env-aws` a partir de `.env-aws.example`. Preencha o arquivo com suas credenciais AWS:

```text
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
# Para AWS Academy, descomente e cole o token completo.
# AWS_SESSION_TOKEN=...
AWS_DEFAULT_REGION=us-east-1
CFN_STACK_NAME=suporte-sla-entrega
PROJECT_NAME=suporte-sla-entrega
S3_PREFIX=suporte-sla
```

### 2. Permissões AWS necessárias

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

Policy IAM de exemplo:

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

### 3. Rodar o pipeline completo

```bash
make run
```

O `make run` cria a `.venv`, instala as dependências e executa o pipeline completo.

A execução faz:

1. Lê obrigatoriamente o `.env-aws`.
2. Cria ou atualiza a stack CloudFormation.
3. Provisiona um bucket S3.
4. Valida os dados brutos já existentes em `data/raw/`.
5. Processa atributos estruturados, textuais e de logs.
6. Treina e avalia os modelos.
7. Carrega o warehouse DuckDB.
8. Executa os modelos e testes dbt.
9. Exporta os agregados do dashboard.
10. Sobe os containers e republica a camada analítica no Postgres.
11. Provisiona o dashboard no Metabase (10 cards + 3 filtros).
12. Envia as camadas `raw`, `processed` e `curated` para o S3.

Ao final, os recursos AWS permanecem ativos para validação no console. Para remover tudo depois da validação:

```bash
make destroy
```

### 4. Executar a DAG do Airflow

```bash
make airflow-run
```

Sobe a stack, aguarda o banco de metadados do Airflow e executa a DAG
`pipeline_suporte_tecnico` de ponta a ponta, gravando o resultado por task em
`evidencias/airflow_dag_run.log`. A interface fica em http://localhost:8081
(`admin` / `admin`).

O `make destroy` esvazia o bucket S3 e remove a stack CloudFormation.

## Dados de entrada

Os dados de entrada já estão versionados em:

```text
data/raw/tickets.csv
data/raw/ticket_messages.jsonl
data/raw/ticket_events.json
```

## Saídas da execução

Após `make run`, os principais artefatos ficam em:

```text
data/processed/
data/curated/warehouse.duckdb
data/curated/dashboard/dashboard_data.json
evidencias/metrics.json
evidencias/matriz_confusao.png
evidencias/curva_roc.png
evidencias/metabase_dashboard.png            # painel no Metabase
evidencias/metabase_dashboard_filtro.png     # o mesmo, com filtro aplicado
evidencias/metabase_dashboard.log            # cards executados + prova do filtro
evidencias/airflow_dag_run.log               # DAG 9/9 SUCCESS (após make airflow-run)
```

No S3, os arquivos são enviados para um bucket com nome parecido com:

```text
s3://suporte-sla-entrega-<id-da-conta>-us-east-1/suporte-sla/
```

Dentro dele ficam as camadas:

```text
suporte-sla/raw/
suporte-sla/processed/
suporte-sla/curated/
```

## Dashboard

O dashboard é a camada de visualização e apoio à decisão. Ele transforma os dados tratados e as predições do modelo em indicadores para o gestor de suporte.

Ele responde perguntas como:

- quantos chamados existem;
- qual é a taxa de violação de SLA;
- quais prioridades, categorias e canais mais violam SLA;
- quais chamados têm maior risco previsto;
- como o modelo está performando.

### Dashboard no Metabase (painel oficial)

Depois de `make run`, acesse:

```text
http://localhost:3000        (admin@suporte.local / Suporte@2026)
```

O painel "Suporte - Apoio a Decisao" é provisionado automaticamente por
`src/bi/metabase_setup.py`: 10 cards e três filtros (**prioridade, categoria e
canal**) ligados às colunas reais das tabelas. Ele lê o Postgres, onde o pipeline
republica os mesmos modelos dbt do DuckDB, sem alterar SQL.

Para rodar só a parte de BI: `make stack-up && make bi`.

Guia detalhado em [dashboard/README_metabase.md](dashboard/README_metabase.md);
as consultas dos cards estão em [dashboard/metabase_queries.sql](dashboard/metabase_queries.sql).

### Orquestração no Airflow

```text
http://localhost:8081        (admin / admin)
```

A DAG `pipeline_suporte_tecnico` executa as mesmas 9 etapas do `run_pipeline.py`.
Para disparar e gerar a evidência: `make airflow-run`.

## Resultados principais

| Modelo                  | Accuracy | Precision | Recall |    F1 | ROC-AUC |
| ----------------------- | -------: | --------: | -----: | ----: | ------: |
| Baseline majoritária   |    0.772 |     0.000 |  0.000 | 0.000 |   0.500 |
| Baseline por prioridade |    0.771 |     0.498 |  0.629 | 0.556 |   0.721 |
| KNN hard-code           |    0.838 |     0.762 |  0.421 | 0.542 |   0.882 |
| KNN scikit-learn        |    0.838 |     0.762 |  0.421 | 0.542 |   0.882 |
| SVM                     |    0.903 |     0.854 |  0.693 | 0.765 |   0.953 |
| MLP                     |    0.888 |     0.747 |  0.765 | 0.756 |   0.944 |

O KNN implementado manualmente teve 100% de concordância com o KNN do scikit-learn, validando a implementação hard-code. O melhor modelo por F1 foi o SVM, selecionado como modelo de produção.

Na execução dbt validada, todos os testes passaram:

```text
PASS=22 WARN=0 ERROR=0 SKIP=0 TOTAL=22
```

## Observações importantes

- O serviço AWS usado de fato na execução é o Amazon S3.
- O bucket é provisionado por CloudFormation durante `make run`.
- O bucket não é destruído automaticamente, para permitir validação no console AWS.
- Para limpar os recursos AWS, use `make destroy`.
- O arquivo `.env-aws` contém credenciais e não deve ser commitado.
