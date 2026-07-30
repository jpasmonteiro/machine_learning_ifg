-- Fato de predicoes: junta a saida do modelo aos atributos do chamado.
select
    p.ticket_id,
    p.sla_breach_real,
    p.sla_breach_previsto,
    p.proba_breach,
    p.modelo,
    f.priority, f.category, f.product, f.customer_tier, f.channel,
    f.resolution_minutes, f.sla_minutes
from {{ ref('stg_predictions') }} p
inner join {{ ref('fct_tickets') }} f using (ticket_id)
