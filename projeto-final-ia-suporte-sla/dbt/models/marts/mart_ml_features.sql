-- Tabela analitica consumida pelo modelo de Aprendizagem de Maquina.
-- Contem apenas atributos conhecidos no momento da decisao (sem vazamento) + alvo.
select
    ticket_id, channel, product, category, priority, customer_tier, region,
    backlog_at_creation, first_response_minutes, reopened,
    created_hour, created_weekday, created_month,
    body_len, word_count, num_question, num_exclam, upper_ratio, urgency_hits,
    kw_refund, kw_cancel, kw_error,
    n_events, n_status_changes, reopened_from_log,
    sla_breach
from {{ ref('fct_tickets') }}
