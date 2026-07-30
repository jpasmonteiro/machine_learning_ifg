-- Fato central: um registro por chamado, com medidas e atributos integrados
-- das tres fontes (estruturada, textual e logs).
with t as (select * from {{ ref('stg_tickets') }}),
     x as (select * from {{ ref('stg_text_features') }}),
     l as (select * from {{ ref('stg_log_features') }})
select
    t.ticket_id,
    t.created_at, t.created_date, t.created_hour, t.created_weekday, t.created_month,
    t.channel, t.product, t.category, t.priority, t.customer_tier, t.region,
    t.customer_id, t.agent_id,
    -- medidas operacionais
    t.backlog_at_creation,
    t.first_response_minutes,
    t.resolution_minutes,
    t.reopened,
    t.csat_score,
    t.csat_missing,
    t.sla_minutes,
    t.sla_breach,
    -- atributos textuais
    x.body_len, x.word_count, x.num_question, x.num_exclam,
    x.upper_ratio, x.urgency_hits, x.kw_refund, x.kw_cancel, x.kw_error,
    -- atributos de logs
    l.n_events, l.n_status_changes, l.reopened_from_log
from t
left join x using (ticket_id)
left join l using (ticket_id)
