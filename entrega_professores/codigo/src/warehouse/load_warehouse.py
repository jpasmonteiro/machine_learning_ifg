"""
Carga dos dados tratados na base analitica (camada CURATED).

Localmente usamos o DuckDB como PROXY do Snowflake: a mesma modelagem dbt roda
nos dois (basta trocar o profile). As tabelas tratadas entram no schema 'raw',
de onde o dbt monta staging -> dimensoes -> fatos.

Para usar Snowflake de verdade, defina a variavel de ambiente
WAREHOUSE_TARGET=snowflake e as credenciais SNOWFLAKE_* (ver README).
"""
import os
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import duckdb
from config.settings import PROCESSED_DIR, DUCKDB_PATH

# tabelas tratadas que sobem para o schema 'raw'
RAW_TABLES = {
    "tickets_clean": "tickets_clean.csv",
    "text_features": "text_features.csv",
    "log_features": "log_features.csv",
    "predictions": "predictions.csv",
}


def load_duckdb():
    con = duckdb.connect(str(DUCKDB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    loaded = []
    for table, fname in RAW_TABLES.items():
        path = PROCESSED_DIR / fname
        if not path.exists():
            print(f"[warehouse] aviso: {fname} ausente, pulando")
            continue
        con.execute(
            f"CREATE OR REPLACE TABLE raw.{table} AS "
            f"SELECT * FROM read_csv_auto('{path.as_posix()}', header=true);"
        )
        n = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
        loaded.append((table, n))
    con.close()
    for t, n in loaded:
        print(f"[warehouse] raw.{t}: {n} linhas")
    print(f"[warehouse] DuckDB pronto em {DUCKDB_PATH}")


def load_snowflake():
    # Caminho de nuvem (opcional). Mantido para reprodutibilidade em producao.
    import snowflake.connector  # noqa: import tardio de proposito
    from snowflake.connector.pandas_tools import write_pandas
    import pandas as pd

    con = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "SUPORTE_DW"),
        schema="RAW",
    )
    con.cursor().execute("CREATE SCHEMA IF NOT EXISTS RAW")
    for table, fname in RAW_TABLES.items():
        path = PROCESSED_DIR / fname
        if not path.exists():
            continue
        df = pd.read_csv(path)
        write_pandas(con, df, table.upper(), auto_create_table=True, overwrite=True)
        print(f"[warehouse] RAW.{table.upper()} carregada ({len(df)} linhas)")
    con.close()


def run():
    target = os.environ.get("WAREHOUSE_TARGET", "duckdb").lower()
    if target == "snowflake":
        load_snowflake()
    else:
        load_duckdb()


if __name__ == "__main__":
    run()
