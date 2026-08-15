"""
Exporta os dados agregados dos marts para alimentar o dashboard.

O Metabase se conecta direto ao warehouse (DuckDB/Snowflake). Este modulo exporta
um JSON consolidado usado pelo mockup estatico do dashboard
(dashboard/mockup.html) e pelas evidencias do relatorio.
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import json
import duckdb
from config.settings import DUCKDB_PATH, CURATED_DIR, EVID_DIR


def q(con, sql):
    return con.execute(sql).fetchdf()


def run():
    con = duckdb.connect(str(DUCKDB_PATH))
    A = "analytics"  # schema final do dbt

    kpis = q(con, f"""
        select
            count(*)                                  as total_chamados,
            round(avg(sla_breach)*100, 1)             as taxa_violacao_pct,
            round(avg(resolution_minutes), 1)         as tempo_medio_resolucao_min,
            round(avg(first_response_minutes), 1)     as tempo_medio_1a_resposta_min,
            round(avg(reopened)*100, 1)               as taxa_reabertura_pct,
            round(avg(csat_score), 2)                 as csat_medio
        from {A}.fct_tickets
    """).iloc[0].to_dict()

    by_cat = q(con, f"""
        select category, count(*) as chamados,
               round(avg(sla_breach)*100,1) as taxa_violacao_pct
        from {A}.fct_tickets group by 1 order by 3 desc
    """).to_dict(orient="records")

    by_pri = q(con, f"""
        select priority, count(*) as chamados,
               round(avg(sla_breach)*100,1) as taxa_violacao_pct
        from {A}.fct_tickets group by 1
        order by case priority when 'Crítica' then 1 when 'Alta' then 2
                               when 'Média' then 3 else 4 end
    """).to_dict(orient="records")

    by_channel = q(con, f"""
        select channel, count(*) as chamados,
               round(avg(sla_breach)*100,1) as taxa_violacao_pct
        from {A}.fct_tickets group by 1 order by 2 desc
    """).to_dict(orient="records")

    by_month = q(con, f"""
        select created_month as mes, count(*) as chamados,
               round(avg(sla_breach)*100,1) as taxa_violacao_pct
        from {A}.fct_tickets group by 1 order by 1
    """).to_dict(orient="records")

    risco = q(con, f"""
        select faixa_risco, count(*) as chamados
        from {A}.mart_ticket_decision
        where faixa_risco <> 'Sem score'
        group by 1
        order by case faixa_risco when 'Alto' then 1 when 'Médio' then 2 else 3 end
    """).to_dict(orient="records")

    # matriz de confusao a partir do fato de predicoes
    cm = q(con, f"""
        select sla_breach_real as real, sla_breach_previsto as previsto, count(*) as n
        from {A}.fct_predictions group by 1,2 order by 1,2
    """).to_dict(orient="records")

    # channel entra aqui para a tabela responder tambem ao filtro de canal.
    top_risco = q(con, f"""
        select ticket_id, priority, category, channel, product, customer_tier,
               round(proba_breach,3) as prob_violacao
        from {A}.mart_ticket_decision
        where faixa_risco = 'Alto'
        order by proba_breach desc limit 60
    """).to_dict(orient="records")

    # CUBO: agregados pre-somados no grao (prioridade, categoria, canal, mes).
    # Com as SOMAS — e nao as medias — o dashboard estatico consegue recalcular
    # todos os indicadores sob qualquer combinacao de filtros, sem precisar
    # carregar os 8.000 chamados linha a linha no navegador.
    cubo = q(con, f"""
        select priority, category, channel, created_month as mes,
               count(*)                          as chamados,
               sum(sla_breach)                   as violacoes,
               sum(resolution_minutes)           as soma_resolucao_min,
               sum(first_response_minutes)       as soma_1a_resposta_min,
               sum(reopened)                     as reaberturas,
               sum(coalesce(csat_score, 0))      as soma_csat,
               sum(case when csat_score is null then 0 else 1 end) as n_csat
        from {A}.fct_tickets
        group by 1, 2, 3, 4
    """).to_dict(orient="records")

    # Mesmo raciocinio para a fila por faixa de risco (conjunto de teste).
    cubo_risco = q(con, f"""
        select priority, category, channel, faixa_risco, count(*) as chamados
        from {A}.mart_ticket_decision
        where faixa_risco <> 'Sem score'
        group by 1, 2, 3, 4
    """).to_dict(orient="records")
    con.close()

    metrics = json.load(open(EVID_DIR / "metrics.json", encoding="utf-8"))

    data = {
        "kpis": kpis, "por_categoria": by_cat, "por_prioridade": by_pri,
        "por_canal": by_channel, "por_mes": by_month, "distribuicao_risco": risco,
        "matriz_confusao": cm, "top_risco": top_risco,
        "cubo": cubo, "cubo_risco": cubo_risco,
        "metricas_modelo": metrics["metricas"], "modelo_producao": metrics["modelo_producao"],
    }
    out_dir = CURATED_DIR / "dashboard"
    out_dir.mkdir(exist_ok=True)
    with open(out_dir / "dashboard_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"[dashboard] dados exportados -> {out_dir/'dashboard_data.json'}")
    print(f"[dashboard] KPIs: {kpis}")

    # Regenera o painel HTML na sequencia, para ele nunca ficar dessincronizado
    # dos dados recem-exportados.
    from src.warehouse import gerar_mockup
    gerar_mockup.run()
    return data


if __name__ == "__main__":
    run()
