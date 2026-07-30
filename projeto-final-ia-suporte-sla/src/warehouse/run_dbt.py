"""
Executa o projeto dbt de forma programatica (sem depender do dbt na PATH).

`dbt build` roda os modelos (staging -> dimensoes -> fatos -> marts) e, na
sequencia, os testes de qualidade de dados. Usamos o DuckDB local por padrao;
para Snowflake, exporte WAREHOUSE_TARGET/SNOWFLAKE_* e ajuste --target.
"""
import os
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from config.settings import DUCKDB_PATH

DBT_DIR = str(pathlib.Path(__file__).resolve().parents[2] / "dbt")


def run(command=None):
    os.environ["DUCKDB_PATH"] = str(DUCKDB_PATH.resolve())
    target = "snowflake" if os.environ.get("WAREHOUSE_TARGET", "").lower() == "snowflake" else "dev"
    from dbt.cli.main import dbtRunner
    runner = dbtRunner()
    args = (command or ["build"]) + ["--project-dir", DBT_DIR,
                                     "--profiles-dir", DBT_DIR, "--target", target]
    res = runner.invoke(args)
    if not res.success:
        raise SystemExit("[dbt] falhou: veja o log acima")
    print("[dbt] concluido com sucesso")
    return res


if __name__ == "__main__":
    run()
