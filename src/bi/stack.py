# -*- coding: utf-8 -*-
"""
Sobe (ou apenas confere) a stack local de BI: Postgres + Metabase + Airflow.

Chamado pelo run_pipeline.py antes das etapas de BI, para que `make run` funcione
de ponta a ponta sem nenhum comando manual: se os containers ja' estiverem no ar,
nada acontece; se nao, `docker compose up -d` os levanta.

Se o Docker nao estiver disponivel na maquina, as etapas de BI sao PULADAS com
aviso, em vez de derrubar o pipeline — o nucleo (ingestao, ML, dbt, S3) continua
reproduzivel sem Docker. Para pular de proposito, exporte SKIP_BI=1.
"""
import os
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "infra" / "docker-compose.yml"
SERVICOS = ("postgres", "metabase", "airflow")


def _docker_disponivel():
    if shutil.which("docker") is None:
        return False, "binario `docker` nao encontrado no PATH"
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=30)
        if r.returncode != 0:
            return False, "o daemon do Docker nao esta respondendo (Docker Desktop aberto?)"
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__} ao consultar o Docker"


def garantir_stack(timeout=420):
    """Garante Postgres/Metabase/Airflow no ar. Retorna True se a BI pode rodar."""
    if os.environ.get("SKIP_BI", "").strip() in {"1", "true", "True"}:
        print("[stack] SKIP_BI ativo -> etapas de BI puladas por opcao do usuario.")
        return False

    ok, motivo = _docker_disponivel()
    if not ok:
        print(f"[stack] Docker indisponivel: {motivo}.")
        print("[stack] As etapas de BI (Postgres/Metabase) serao PULADAS.")
        print("[stack] O restante do pipeline nao depende do Docker.")
        return False

    print(f"[stack] subindo servicos: {', '.join(SERVICOS)}")
    # `up -d` e' idempotente: se ja' estiverem de pe' e saudaveis, retorna na hora.
    # --wait faz o compose aguardar os healthchecks declarados no arquivo.
    cmd = ["docker", "compose", "-f", str(COMPOSE), "up", "-d", "--wait", *SERVICOS]
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"[stack] os containers nao ficaram saudaveis em {timeout}s.")
        print("[stack] Verifique com: docker compose -f infra/docker-compose.yml ps")
        return False

    if r.returncode != 0:
        print("[stack] falha ao subir a stack:")
        print((r.stderr or r.stdout).strip()[-800:])
        print("[stack] Etapas de BI puladas. Suba manualmente com: make stack-up")
        return False

    print("[stack] Postgres :5433 | Metabase :3000 | Airflow :8081 prontos")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if garantir_stack() else 1)
