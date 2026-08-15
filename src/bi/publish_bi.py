# -*- coding: utf-8 -*-
"""
Publica a camada analitica no Postgres, que e' a fonte lida pelo Metabase.

POR QUE ESTA ETAPA EXISTE
O warehouse padrao da execucao local e' o DuckDB, um arquivo — e o Metabase nao
tem driver nativo para ele (so' um plugin da comunidade). Em vez de depender
desse plugin, o projeto republica a MESMA modelagem em um Postgres de verdade,
que o Metabase le por driver nativo.

O ganho vai alem do dashboard: rodar os mesmos modelos dbt em dois warehouses
diferentes, sem alterar uma linha de SQL, e' a evidencia pratica de que a
modelagem e' portavel para o Snowflake (o terceiro target do profiles.yml).

O que roda aqui:
    1. carga das tabelas tratadas em raw.*        (WAREHOUSE_TARGET=postgres)
    2. dbt build: staging -> dims -> fatos + testes

Uso:
    python -m src.bi.publish_bi
"""
import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))


def postgres_disponivel():
    """Testa a conexao antes de tentar a carga, para dar um erro legivel."""
    from sqlalchemy import create_engine, text
    from src.warehouse.load_warehouse import postgres_url
    try:
        engine = create_engine(postgres_url(), connect_args={"connect_timeout": 5})
        with engine.connect() as con:
            con.execute(text("select 1"))
        return True
    except Exception as exc:
        print(f"[bi] Postgres indisponivel: {type(exc).__name__}")
        print(f"[bi] {str(exc).splitlines()[0][:160]}")
        return False


def run():
    from src.warehouse import load_warehouse, run_dbt

    if not postgres_disponivel():
        raise SystemExit(
            "[bi] Nao foi possivel conectar no Postgres do warehouse.\n"
            "[bi] Suba os containers antes: make stack-up")

    anterior = os.environ.get("WAREHOUSE_TARGET")
    os.environ["WAREHOUSE_TARGET"] = "postgres"
    try:
        print("[bi] 1/2 carga das tabelas tratadas em raw.*")
        load_warehouse.run()
        print("[bi] 2/2 dbt build no target postgres (modelos + testes)")
        run_dbt.run()
    finally:
        # Nao contamina as etapas seguintes do pipeline, que usam DuckDB.
        if anterior is None:
            os.environ.pop("WAREHOUSE_TARGET", None)
        else:
            os.environ["WAREHOUSE_TARGET"] = anterior

    print("[bi] schema analytics publicado no Postgres (pronto para o Metabase)")
    return {"target": "postgres"}


if __name__ == "__main__":
    run()
