# O que foi adicionado à entrega

Documento de referência das três lacunas fechadas nesta rodada: **DAG funcional no
Airflow**, **dashboard no Metabase** e **filtro analítico**. Tudo roda junto do
pipeline, sem passo manual.

| Requisito do enunciado | Antes | Agora |
|---|---|---|
| 4.4 — "DAG funcional no Airflow" | DAG existia, mas nunca executada; sem ambiente para rodá-la | Airflow em container, DAG **9/9 tasks SUCCESS**, evidência em `evidencias/airflow_dag_run.log` |
| 4.7 — "dashboard no Metabase" | HTML estático; Metabase só como sugestão em SQL | Metabase provisionado por script, 10 cards, prints em `evidencias/metabase_dashboard*.png` |
| 4.7 — "pelo menos um filtro ou recorte analítico" | Nenhum filtro | 3 filtros (Prioridade, Categoria, Canal) no Metabase **e** no painel HTML |

---

## 1. Como rodar

O comando de sempre agora faz tudo, incluindo subir os containers:

```bash
make run
```

Ao final ele imprime o endereço do painel. Serviços publicados:

| Serviço | Endereço | Credenciais |
|---|---|---|
| Metabase | http://localhost:3000 | `admin@suporte.local` / `Suporte@2026` |
| Airflow | http://localhost:8081 | `admin` / `admin` |
| Postgres | `localhost:5433` | `suporte` / `suporte` (base `suporte_dw`) |

Comandos auxiliares:

```bash
make stack-up      # sobe Postgres + Metabase + Airflow
make bi            # publica no Postgres e provisiona o painel do Metabase
make airflow-run   # executa a DAG e grava a evidência
make stack-reset   # apaga tudo e recria do zero (prova de reprodutibilidade)
make stack-down    # para os containers, preservando os dados
```

Sem Docker na máquina, `make run` **não quebra**: as duas etapas de BI são puladas
com aviso e o restante do pipeline (ingestão, ML, dbt, S3) roda normalmente. Para
pular de propósito: `SKIP_BI=1 make run`.

---

## 2. DAG funcional no Airflow

### O ambiente

`infra/docker-compose.yml` sobe o Airflow 2.10.5 com metadata DB no Postgres e a
pasta do projeto montada em `/opt/project`. A interface fica em **8081** porque a
8080 costuma estar ocupada.

**Decisão de projeto — por que `BashOperator` e não `PythonOperator`:** o Airflow
fixa versões de Jinja2 e pandas que conflitam com as do dbt-core. Instalar os dois
no mesmo ambiente quebra um ou outro. Então o código do projeto vive em um
virtualenv separado (`/opt/pipeline-venv`, criado em `infra/airflow/Dockerfile`) e
cada task o invoca como subprocesso. O scheduler apenas orquestra; o pipeline roda
exatamente com as versões do `requirements.txt`. Isso também isola falhas: uma task
que quebra não derruba o processo do scheduler.

### As 9 tasks

```
ingestao → processamento_atributos → treino_avaliacao_ml → carga_warehouse
   → dbt_build → export_dashboard → publicar_bi_postgres → dashboard_metabase
   → upload_s3
```

As duas do meio são novas e espelham as etapas 7 e 8 do `run_pipeline.py`.

A task `upload_s3` encerra com sucesso e mensagem explicativa quando não há
`.env-aws`, para a DAG poder ficar verde de ponta a ponta em uma máquina sem
credenciais AWS (`AWS_STEP_OPTIONAL=1` no compose).

### Evidência

`make airflow-run` executa `airflow dags test`, que roda a DAG inteira em primeiro
plano respeitando as dependências, e grava um resumo legível em
`evidencias/airflow_dag_run.log` — estado por task e as saídas do próprio pipeline.
Última execução: **SUCCESS (9/9 tasks)**.

---

## 3. Dashboard no Metabase

### Por que entrou um Postgres

O warehouse padrão da execução local é o DuckDB, que é um **arquivo** — e o Metabase
não tem driver nativo para ele, apenas um plugin da comunidade que costuma quebrar
entre versões. Em vez de depender desse plugin, o pipeline **republica a mesma
modelagem dbt em um Postgres**, que o Metabase lê por driver nativo.

