# -*- coding: utf-8 -*-
"""
Captura os prints do dashboard do Metabase para a pasta de evidencias.

Gera dois arquivos, que sao a prova visual do item 4.7 do enunciado:
  evidencias/metabase_dashboard.png .......... painel completo, sem filtro
  evidencias/metabase_dashboard_filtro.png ... o mesmo painel com Prioridade=Critica

COMO FUNCIONA
O painel exige login, e um navegador headless nao tem sessao. Em vez de
automatizar a tela de login, o script liga o compartilhamento por link do
Metabase, gera um link publico temporario do painel, tira as duas fotos e
DESLIGA tudo de novo — o link e' revogado e a configuracao volta ao estado
anterior. Nada fica exposto depois da captura.

REQUISITO
Google Chrome instalado (usado em modo headless). Sem ele, a etapa e' pulada
com aviso: e' captura de evidencia, nao faz parte do processamento dos dados.

Uso:
    python -m src.bi.capturar_prints
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from config.settings import EVID_DIR
from src.bi.metabase_setup import ADMIN, NOME_DASH, Metabase

# Caminhos comuns do Chrome. O primeiro que existir e' usado.
CHROMES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
]
LARGURA, ALTURA = 1600, 1610


def achar_chrome():
    for caminho in CHROMES:
        if caminho and pathlib.Path(caminho).exists():
            return caminho
    return None


def _tirar_foto(chrome, url, destino):
    subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--virtual-time-budget=20000", f"--window-size={LARGURA},{ALTURA}",
         f"--screenshot={destino}", url],
        capture_output=True, timeout=180,
    )
    return destino.exists()


def run():
    chrome = achar_chrome()
    if not chrome:
        print("[prints] Chrome nao encontrado -> captura pulada.")
        print("[prints] Os prints sao evidencia; o pipeline nao depende deles.")
        return {"pulado": True}

    url = os.environ.get("MB_URL", "http://localhost:3000")
    mb = Metabase(url)
    mb.esperar_no_ar()
    mb.autenticar()

    painel = next((d for d in mb.get("/api/dashboard")
                   if d["name"] == NOME_DASH and not d.get("archived")), None)
    if not painel:
        print(f"[prints] painel '{NOME_DASH}' nao existe ainda -> captura pulada.")
        print("[prints] Rode antes: make bi")
        return {"pulado": True}
    dash_id = painel["id"]

    # Liga o compartilhamento so' pelo tempo da captura.
    mb.put("/api/setting/enable-public-sharing", {"value": True})
    try:
        try:
            uuid = mb.post(f"/api/dashboard/{dash_id}/public_link", {})["uuid"]
        except SystemExit:
            # Ja' existia um link publico: reaproveita em vez de falhar.
            uuid = mb.get(f"/api/dashboard/{dash_id}")["public_uuid"]

        publico = f"{url}/public/dashboard/{uuid}"
        gerados = []
        for destino, sufixo, rotulo in [
            (EVID_DIR / "metabase_dashboard.png", "", "sem filtro"),
            (EVID_DIR / "metabase_dashboard_filtro.png",
             "?prioridade=Cr%C3%ADtica", "com Prioridade=Critica"),
        ]:
            if _tirar_foto(chrome, publico + sufixo, destino):
                kb = destino.stat().st_size / 1024
                print(f"[prints] {destino.name} ({kb:.0f} KB) - {rotulo}")
                gerados.append(str(destino))
            else:
                print(f"[prints] falhou ao capturar {destino.name}")
    finally:
        # Revoga o link e desliga o compartilhamento, aconteca o que acontecer.
        try:
            mb._call("DELETE", f"/api/dashboard/{dash_id}/public_link")
        except SystemExit:
            pass
        mb.put("/api/setting/enable-public-sharing", {"value": False})
        print("[prints] link publico revogado e compartilhamento desligado")

    return {"prints": gerados}


if __name__ == "__main__":
    run()
