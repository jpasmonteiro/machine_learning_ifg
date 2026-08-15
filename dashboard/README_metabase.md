# Dashboard de Apoio a Decisao (Metabase)

O dashboard final e' construido no **Metabase**, conectado diretamente ao
warehouse (DuckDB no ambiente local; Snowflake em producao). As consultas de
cada card estao em `metabase_queries.sql`.

Para registro e uso no relatorio/apresentacao, geramos tambem:
- `mockup.html` - versao estatica navegavel do painel (abre no navegador);
- `../evidencias/dashboard_mockup.png` - imagem do painel.

## Como subir o Metabase localmente (Docker)

```bash
# 1) Gere o warehouse rodando o pipeline (cria data/curated/warehouse.duckdb)
python run_pipeline.py

# 2) Suba o Metabase
docker run -d -p 3000:3000 --name metabase metabase/metabase

# 3) Acesse http://localhost:3000, crie o usuario admin e adicione o banco:
#    - DuckDB: use o plugin community "Metabase DuckDB driver" apontando para
#      data/curated/warehouse.duckdb (schema analytics); ou
#    - Snowflake: driver nativo, com as credenciais do projeto.

# 4) Crie os cards colando cada consulta de metabase_queries.sql e monte o
#    dashboard "Suporte - Apoio a Decisao".
```

> Observacao pratica: o driver de DuckDB no Metabase e' um plugin da comunidade.
> Em producao a conexao recomendada e' o Snowflake (driver nativo). Por isso o
> `mockup.html`/`.png` documentam o resultado de forma independente do driver.

## Cards do dashboard

| Card | Pergunta de negocio | Fonte |
|------|---------------------|-------|
| KPIs | Qual o panorama geral do suporte? | `fct_tickets` |
| Violacao por prioridade | Onde o SLA mais estoura? | `fct_tickets` |
| Violacao por categoria | Que tipos de chamado sao mais criticos? | `fct_tickets` |
| Evolucao mensal | A situacao esta melhorando ou piorando? | `fct_tickets` |
| Violacao por canal | Algum canal exige mais atencao? | `fct_tickets` |
| Fila priorizada por risco | Quais chamados atacar AGORA? | `mart_ticket_decision` |
| Distribuicao de risco | Qual o tamanho do risco na fila? | `mart_ticket_decision` |
| Matriz de confusao | O modelo e' confiavel? | `fct_predictions` |

## Filtros

O dashboard tem filtros de **prioridade**, **categoria**, **canal** e **mes**,
aplicados sobre `fct_tickets` e `mart_ticket_decision`.

## Como o dashboard apoia a decisao

O gestor do suporte usa o painel para **realocar agentes para os chamados com
maior risco previsto de violar o SLA** (card "Fila priorizada por risco"),
antes que o prazo estoure. Os cards de prioridade/categoria/canal mostram
**onde** concentrar esforco estrutural (ex.: "Solicitacao de Recurso" e "Bug /
Defeito" concentram a maior parte das violacoes), e a matriz de confusao da' ao
gestor a **confianca** necessaria para agir com base na previsao.
