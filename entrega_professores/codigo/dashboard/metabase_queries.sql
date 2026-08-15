-- ===========================================================================
-- Consultas do dashboard (Metabase) sobre o schema analitico `analytics`.
-- Funcionam tanto no DuckDB (local) quanto no Snowflake (producao), pois o dbt
-- gera os mesmos modelos nos dois. No Metabase, cada consulta vira um "card".
-- ===========================================================================

-- [KPI] Indicadores principais ---------------------------------------------
select
    count(*)                               as chamados,
    round(avg(sla_breach) * 100, 1)        as taxa_violacao_sla_pct,
    round(avg(resolution_minutes) / 60, 1) as tempo_medio_resolucao_h,
    round(avg(first_response_minutes), 0)  as tempo_medio_1a_resposta_min,
    round(avg(csat_score), 2)              as csat_medio,
    round(avg(reopened) * 100, 1)          as taxa_reabertura_pct
from analytics.fct_tickets;

-- [Card 1] Violacao de SLA por prioridade ----------------------------------
select priority,
       count(*)                        as chamados,
       round(avg(sla_breach)*100, 1)   as taxa_violacao_pct
from analytics.fct_tickets
group by priority
order by taxa_violacao_pct desc;

-- [Card 2] Violacao de SLA por categoria -----------------------------------
select category,
       count(*)                        as chamados,
       round(avg(sla_breach)*100, 1)   as taxa_violacao_pct
from analytics.fct_tickets
group by category
order by taxa_violacao_pct desc;

-- [Card 3] Evolucao mensal -------------------------------------------------
select created_month                   as mes,
       count(*)                        as chamados,
       round(avg(sla_breach)*100, 1)   as taxa_violacao_pct
from analytics.fct_tickets
group by created_month
order by created_month;

-- [Card 4] Violacao por canal ----------------------------------------------
select channel,
       count(*)                        as chamados,
       round(avg(sla_breach)*100, 1)   as taxa_violacao_pct
from analytics.fct_tickets
group by channel
order by taxa_violacao_pct desc;

-- [Card 5] Fila priorizada por risco previsto (apoio direto a decisao) ------
-- Lista os chamados em aberto com maior probabilidade de violar o SLA.
select ticket_id, priority, category, product, customer_tier,
       round(proba_breach, 3)          as prob_violacao,
       faixa_risco
from analytics.mart_ticket_decision
where faixa_risco = 'Alto'
order by proba_breach desc
limit 50;

-- [Card 6] Distribuicao da fila por faixa de risco -------------------------
select faixa_risco, count(*) as chamados
from analytics.mart_ticket_decision
where faixa_risco <> 'Sem score'
group by faixa_risco;

-- [Card 7] Qualidade do modelo: matriz de confusao -------------------------
select sla_breach_real     as real,
       sla_breach_previsto as previsto,
       count(*)            as n
from analytics.fct_predictions
group by 1, 2
order by 1, 2;

-- [Filtro sugerido no Metabase] prioridade, categoria, canal e mes como
-- parametros do dashboard, aplicados sobre fct_tickets / mart_ticket_decision.
