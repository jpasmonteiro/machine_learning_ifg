# Custos aproximados (item 4.5 e 6.9)

## Ambiente do trabalho (o que realmente rodamos)

Para a entrega, o pipeline roda **localmente** (DuckDB como proxy do Snowflake,
Airflow/Metabase via Docker). O unico recurso de nuvem efetivamente usado e' o
**Amazon S3** para os dados brutos, dentro do **nivel gratuito** (Free Tier).

| Item | Uso | Custo no trabalho |
|------|-----|-------------------|
| Amazon S3 | < 5 GB, dentro do Free Tier (12 meses) | ~ US$ 0,00 |
| Demais componentes | executados localmente (Docker/DuckDB) | US$ 0,00 |
| **Total do trabalho** | | **~ US$ 0,00** |

## Estimativa da arquitetura equivalente 100% em AWS (producao pequena)

Valores mensais aproximados, regiao us-east-1, carga pequena (ordem de 10 mil
chamados/mes). Servem de referencia; precos reais variam.

| Servico | Configuracao assumida | Estimativa/mes (US$) |
|---------|-----------------------|----------------------|
| Amazon S3 | ~20 GB + requisicoes | 1 a 3 |
| AWS Lambda | ingestao/processamento, < 1 M invocacoes | 0 a 1 (Free Tier) |
| Amazon MWAA (Airflow) | 1 ambiente `mw1.small` | 350 a 400 |
| Snowflake | X-Small, uso intermitente (~10 h/mes) | 25 a 60 |
| Amazon SageMaker | treino esporadico + endpoint pequeno | 50 a 120 |
| EC2 (Metabase) | `t3.small` 24x7 | 15 a 20 |
| CloudWatch | logs e metricas basicas | 2 a 5 |
| Transferencia de dados | saida pequena | 1 a 5 |
| **Total aproximado** | | **~ US$ 450 a 600 / mes** |

## Observacoes de custo

- O **MWAA** e' o maior custo fixo. Para reduzir, da' para trocar por Airflow
  em um unico EC2 (`t3.medium`, ~US$ 30/mes) ou por **Step Functions** (serverless).
- O **Snowflake** cobra por tempo de computacao; com auto-suspend o custo cai bastante.
- **SageMaker** pode ser substituido por treino em Lambda/EC2 + modelo salvo no S3
  para cargas pequenas, derrubando bastante o custo.
- Versao "enxuta" (sem MWAA e sem SageMaker gerenciado): **~ US$ 70 a 120/mes**.
