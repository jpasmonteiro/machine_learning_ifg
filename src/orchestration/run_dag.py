# -*- coding: utf-8 -*-
"""
Dispara a DAG no Airflow e gera uma evidencia legivel da execucao.

`airflow dags test` roda a DAG inteira em primeiro plano, respeitando as
dependencias entre as tasks e sem depender do scheduler — e' a forma mais direta
de produzir uma evidencia reproduzivel. A saida bruta tem milhares de linhas de
log do Airflow, entao este modulo extrai o que interessa (estado por task e as
saidas do proprio pipeline) para evidencias/airflow_dag_run.log.

Uso:
    make airflow-run
    python -m src.orchestration.run_dag
"""
import pathlib
import re
import subprocess
import sys
import time
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from config.settings import EVID_DIR

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "infra" / "docker-compose.yml"
DAG_ID = "pipeline_suporte_tecnico"

RE_ESTADO = re.compile(r"Marking task as (SUCCESS|FAILED).*?task_id=([a-z_0-9]+)")
# Linhas produzidas pelo proprio pipeline (e nao pelo Airflow) valem como saida.
RE_SAIDA = re.compile(r"INFO - (\[(?:ingestao|processing|warehouse|dashboard|bi|s3|aws|stack)\].*)")
RE_DBT = re.compile(r"INFO - .*?(Done\. PASS=\d+.*)")


def _executar(data_execucao):
    cmd = ["docker", "compose", "-f", str(COMPOSE), "exec", "-T", "airflow",
           "airflow", "dags", "test", DAG_ID, data_execucao]
    print(f"[dag] {' '.join(cmd[-4:])}")
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=1800)
    return proc.stdout + proc.stderr, proc.returncode


def run(data_execucao=None):
    data_execucao = data_execucao or date.today().isoformat()
    bruto, codigo = _executar(data_execucao)

    # Estado final de cada task, na ordem em que o Airflow as concluiu.
    estados, vistos = [], set()
    for estado, task in RE_ESTADO.findall(bruto):
        if task not in vistos:
            vistos.add(task)
            estados.append((task, estado))

    saidas, vistas = [], set()
    for linha in RE_SAIDA.findall(bruto) + [m for m in RE_DBT.findall(bruto)]:
        limpa = linha.strip()
        if limpa not in vistas:
            vistas.add(limpa)
            saidas.append(limpa)

    ok = codigo == 0 and all(e == "SUCCESS" for _, e in estados) and estados
    linhas = [
        "EVIDENCIA DE EXECUCAO - DAG DO AIRFLOW",
        "=" * 66,
        f"DAG........: {DAG_ID} (schedule @daily, {len(estados)} tasks)",
        "Airflow....: 2.10.5  |  operador: BashOperator (isolamento por processo)",
        f"Executado..: {time.strftime('%Y-%m-%d %H:%M')}",
        f"Comando....: airflow dags test {DAG_ID} {data_execucao}",
        "Interface..: http://localhost:8081  (usuario airflow / senha airflow)",
        "Ambiente...: container suporte-airflow (infra/docker-compose.yml)",
        "",
        "RESULTADO POR TASK (ordem de dependencia)",
        "-" * 66,
    ]
    linhas += [f"  {i}. {task:<26} {estado}" for i, (task, estado) in enumerate(estados, 1)]
    linhas += ["", f"ESTADO FINAL: {'SUCCESS' if ok else 'FAILED'}  "
                   f"({sum(1 for _, e in estados if e == 'SUCCESS')}/{len(estados)} tasks)",
               "", "SAIDAS DO PIPELINE", "-" * 66]
    linhas += [f"  {s}" for s in saidas]
    linhas.append("")

    destino = EVID_DIR / "airflow_dag_run.log"
    destino.write_text("\n".join(linhas), encoding="utf-8")

    for task, estado in estados:
        print(f"  {task:<26} {estado}")
    print(f"[dag] estado final: {'SUCCESS' if ok else 'FAILED'}")
    print(f"[dag] evidencia -> {destino}")
    if not ok:
        # Guarda o log completo ao lado para diagnostico, sem poluir a evidencia.
        (EVID_DIR / "airflow_dag_run.full.log").write_text(bruto, encoding="utf-8")
        raise SystemExit("[dag] a DAG falhou; log completo em "
                         "evidencias/airflow_dag_run.full.log")
    return {"tasks": estados, "evidencia": str(destino)}


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
