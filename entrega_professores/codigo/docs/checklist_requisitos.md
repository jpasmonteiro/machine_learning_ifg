# Checklist de requisitos (enunciado x entregue)

## 3. Organização e regras

- [X] Entrega: repositório + apresentação + relatório
- [X] Tecnologias: AWS (S3 + CloudFormation), Snowflake (profile dbt; DuckDB como proxy local), dbt, Airflow (DAG), Python
- [X] Dados: estruturado + não estruturado + semiestruturado (3 fontes)
- [X] Reprodutibilidade: ingestão, processamento/atributos, carga, dbt, treino/aplicação, predições (run_pipeline.py)
- [X] Nuvem: ≥1 serviço AWS + template CloudFormation YAML
- [X] Visualização: dashboard (Metabase: queries + guia + mockup)
- [X] Grupo de 4 alunos: preencher nomes reais (capa do relatório/slides)

## 4. Escopo mínimo

- [X] 4.1 Definição do problema (domínio, decisor, decisão, fontes, tarefa, resultado)
- [X] 4.2 Datasets + documentação (dicionario_de_dados.md)
- [X] 4.3 Processamento e extração de atributos (estruturado + texto + logs)
- [X] 4.4 ELT: DAG Airflow, carga, dbt staging/dims/facts, **10 testes** (mín. 2), docs, tabela ML + fatos
- [X] 4.5 Nuvem: S3 em camadas, documentação, diagrama 100% AWS, custos
- [X] 4.6 ML: tarefa, preparação, baseline, **hard-code**, **biblioteca**, comparação, métricas, predições
- [X] 4.7 Visualização: indicadores, dados tratados, resultados do modelo, filtros, apoio à decisão

## 5. Avaliação

- [X] 5.1 Conjunto de avaliação (teste com 2.000 chamados, fora da amostra)
- [X] 5.2 Métricas de classificação (accuracy, precision, recall, F1, matriz de confusão, ROC-AUC)
- [X] 5.3 Avaliação do pipeline (execução, qualidade, testes dbt, rastreabilidade)
- [X] 5.4 Avaliação qualitativa (acertos, erros, causas, limitações, riscos, melhorias)

## 6/7. Entregáveis

- [X] 7.1 Repositório (README, scripts, DAGs, dbt, código ML, instruções, CloudFormation, evidências)
- [X] 7.2 Apresentação (.pptx)
- [X] 7.3 Relatório (.docx)