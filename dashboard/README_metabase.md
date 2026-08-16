# Dashboard de Apoio a Decisao (Metabase)

O dashboard final e' construido no **Metabase**, conectado ao warehouse Postgres
que o pipeline publica (o mesmo schema `analytics` gerado pelos modelos dbt).

Ele nao e' montado a mao: o script `src/bi/metabase_setup.py` provisiona tudo pela
API — usuario administrador, conexao com o banco, os 10 cards e o painel com os
filtros. Detalhes em [`../docs/ADICOES_ENTREGA.md`](../docs/ADICOES_ENTREGA.md).

## Como subir

```bash
make run
```

Isso ja' sobe os containers, publica os dados e provisiona o painel. Ao final o
pipeline imprime a URL. Para rodar so' a parte de BI:

```bash
make stack-up   # Postgres + Metabase + Airflow
make bi         # publica no Postgres e provisiona o painel
```

| Servico  | Endereco              | Credenciais                          |
| -------- | --------------------- | ------------------------------------ |
| Metabase | http://localhost:3000 | `admin@suporte.local` / `Suporte@2026` |
| Postgres | `localhost:5433`      | `suporte` / `suporte` (base `suporte_dw`) |

> Por que Postgres e nao DuckDB: o Metabase so' le DuckDB por um plugin da
> comunidade, que quebra entre versoes. O pipeline republica a MESMA modelagem dbt
> em um Postgres, lido por driver nativo. De quebra, rodar os mesmos modelos em
> dois warehouses sem mudar uma linha de SQL comprova a portabilidade da modelagem
> para o Snowflake.

As consultas de cada card estao versionadas em `metabase_queries.sql` (referencia
para leitura; quem cria os cards de fato e' o script).

## Cards do dashboard

| Card                            | Pergunta de negocio                     | Fonte                  |
| ------------------------------- | --------------------------------------- | ---------------------- |
| Chamados no periodo             | Qual o volume?                          | `fct_tickets`          |
| Taxa de violacao de SLA (%)     | Qual o tamanho do problema?             | `fct_tickets`          |
| Tempo medio de resolucao (h)    | Quanto demoramos?                       | `fct_tickets`          |
| Violacao por prioridade         | Onde o SLA mais estoura?                | `fct_tickets`          |
| Violacao por categoria          | Que tipos de chamado sao mais criticos? | `fct_tickets`          |
| Evolucao mensal                 | A situacao esta melhorando ou piorando? | `fct_tickets`          |
| Violacao por canal              | Algum canal exige mais atencao?         | `fct_tickets`          |
| Fila priorizada por risco       | Quais chamados atacar AGORA?            | `mart_ticket_decision` |
| Distribuicao de risco           | Qual o tamanho do risco na fila?        | `mart_ticket_decision` |
| Matriz de confusao              | O modelo e' confiavel?                  | `fct_predictions`      |

## Filtros

O painel tem tres filtros — **Prioridade**, **Categoria** e **Canal** — aplicados
sobre `fct_tickets` e `mart_ticket_decision`. Sao *field filters*: cada parametro
esta ligado a coluna real da tabela, e nao a um texto solto.

Efeito medido no card "Taxa de violacao de SLA" (registro completo em
`../evidencias/metabase_dashboard.log`):

| Recorte                | Taxa de violacao |
| ---------------------- | ---------------: |
| sem filtro             |           22,8 % |
| Prioridade = Critica   |           60,4 % |
| Prioridade = Alta      |           47,3 % |
| Prioridade = Media     |           15,6 % |
| Prioridade = Baixa     |            4,8 % |

## Evidencias

- `../evidencias/metabase_dashboard.png` - painel completo, sem filtro;
- `../evidencias/metabase_dashboard_filtro.png` - o mesmo com Prioridade = Critica;
- `../evidencias/metabase_dashboard.log` - os 10 cards executados e a demonstracao
  do filtro;

## Como o dashboard apoia a decisao

O gestor do suporte usa o painel para **realocar agentes para os chamados com
maior risco previsto de violar o SLA** (card "Fila priorizada por risco"),
antes que o prazo estoure. Os cards de prioridade/categoria/canal mostram
**onde** concentrar esforco estrutural (ex.: "Solicitacao de Recurso" e "Bug /
Defeito" concentram a maior parte das violacoes), e a matriz de confusao da' ao
gestor a **confianca** necessaria para agir com base na previsao.

Os filtros transformam o painel de relatorio em ferramenta de investigacao: o
gestor recorta por prioridade para tratar a fila critica, por categoria para achar
a causa estrutural, e por canal para decidir onde reforcar a equipe.
