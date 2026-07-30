# Checklist de requisitos (enunciado x entregue)

## 3. Organização e regras
- [x] Entrega: repositório + apresentação + relatório
- [x] Tecnologias: AWS (S3 + CloudFormation), Snowflake (profile dbt; DuckDB como proxy local), dbt, Airflow (DAG), Python
- [x] Dados: estruturado + não estruturado + semiestruturado (3 fontes)
- [x] Reprodutibilidade: ingestão, processamento/atributos, carga, dbt, treino/aplicação, predições (run_pipeline.py)
- [x] Nuvem: ≥1 serviço AWS + template CloudFormation YAML
- [x] Visualização: dashboard (Metabase: queries + guia + mockup)
- [ ] Grupo de 4 alunos: preencher nomes reais (capa do relatório/slides)

## 4. Escopo mínimo
- [x] 4.1 Definição do problema (domínio, decisor, decisão, fontes, tarefa, resultado)
- [x] 4.2 Datasets + documentação (dicionario_de_dados.md)
- [x] 4.3 Processamento e extração de atributos (estruturado + texto + logs)
- [x] 4.4 ELT: DAG Airflow, carga, dbt staging/dims/facts, **10 testes** (mín. 2), docs, tabela ML + fatos
- [x] 4.5 Nuvem: S3 em camadas, documentação, diagrama 100% AWS, custos
- [x] 4.6 ML: tarefa, preparação, baseline, **hard-code**, **biblioteca**, comparação, métricas, predições
- [x] 4.7 Visualização: indicadores, dados tratados, resultados do modelo, filtros, apoio à decisão

## 5. Avaliação
- [x] 5.1 Conjunto de avaliação (teste com 2.000 chamados, fora da amostra)
- [x] 5.2 Métricas de classificação (accuracy, precision, recall, F1, matriz de confusão, ROC-AUC)
- [x] 5.3 Avaliação do pipeline (execução, qualidade, testes dbt, rastreabilidade)
- [x] 5.4 Avaliação qualitativa (acertos, erros, causas, limitações, riscos, melhorias)

## 6/7. Entregáveis
- [x] 7.1 Repositório (README, scripts, DAGs, dbt, código ML, instruções, CloudFormation, evidências)
- [x] 7.2 Apresentação (.pptx)
- [x] 7.3 Relatório (.docx)

## Itens que dependem do grupo (ação de vocês)
1. Preencher os nomes reais dos 4 integrantes (capa do relatório e slide 1).
2. (Opcional p/ nota máxima) Subir o Metabase via Docker e montar o dashboard com as queries prontas.
3. (Opcional) Conectar Snowflake/AWS reais usando os profiles e o template já preparados.
4. Cada integrante deve entender as etapas para a apresentação (todos participam).
