-- Mart de apoio a decisao para o dashboard: chamados + risco previsto de
-- violacao de SLA, com faixa de risco para priorizacao da fila.
select
    f.*,
    p.proba_breach,
    p.sla_breach_previsto,
    case
        when p.proba_breach >= 0.7 then 'Alto'
        when p.proba_breach >= 0.4 then 'Médio'
        when p.proba_breach is not null then 'Baixo'
        else 'Sem score'
    end as faixa_risco
from {{ ref('fct_tickets') }} f
left join {{ ref('stg_predictions') }} p using (ticket_id)
