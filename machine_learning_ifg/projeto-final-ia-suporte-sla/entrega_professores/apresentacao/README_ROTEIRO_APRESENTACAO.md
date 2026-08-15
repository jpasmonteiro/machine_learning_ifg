# Storytelling e roteiro da apresentação gravada

## Ideia central

O projeto responde a uma dor operacional simples: em uma fila de suporte, nem todo chamado tem o
mesmo risco. Se o gestor souber antes quais chamados têm maior chance de violar o SLA, ele pode
priorizar atendimento, redistribuir agentes e agir antes que o problema vire atraso.

Frase-chave:

> Nosso objetivo não é só prever uma métrica; é transformar dados do suporte em uma fila de decisão.

## Estrutura sugerida da gravação

Tempo recomendado: 8 a 12 minutos.

### 1. Abertura - problema e decisão

Fala sugerida:

> Este trabalho integra dados, nuvem, modelagem e aprendizagem de máquina para resolver um problema
> de suporte técnico: prever quais chamados têm maior risco de violar o SLA de resolução. A decisão
> apoiada pelo modelo é direta: quais chamados o gestor deve priorizar agora.

Pontos para mostrar:

- Tema do projeto.
- Variável-alvo: `sla_breach`.
- Decisor: gestor/coordenador de suporte.
- Ação: priorizar fila e realocar agentes.

Frases-chave:

- "O SLA é um compromisso operacional, não apenas um indicador."
- "A previsão só tem valor se ajudar alguém a decidir antes do atraso acontecer."

### 2. Fontes de dados e variável-alvo

Fala sugerida:

> Trabalhamos com três tipos de fonte. A primeira é estruturada, com informações do ticket como
> prioridade, canal e produto. A segunda é não estruturada, com textos do cliente e anotações. A
> terceira é semiestruturada, com logs de eventos do chamado. A partir do tempo de resolução e da
> regra de SLA por prioridade, criamos a variável-alvo binária: violou ou não violou o SLA.

Pontos para mostrar:

- `docs/dicionario_de_dados.md`.
- `src/ingestion/generate_data.py`.
- Regras de SLA: Crítica 240 min, Alta 480 min, Média 1440 min, Baixa 2880 min.

Frase-chave:

> Unimos sinais de cadastro, texto e histórico de eventos para representar melhor o risco do chamado.

### 3. Pipeline de dados

Fala sugerida:

> A solução foi construída como um pipeline reprodutível. Primeiro geramos ou ingerimos os dados,
> depois extraímos atributos, treinamos e avaliamos os modelos, carregamos o warehouse, executamos o
> dbt e exportamos os dados para o dashboard.

Sequência técnica:

1. `src/ingestion`: ingestão dos dados.
2. `src/processing`: criação de atributos.
3. `src/ml`: treino e avaliação.
4. `src/warehouse`: carga no DuckDB/Snowflake e execução dbt.
5. `dashboard`: consultas e painel.
6. `airflow/dags`: DAG de orquestração.

Frase-chave:

> O `run_pipeline.py` é o ponto único de reprodutibilidade do projeto.

### 4. Modelagem dbt e warehouse

Fala sugerida:

> No warehouse, usamos DuckDB localmente como proxy do Snowflake. A camada dbt organiza os dados em
> staging, dimensões, fatos e marts. Isso separa dado bruto de dado analítico e permite testes de
> qualidade no pipeline.

Pontos para mostrar:

- `dbt/models/staging`.
- `dbt/models/marts`.
- `mart_ml_features`.
- `mart_ticket_decision`.

Frases-chave:

- "O dbt documenta e testa as transformações."
- "O mart de decisão aproxima o modelo do uso real pelo gestor."

### 5. Aprendizagem de máquina

Fala sugerida:

> A tarefa de ML é uma classificação binária. Comparamos baselines, KNN implementado manualmente,
> KNN com scikit-learn, SVM e MLP. O KNN hard-code teve exatamente o mesmo resultado do KNN da
> biblioteca, o que valida a implementação manual. O melhor modelo final foi o SVM, com F1 de 0.765
> e ROC-AUC de 0.953.

Métricas para citar:

- Treino: 6.000 chamados.
- Teste: 2.000 chamados.
- Atributos: 49.
- Prevalência de violação no teste: 22,8%.
- SVM: accuracy 0.903, precision 0.854, recall 0.693, F1 0.765, ROC-AUC 0.953.
- MLP: F1 0.756, recall 0.765.
- KNN hard-code e KNN scikit-learn: concordância de 100%.

