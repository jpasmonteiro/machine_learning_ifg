# Dicionário de dados

Documentação da origem, formato, campos e limitações dos dados usados no projeto.

## Origem dos dados

A base de entrada está versionada em `data/raw/` e representa registros históricos de uma operação de suporte técnico. Os arquivos foram disponibilizados junto com a entrega para garantir reprodutibilidade da execução, sem depender de sistemas externos ou integrações adicionais no momento da avaliação.

A base reúne três fontes complementares:

- `tickets.csv`: dados tabulares dos chamados.
- `ticket_messages.jsonl`: textos associados aos chamados.
- `ticket_events.json`: eventos de ciclo de vida dos chamados.

## 1. tickets.csv (estruturado)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| ticket_id | texto | Identificador único do chamado (ex.: TCK-000001) |
| created_at | timestamp | Data/hora de abertura |
| channel | categórico | Canal: Email, Chat, Telefone, Formulário Web, Redes Sociais |
| product | categórico | Produto relacionado |
| category | categórico | Categoria do chamado (7 valores) |
| priority | categórico | Baixa, Média, Alta, Crítica |
| customer_tier | categórico | Free, Basic, Premium, Enterprise |
| customer_id | texto | Identificador do cliente |
| agent_id | texto | Identificador do agente |
| region | categórico | Região do cliente |
| backlog_at_creation | inteiro | Tamanho da fila no momento da abertura |
| first_response_minutes | numérico | Minutos até a primeira resposta |
| resolution_minutes | numérico | Minutos até a resolução (**desfecho** - não usar como atributo) |
| reopened | binário | 1 se o chamado foi reaberto |
| csat_score | inteiro (1-5) | Satisfação; ausente em parte dos registros (desfecho - não usar como atributo) |

## 2. ticket_messages.jsonl (não estruturado)

Uma linha JSON por chamado, com os seguintes campos:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| ticket_id | texto | Identificador do chamado, usado para cruzamento com `tickets.csv` |
| subject | texto | Assunto do chamado |
| body | texto | Mensagem do cliente |
| agent_note | texto | Nota operacional associada ao atendimento |
| lang | texto | Idioma do texto |

## 3. ticket_events.json (semiestruturado)

Lista de objetos no formato `{ ticket_id, events: [...] }`. Cada evento contém:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| ts | timestamp | Data/hora do evento |
| event | texto | Evento registrado: created, first_response, reopened ou resolved |
| actor | texto | Ator responsável pelo evento |
| from_status | texto/nulo | Status anterior |
| to_status | texto | Novo status |

## Variável-alvo

`sla_breach` (binária): indica se o tempo de resolução (`resolution_minutes`) ultrapassou o SLA definido para a prioridade do chamado.

| Prioridade | SLA de resolução |
|------------|-----------------:|
| Crítica | 240 min |
| Alta | 480 min |
| Média | 1440 min |
| Baixa | 2880 min |

## Tabela analítica para ML

A tabela `mart_ml_features` contém apenas atributos conhecidos no momento da decisão, logo após a primeira resposta do agente, além da variável-alvo.

Principais grupos de atributos:

- Dados do chamado: canal, produto, categoria, prioridade, faixa do cliente, região, fila no momento da abertura e primeira resposta.
- Atributos de texto: `body_len`, `word_count`, `num_question`, `num_exclam`, `upper_ratio`, `urgency_hits`, `kw_refund`, `kw_cancel`, `kw_error`.
- Atributos de eventos: `n_events`, `n_status_changes`, `reopened_from_log`.

Campos como `resolution_minutes` e `csat_score` são tratados como desfechos e não entram como atributos do modelo, evitando vazamento de informação.

## Limitações

- A base entregue é um recorte fechado para fins de modelagem e reprodução do pipeline.
- Os resultados devem ser reavaliados antes de qualquer uso produtivo em uma operação real.
- `csat_score` está ausente em parte dos registros, pois nem todos os clientes registram avaliação.
- `first_response_minutes` só está disponível após a primeira resposta, coerente com o ponto de decisão adotado.
