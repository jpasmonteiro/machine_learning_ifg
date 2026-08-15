"""
Executa o projeto dbt de forma programatica (sem depender do dbt na PATH).

`dbt build` roda os modelos (staging -> dimensoes -> fatos -> marts) e, na
sequencia, os testes de qualidade de dados.

O target sai de WAREHOUSE_TARGET (duckdb -> perfil `dev`, postgres, snowflake).
Os modelos SQL sao identicos nos tres: so' muda a conexao no profiles.yml.
"""
import os
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from config.settings import DUCKDB_PATH

DBT_DIR = str(pathlib.Path(__file__).resolve().parents[2] / "dbt")


# WAREHOUSE_TARGET -> nome do output em dbt/profiles.yml
TARGETS = {"duckdb": "dev", "postgres": "postgres", "snowflake": "snowflake"}


def run(command=None):
    os.environ["DUCKDB_PATH"] = str(DUCKDB_PATH.resolve())
    target = TARGETS.get(os.environ.get("WAREHOUSE_TARGET", "").lower(), "dev")
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