O ganho vai além do dashboard: rodar os mesmos modelos dbt em dois warehouses
diferentes, **sem alterar uma linha de SQL**, é a evidência prática de que a
modelagem é portável para o Snowflake — o terceiro target já declarado em
`dbt/profiles.yml`.

> Essa portabilidade cobrou o preço dela na primeira execução: o modelo
> `stg_predictions` usava `cast(... as double)`, atalho que só existe no DuckDB, e
> quebrou no Postgres. Trocado por `double precision` (padrão ANSI), que funciona
> nos três bancos. É exatamente o tipo de defeito que só aparece quando se roda em
> mais de um warehouse.

### O provisionamento

`src/bi/metabase_setup.py` faz tudo pela API REST, **do zero e sem passo manual**:

1. espera o Metabase responder em `/api/health`;
2. na primeira execução cria o usuário administrador via `/api/setup`;
3. cadastra a conexão com o Postgres e aguarda o sync do schema;
4. cria os 10 cards, com os filtros ligados a colunas reais (*field filters*);
5. monta o painel "Suporte - Apoio a Decisao" mapeando os filtros aos cards;
6. executa cada card e grava `evidencias/metabase_dashboard.log`.

O script é **idempotente**: rodar de novo atualiza o que existe em vez de duplicar.

Detalhe técnico que custou caro: a partir do Metabase 0.51 é preciso enviar a query
no formato MBQL "lib" (`stages`). O formato legado ainda é aceito, mas as
*template-tags* são descartadas na conversão — e sem elas os filtros do dashboard
não têm onde se ligar.

Os metadados do Metabase ficam no Postgres (`metabase_app`), não no H2 interno do
container. Sem isso, o painel se perderia a cada `docker compose down`.

### Os 10 cards

| Card | Pergunta de negócio |
|---|---|
| Chamados no período | Qual o volume? |
| Taxa de violação de SLA (%) | Qual o tamanho do problema? |
| Tempo médio de resolução (h) | Quanto demoramos? |
| Violação por prioridade | Onde o SLA mais estoura? |
| Violação por categoria | Que tipos de chamado são críticos? |
| Evolução mensal | Está melhorando ou piorando? |
| Violação por canal | Algum canal exige mais atenção? |
| **Fila priorizada por risco** | **Quais chamados atacar agora?** |
| Distribuição por faixa de risco | Qual o tamanho do risco na fila? |
| Matriz de confusão | O modelo é confiável? |

---

## 4. O filtro

Três filtros — **Prioridade, Categoria e Canal** — presentes nos dois painéis.

### No Metabase

São *field filters*: cada parâmetro está ligado à coluna real da tabela, não a um
texto solto. No SQL usam a sintaxe de filtro opcional do Metabase:

```sql
where 1=1
  [[and {{prioridade}}]]
  [[and {{categoria}}]]
  [[and {{canal}}]]
```

Sem valor selecionado o trecho some da query; com valor, vira `and priority = ...`.

### No painel HTML

`dashboard/mockup.html` deixou de ser um print estático. O `export_dashboard.py`
passou a exportar um **cubo** com as somas pré-agregadas no grão
(prioridade, categoria, canal, mês) — 1.528 linhas. Com as *somas*, e não as médias,
o navegador recalcula todos os indicadores sob qualquer combinação de filtros, sem
carregar os 8.000 chamados linha a linha.

O Chart.js foi versionado em `dashboard/vendor/`, então o painel **abre sem
internet** — importante para a apresentação.

### Validação cruzada

O mesmo recorte foi conferido por três caminhos independentes:

| Recorte | Metabase (Postgres) | Painel HTML (cubo) | SQL direto (DuckDB) |
|---|---|---|---|
| Sem filtro | 8.000 / 22,8% | 8.000 / 22,8% | 8.000 / 22,8% |
| Prioridade = Crítica | 654 / 60,4% | 654 / 60,4% | 654 / 60,4% |
| Crítica + Bug / Defeito | — | 79 / 100% / 13,7h / CSAT 2,83 | 79 / 100% / 13,7h / CSAT 2,83 |

