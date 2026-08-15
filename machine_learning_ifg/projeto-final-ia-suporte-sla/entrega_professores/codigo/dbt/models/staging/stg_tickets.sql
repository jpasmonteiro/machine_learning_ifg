-- Staging dos chamados: padroniza tipos e seleciona as colunas relevantes.
with src as (select * from {{ source('raw', 'tickets_clean') }})
select
    ticket_id,
    cast(created_at as timestamp)            as created_at,
    cast(created_date as date)               as created_date,
    created_hour,
    created_weekday,
    created_month,
    channel,
    product,
    category,
    priority,
    customer_tier,
    region,
    customer_id,
    agent_id,
    backlog_at_creation,
    first_response_minutes,
    resolution_minutes,
    reopened,
    csat_score,
    csat_missing,
    sla_minutes,
    sla_breach
from src
