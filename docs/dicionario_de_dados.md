# Dicionário de dados

Documentação da origem, formato, campos e limitações dos dados (item 4.2.1).

> **Origem:** dados sintéticos gerados por `src/ingestion/generate_data.py` (semente fixa = 42),
> com esquema espelhando o *Customer Support Ticket Dataset*. Para usar dados reais, substitua os
> arquivos em `data/raw/` mantendo os mesmos nomes de campos.

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
| csat_score | inteiro (1-5) | Satisfação; **ausente em ~40%** (desfecho - não usar como atributo) |

## 2. ticket_messages.jsonl (não estruturado)

Uma linha JSON por chamado: `ticket_id`, `subject`, `body` (texto livre do cliente),
`agent_note`, `lang`.

## 3. ticket_events.json (semiestruturado)

Lista de objetos `{ ticket_id, events: [...] }`. Cada evento contém `ts`, `event`
(created, first_response, reopened, resolved), `actor`, `from_status`, `to_status`.

## Variável-alvo

`sla_breach` (binária): 1 se `resolution_minutes` ultrapassou o SLA da prioridade.
SLA de resolução: Crítica 240 min, Alta 480 min, Média 1440 min, Baixa 2880 min.

## Tabela analítica para ML (mart_ml_features)

Contém apenas atributos conhecidos no momento da decisão (logo após a 1ª resposta) mais o alvo.
Inclui os campos estruturados (exceto desfechos), os atributos de texto (body_len, word_count,
num_question, num_exclam, upper_ratio, urgency_hits, kw_refund, kw_cancel, kw_error) e os de logs
(n_events, n_status_changes, reopened_from_log).

## Limitações

- Dados sintéticos: não capturam ruído de textos reais (gírias, erros de digitação, idiomas).
- `csat_score` ausente em parte dos registros (clientes que não avaliaram).
- `first_response_minutes` só está disponível após a primeira resposta, coerente com o ponto de
  decisão adotado.