A demonstração por prioridade está registrada em `evidencias/metabase_dashboard.log`,
feita pelo endpoint do dashboard — ou seja, passando pelos `parameter_mappings` do
painel, e não por um parâmetro solto no SQL.

---

## 5. Arquivos

### Novos

| Arquivo | Função |
|---|---|
| `infra/docker-compose.yml` | Postgres + Metabase + Airflow |
| `infra/airflow/Dockerfile` | imagem do Airflow com venv isolado do pipeline |
| `infra/postgres-init/01-bancos-auxiliares.sql` | cria `metabase_app` e `airflow` |
| `src/bi/publish_bi.py` | republica a modelagem no Postgres |
| `src/bi/metabase_setup.py` | provisiona o painel pela API |
| `src/bi/stack.py` | sobe/confere os containers; pula com aviso sem Docker |
| `src/orchestration/run_dag.py` | dispara a DAG e gera a evidência |
| `src/warehouse/gerar_mockup.py` | gera o painel HTML com filtros |
| `src/cloud/provision_and_upload.py` | provisiona o bucket e envia, no mesmo processo |
| `dashboard/vendor/chart.umd.min.js` | Chart.js local (painel sem internet) |

### Alterados

| Arquivo | Mudança |
|---|---|
| `run_pipeline.py` | etapas 7 e 8 (Postgres e Metabase); imprime a URL do painel |
| `airflow/dags/pipeline_suporte_dag.py` | reescrita: BashOperator, 9 tasks, AWS opcional |
| `dbt/profiles.yml` | target `postgres` |
| `dbt/models/staging/stg_predictions.sql` | `double` → `double precision` (portabilidade) |
| `src/warehouse/load_warehouse.py` | `load_postgres()` |
| `src/warehouse/run_dbt.py` | mapa `WAREHOUSE_TARGET` → target do dbt |
| `src/warehouse/export_dashboard.py` | exporta o cubo e regenera o painel HTML |
| `dashboard/mockup.html` | gerado por script, com filtros funcionais |
| `Makefile` | alvos `stack-*`, `bi`, `airflow-run` |
| `requirements.txt` | `dbt-postgres`, `SQLAlchemy`, `psycopg2-binary` |

### Evidências geradas

| Arquivo | Conteúdo |
|---|---|
| `evidencias/airflow_dag_run.log` | DAG 9/9 SUCCESS, com as saídas do pipeline |
| `evidencias/metabase_dashboard.log` | 10 cards executados + demonstração do filtro |
| `evidencias/metabase_dashboard.png` | painel no Metabase, sem filtro |
| `evidencias/metabase_dashboard_filtro.png` | mesmo painel com Prioridade = Crítica |
| `evidencias/dashboard_mockup.png` | painel HTML com a barra de filtros |

---

## 6. Reprodutibilidade

A entrega foi validada do zero: `make stack-reset` apaga containers e volumes
(inclusive os metadados do Metabase) e `make bi` reconstrói tudo — usuário
administrador, conexão, cards, painel e filtros — sem intervenção manual.

Execução completa: **`make run` em ~31s**, 9/9 etapas, `dbt build` com
`PASS=22 WARN=0 ERROR=0` nos dois warehouses (DuckDB e Postgres).

---

## 7. Pontos de atenção

- **O Snowflake continua não exercitado.** O target existe em `dbt/profiles.yml` e a
  modelagem já provou ser portável (DuckDB → Postgres), mas nenhuma execução real em
  Snowflake foi feita. É a lacuna que resta do item 4.4.
- **Credenciais locais em texto claro** (`suporte/suporte`, `admin/admin`,
  `Suporte@2026`) são de desenvolvimento descartável, versionadas de propósito para o
  avaliador conseguir rodar. Não servem para nenhum ambiente real.
- **`evidencias/airflow_dag_run.log` contém o número da conta AWS** usada na execução.
  Se preferir não expor, edite a linha antes de publicar o repositório.
