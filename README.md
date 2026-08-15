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

- Relatório final em PDF: [relatorio/Projeto_Final.pdf](relatorio/Projeto_Final.pdf)
- Relatório editável: [relatorio/Relatorio_Projeto_Final.docx](relatorio/Relatorio_Projeto_Final.docx)
- Apresentação: [apresentacao/Apresentacao_Projeto_Final.pptx](apresentacao/Apresentacao_Projeto_Final.pptx)
- Código executável e dados de entrada na raiz do repositório
- Dashboard local: [dashboard/mockup.html](dashboard/mockup.html)

## Estrutura principal

```text
.
├── README.md                         # guia principal da entrega
├── Makefile                          # comandos make env, make run e make destroy
├── .env-aws.example                  # modelo de credenciais AWS
├── requirements.txt                  # dependências Python
├── run_pipeline.py                   # orquestrador principal
├── data/
│   ├── raw/                          # dados brutos já materializados
│   ├── processed/                    # saídas processadas/features
│   └── curated/                      # warehouse DuckDB e dados do dashboard
├── src/                              # código-fonte Python
├── config/                           # configurações do projeto
├── dbt/                              # modelos e testes dbt
├── dashboard/                        # mockup HTML e consultas Metabase
├── infra/                            # CloudFormation, custos e diagrama AWS
├── evidencias/                       # métricas, matriz de confusão, ROC e dashboard
├── relatorio/                        # relatório final
├── apresentacao/                     # slides da apresentação
└── airflow/                          # DAG de referência do Airflow
```

## Visão geral da solução

Fluxo principal:

```text
dados raw -> processamento/features -> machine learning -> warehouse DuckDB -> dbt -> dashboard -> S3
```

O projeto inclui:

- Dados brutos já materializados em `data/raw/`.
- Três fontes: estruturada (`tickets.csv`), não estruturada (`ticket_messages.jsonl`) e semiestruturada (`ticket_events.json`).
- Processamento e extração de atributos de negócio, texto e logs.
- Modelos de classificação: baseline, KNN hard-code, KNN scikit-learn, SVM e MLP.
- Warehouse local em DuckDB como proxy de Snowflake.
- Modelagem dbt com staging, dimensões, fatos, mart de ML, mart de decisão e testes.
- Provisionamento obrigatório de bucket Amazon S3 via CloudFormation.
- Upload das camadas `raw`, `processed` e `curated` para o S3.
- Dashboard em mockup HTML e consultas para Metabase.

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
9. Exporta dados para o dashboard.
10. Envia as camadas `raw`, `processed` e `curated` para o S3.

Ao final, os recursos AWS permanecem ativos para validação no console. Para remover tudo depois da validação:

```bash
make destroy
```

O `make destroy` esvazia o bucket S3 e remove a stack CloudFormation.

## Dados de entrada

Os dados de entrada já estão versionados em:

```text
data/raw/tickets.csv
data/raw/ticket_messages.jsonl
data/raw/ticket_events.json
```

Eles foram gerados uma única vez pelo script sintético do projeto, com semente fixa, e não são recriados durante a execução principal. O script de geração permanece no repositório apenas para rastreabilidade.

## Saídas geradas

Após `make run`, as principais saídas ficam em:

```text
data/processed/
data/curated/warehouse.duckdb
data/curated/dashboard/dashboard_data.json
evidencias/metrics.json
evidencias/matriz_confusao.png
evidencias/curva_roc.png
evidencias/dashboard_mockup.png
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

### Abrir o dashboard rapidamente

Depois de rodar `make run`, abra este arquivo no navegador:

[dashboard/mockup.html](dashboard/mockup.html)

Esse mockup usa os dados exportados em:

```text
data/curated/dashboard/dashboard_data.json
```

### Dashboard em Metabase

As consultas SQL dos cards estão em:

[dashboard/metabase_queries.sql](dashboard/metabase_queries.sql)

O guia específico do Metabase está em:

[dashboard/README_metabase.md](dashboard/README_metabase.md)

Em produção, o Metabase poderia se conectar ao warehouse analítico. Na entrega local, o mockup HTML é a forma mais simples de visualizar o resultado sem instalar ferramenta adicional.

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