Frases-chave:

- "O baseline majoritário parece ter boa acurácia, mas não encontra nenhum chamado crítico."
- "Por isso olhamos precision, recall, F1 e ROC-AUC, não apenas accuracy."
- "O SVM foi escolhido pelo melhor equilíbrio geral, especialmente no F1."

### 6. Dashboard e uso pelo gestor

Fala sugerida:

> O dashboard fecha o ciclo. Ele mostra KPIs, violação por prioridade, categoria, canal e uma fila
> priorizada por risco. Essa fila é a tradução prática do modelo: quais chamados devem receber
> atenção primeiro.

Pontos para mostrar:

- `dashboard/mockup.html`.
- `dashboard/metabase_queries.sql`.
- `evidencias/dashboard_mockup.png`.

Frases-chave:

- "O painel transforma predição em ação."
- "A pergunta final não é qual modelo ganhou, mas que decisão melhorou."

### 7. Nuvem e arquitetura AWS

Fala sugerida:

> A validação em nuvem usa Amazon S3 para armazenar as camadas raw, processed e curated. Na execução
> da entrega, o bucket é criado obrigatoriamente por CloudFormation a partir das credenciais do
> arquivo `.env-aws`; depois a pipeline envia os dados para o S3 e remove o bucket ao final. Também
> entregamos uma arquitetura de referência 100% AWS para mostrar como a solução poderia evoluir.

Pontos para mostrar:

- `infra/arquitetura_aws.png`.
- `infra/cloudformation-s3-pipeline.yaml`.
- `.env-aws.example`.
- `src/cloud/s3_sync.py`.
- `docs/aws_academy.md`.

Frases-chave:

- "O S3 é o serviço AWS efetivamente usado na execução da entrega."
- "O CloudFormation cria e remove o bucket de forma reprodutível."
- "DuckDB é o proxy local; Snowflake é o alvo de produção previsto."
- "A arquitetura é escalável, mas a entrega continua reprodutível localmente."

### 8. Limitações e próximos passos

Fala sugerida:

> Como limitação, os dados são sintéticos, então não capturam todo o ruído de tickets reais. Em uma
> próxima etapa, usaríamos dados históricos reais, calibraríamos o limiar de risco conforme o custo
> de falso negativo e implantaríamos monitoramento de performance do modelo ao longo do tempo.

Pontos para citar:

- Dados sintéticos.
- Possível ajuste de threshold conforme operação.
- Monitoramento de drift.
- Integração real com ferramenta de chamados.
- Teste A/B ou piloto operacional com gestores.

Frase-chave:

> O próximo salto não é trocar o algoritmo; é colocar a previsão dentro do fluxo real de atendimento.

### 9. Encerramento

Fala sugerida:

> Em resumo, entregamos uma solução completa: dados de múltiplas fontes, pipeline reprodutível,
> modelagem com dbt, validação em nuvem com S3, modelos de ML comparados, implementação hard-code,
> evidências e dashboard de decisão. O resultado final é uma ferramenta para antecipar violações de
> SLA e orientar a priorização do suporte.

Frases-chave para fechar:

- "Da ingestão ao dashboard, o projeto cobre o ciclo completo de dados para decisão."
- "A entrega principal é uma fila inteligente de priorização."
- "O valor está em agir antes que o SLA seja violado."

## Divisão sugerida entre integrantes

- Integrante 1: problema, dados e variável-alvo.
- Integrante 2: pipeline, dbt, warehouse e Airflow.
- Integrante 3: modelos, métricas e comparação hard-code versus biblioteca.
- Integrante 4, se houver: nuvem, dashboard, limitações e fechamento.

Se forem três integrantes, juntar nuvem e dashboard com o fechamento.

## Checklist antes de gravar

- Atualizar o link do repositório no README principal.
- Abrir `dashboard/mockup.html` para mostrar a tela final.
- Deixar `evidencias/metrics.json`, `matriz_confusao.png` e `curva_roc.png` à mão.
- Ensaiar a transição: problema -> dados -> pipeline -> modelo -> dashboard -> nuvem -> conclusão.
- Evitar explicar código linha por linha; focar na decisão apoiada e nas evidências.
