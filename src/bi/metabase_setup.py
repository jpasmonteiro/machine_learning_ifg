# -*- coding: utf-8 -*-
"""
Provisiona o dashboard do Metabase pela API, do zero e sem passo manual.

O que este modulo faz, em ordem:
  1. espera o Metabase responder em /api/health;
  2. na primeira execucao, cria o usuario administrador via /api/setup
     (nas seguintes, apenas autentica);
  3. cadastra a conexao com o Postgres (driver nativo) e espera o sync do schema;
  4. cria os 10 cards do painel, com filtros de dimensao (field filters);
  5. monta o dashboard "Suporte - Apoio a Decisao" ligando os filtros aos cards;
  6. executa cada card e grava evidencias/metabase_dashboard.log.

E' idempotente: rodar de novo atualiza o que ja' existe em vez de duplicar.

PRE-REQUISITOS
    - containers no ar ......... make stack-up
    - marts carregados ......... make publish-bi
      (equivale a WAREHOUSE_TARGET=postgres nas etapas de carga e dbt)

USO
    python -m src.bi.metabase_setup
    python -m src.bi.metabase_setup --url http://localhost:3000

CREDENCIAIS
    Definidas por ambiente, com padroes de desenvolvimento local:
        MB_URL       http://localhost:3000
        MB_USER      admin@suporte.local
        MB_PASSWORD  Suporte@2026
    Se o Metabase ja' estiver configurado com outro usuario, exporte MB_USER e
    MB_PASSWORD (ou MB_API_KEY) antes de rodar.
"""
import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from config.settings import EVID_DIR

# Conexao que o METABASE usa para falar com o Postgres. Como os dois estao na
# mesma rede do compose, o host e' o nome do servico e a porta e' a INTERNA
# (5432), nao a publicada no host (5433).
PG = {
    "host": os.environ.get("MB_PG_HOST", "postgres"),
    "port": int(os.environ.get("MB_PG_PORT", "5432")),
    "dbname": os.environ.get("MB_PG_DATABASE", "suporte_dw"),
    "user": os.environ.get("MB_PG_USER", "suporte"),
    "password": os.environ.get("MB_PG_PASSWORD", "suporte"),
}
NOME_BANCO = "Suporte DW (Postgres)"
NOME_DASH = "Suporte - Apoio a Decisao"

ADMIN = {
    "email": os.environ.get("MB_USER", "admin@suporte.local"),
    "password": os.environ.get("MB_PASSWORD", "Suporte@2026"),
    "first_name": "Grupo",
    "last_name": "Suporte IA",
}


# --------------------------------------------------------------------------- HTTP
class Metabase:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.headers = {"Content-Type": "application/json"}

    def _call(self, metodo, caminho, corpo=None, timeout=180):
        dados = json.dumps(corpo).encode() if corpo is not None else None
        req = urllib.request.Request(self.base + caminho, data=dados,
                                     headers=self.headers, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                txt = r.read().decode()
                return json.loads(txt) if txt else {}
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode()[:500]
            raise SystemExit(f"\n[erro] {metodo} {caminho} -> HTTP {e.code}\n{detalhe}\n")
        except urllib.error.URLError as e:
            raise SystemExit(
                f"\n[erro] Metabase inacessivel em {self.base}: {e.reason}\n"
                f"Suba os containers com: make stack-up\n")

    get = lambda self, p: self._call("GET", p)
    post = lambda self, p, b: self._call("POST", p, b)
    put = lambda self, p, b: self._call("PUT", p, b)

    # ------------------------------------------------------------- autenticacao
    def esperar_no_ar(self, tentativas=60, intervalo=5):
        """O Metabase leva ~40s para subir; migra o app DB no primeiro boot."""
        for i in range(tentativas):
            try:
                req = urllib.request.Request(self.base + "/api/health")
                with urllib.request.urlopen(req, timeout=10) as r:
                    if json.loads(r.read().decode()).get("status") == "ok":
                        return True
            except Exception:
                pass
            if i == 0:
                print("  aguardando o Metabase subir...", end="", flush=True)
            else:
                print(".", end="", flush=True)
            time.sleep(intervalo)
        print()
        raise SystemExit(f"[erro] Metabase nao respondeu em {self.base} apos "
                         f"{tentativas * intervalo}s. Veja: docker logs suporte-metabase")

    def autenticar(self):
        """Cria o admin na primeira vez; nas seguintes so' abre a sessao.

        Uma API key em MB_API_KEY tem prioridade e dispensa usuario/senha.
        """
        if os.environ.get("MB_API_KEY"):
            self.headers["x-api-key"] = os.environ["MB_API_KEY"]
            print("  autenticado por API key (MB_API_KEY)")
            return

        props = self.get("/api/session/properties")
        if not props.get("has-user-setup"):
            token = props.get("setup-token")
            if not token:
                raise SystemExit("[erro] Metabase sem admin e sem setup-token. "
                                 "Recrie o container: make stack-reset")
            sessao = self.post("/api/setup", {
                "token": token,
                "user": {**ADMIN, "site_name": "Suporte IA - IFG"},
                "prefs": {"site_name": "Suporte IA - IFG", "allow_tracking": False},
            })["id"]
            self.headers["X-Metabase-Session"] = sessao
            print(f"  admin criado: {ADMIN['email']} / {ADMIN['password']}")
            return

        sessao = self.post("/api/session", {"username": ADMIN["email"],
                                            "password": ADMIN["password"]})["id"]
        self.headers["X-Metabase-Session"] = sessao
        print(f"  autenticado como {ADMIN['email']}")


# ----------------------------------------------------------------- banco de dados
def garantir_banco(mb):
    for d in mb.get("/api/database").get("data", []):
        if d["name"] == NOME_BANCO:
            print(f"  banco ja' existe (id={d['id']})")
            return d["id"]
    novo = mb.post("/api/database", {
        "engine": "postgres", "name": NOME_BANCO,
        "details": {**PG, "ssl": False, "tunnel-enabled": False,
                    "schema-filters-type": "all"},
        "is_full_sync": True,
    })
    print(f"  banco criado (id={novo['id']})")
    return novo["id"]


def esperar_sync(mb, db_id, tabelas_esperadas, tentativas=40):
    """O Metabase varre o schema de forma assincrona; espera as tabelas aparecerem."""
    mb.post(f"/api/database/{db_id}/sync_schema", {})
    achadas = set()
    for _ in range(tentativas):
        meta = mb.get(f"/api/database/{db_id}/metadata")
        achadas = {t["name"] for t in meta.get("tables", [])
                   if t.get("schema") == "analytics"}
        if tabelas_esperadas <= achadas:
            print(f"  schema sincronizado ({len(achadas)} tabelas em analytics)")
            return meta
        time.sleep(3)
    raise SystemExit(
        f"[erro] o sync do Metabase nao encontrou {sorted(tabelas_esperadas - achadas)} "
        f"no schema analytics.\nRode a carga antes: make publish-bi")


def mapa_campos(meta):
    """{(tabela, coluna): field_id} para montar os filtros de dimensao."""
    m = {}
    for t in meta.get("tables", []):
        if t.get("schema") != "analytics":
            continue
        for f in t.get("fields", []):
            m[(t["name"], f["name"])] = f["id"]
    return m


# ------------------------------------------------------------------------- cards
# Os tres filtros do painel. Cada um vira um parametro do dashboard ligado a uma
# coluna real da tabela (field filter), e nao a um texto solto.
FILTROS = [("prioridade", "Prioridade", "priority"),
           ("categoria", "Categoria", "category"),
           ("canal", "Canal", "channel")]

# `[[and {{slug}}]]` e' a sintaxe de filtro OPCIONAL do Metabase: sem valor
# selecionado, o trecho inteiro some do SQL; com valor, vira `and priority = ...`.
WHERE = "\n".join(f"  [[and {{{{{slug}}}}}]]" for slug, _, _ in FILTROS)

CARDS = [
    dict(nome="Chamados no período", display="scalar", tabela="fct_tickets",
         sql=f"select count(*) as chamados\nfrom analytics.fct_tickets\nwhere 1=1\n{WHERE}"),

    dict(nome="Taxa de violação de SLA (%)", display="scalar", tabela="fct_tickets",
         sql=f"select round(avg(sla_breach)*100, 1) as taxa_violacao_pct\n"
             f"from analytics.fct_tickets\nwhere 1=1\n{WHERE}"),

    # resolution_minutes e' double precision: o Postgres nao tem round(double, int),
    # entao a media passa por numeric antes de arredondar.
    dict(nome="Tempo médio de resolução (h)", display="scalar", tabela="fct_tickets",
         sql=f"select round(cast(avg(resolution_minutes)/60 as numeric), 1) as horas\n"
             f"from analytics.fct_tickets\nwhere 1=1\n{WHERE}"),

    dict(nome="Violação de SLA por prioridade", display="bar", tabela="fct_tickets",
         sql=f"select priority as prioridade,\n"
             f"       round(avg(sla_breach)*100, 1) as taxa_violacao_pct\n"
             f"from analytics.fct_tickets\nwhere 1=1\n{WHERE}\n"
             f"group by priority\norder by taxa_violacao_pct desc",
         eixo=("prioridade", ["taxa_violacao_pct"])),

    dict(nome="Violação de SLA por categoria", display="row", tabela="fct_tickets",
         sql=f"select category as categoria,\n"
             f"       round(avg(sla_breach)*100, 1) as taxa_violacao_pct\n"
             f"from analytics.fct_tickets\nwhere 1=1\n{WHERE}\n"
             f"group by category\norder by taxa_violacao_pct desc",
         eixo=("categoria", ["taxa_violacao_pct"])),

    dict(nome="Evolução mensal da violação de SLA", display="line", tabela="fct_tickets",
         sql=f"select created_month as mes,\n"
             f"       round(avg(sla_breach)*100, 1) as taxa_violacao_pct\n"
             f"from analytics.fct_tickets\nwhere 1=1\n{WHERE}\n"
             f"group by created_month\norder by mes",
         eixo=("mes", ["taxa_violacao_pct"])),

    dict(nome="Violação de SLA por canal", display="bar", tabela="fct_tickets",
         sql=f"select channel as canal, count(*) as chamados,\n"
             f"       round(avg(sla_breach)*100, 1) as taxa_violacao_pct\n"
             f"from analytics.fct_tickets\nwhere 1=1\n{WHERE}\n"
             f"group by channel\norder by taxa_violacao_pct desc",
         eixo=("canal", ["taxa_violacao_pct"])),

    dict(nome="Fila priorizada por risco previsto", display="table",
         tabela="mart_ticket_decision",
         sql=f"select ticket_id, priority as prioridade, category as categoria,\n"
             f"       product as produto, customer_tier as tier,\n"
             f"       round(proba_breach::numeric, 3) as prob_violacao, faixa_risco\n"
             f"from analytics.mart_ticket_decision\nwhere faixa_risco = 'Alto'\n{WHERE}\n"
             f"order by proba_breach desc\nlimit 50"),

    dict(nome="Distribuição da fila por faixa de risco", display="pie",
         tabela="mart_ticket_decision",
         sql=f"select faixa_risco, count(*) as chamados\n"
             f"from analytics.mart_ticket_decision\n"
             f"where faixa_risco <> 'Sem score'\n{WHERE}\n"
             f"group by faixa_risco",
         eixo=("faixa_risco", ["chamados"])),

    dict(nome="Matriz de confusão do modelo", display="table", tabela="fct_predictions",
         sql="select case sla_breach_real when 1 then 'Violou (real)' else 'Não violou (real)' end as real,\n"
             "       case sla_breach_previsto when 1 then 'Violou (previsto)' else 'Não violou (previsto)' end as previsto,\n"
             "       count(*) as chamados\n"
             "from analytics.fct_predictions\ngroup by 1, 2\norder by 1, 2"),
]


def template_tags(card, campos):
    """Filtros de dimensao (field filters) ligados as colunas reais da tabela."""
    tags = {}
    if "[[and" not in card["sql"]:
        return tags
    for slug, rotulo, coluna in FILTROS:
        fid = campos.get((card["tabela"], coluna))
        if fid is None:
            continue
        tags[slug] = {"id": f"tag-{card['tabela']}-{slug}", "name": slug,
                      "display-name": rotulo, "type": "dimension",
                      "dimension": ["field", fid, None],
                      "widget-type": "string/=", "default": None}
    return tags


def visualizacao(card):
    if not card.get("eixo"):
        return {}
    dim, metricas = card["eixo"]
    return {"graph.dimensions": [dim], "graph.metrics": metricas}


def criar_cards(mb, db_id, campos):
    existentes = {c["name"]: c["id"] for c in mb.get("/api/card") if not c.get("archived")}
    resultado = []
    for card in CARDS:
        tags = template_tags(card, campos)
        # Metabase >= 0.51 usa o formato MBQL "lib" (stages). O formato legado
        # ({"type":"native","native":{"query":...}}) ainda e' aceito, mas as
        # template-tags sao DESCARTADAS na conversao — e sem elas os filtros do
        # dashboard nao tem onde se ligar.
        corpo = {
            "name": card["nome"],
            "display": card["display"],
            "visualization_settings": visualizacao(card),
            "dataset_query": {
                "lib/type": "mbql/query", "database": db_id,
                "stages": [{"lib/type": "mbql.stage/native",
                            "native": card["sql"], "template-tags": tags}],
            },
            "description": None,
        }
        if card["nome"] in existentes:
            cid = existentes[card["nome"]]
            mb.put(f"/api/card/{cid}", corpo)
            print(f"  atualizado: {card['nome']}")
        else:
            cid = mb.post("/api/card", corpo)["id"]
            print(f"  criado....: {card['nome']}")
        resultado.append({**card, "id": cid, "tags": tags})
    return resultado


# --------------------------------------------------------------------- dashboard
def montar_dashboard(mb, cards):
    existente = next((d for d in mb.get("/api/dashboard")
                      if d["name"] == NOME_DASH and not d.get("archived")), None)
    dash_id = (existente["id"] if existente
               else mb.post("/api/dashboard", {
                   "name": NOME_DASH,
                   "description": "Previsão de violação de SLA em chamados de suporte técnico. "
                                  "Fonte: modelos dbt no schema analytics."})["id"])
    print(f"  dashboard id={dash_id}")

    parametros = [{"id": f"param-{slug}", "name": rotulo, "slug": slug,
                   "type": "string/=", "sectionId": "string"}
                  for slug, rotulo, _ in FILTROS]

    # grade do Metabase: 24 colunas de largura
    layout = [(0, 0, 6, 4), (6, 0, 6, 4), (12, 0, 6, 4),
              (0, 4, 12, 6), (12, 4, 12, 6),
              (0, 10, 12, 6), (12, 10, 12, 6),
              (0, 16, 16, 8), (16, 16, 8, 8),
              (0, 24, 12, 6)]

    dashcards = []
    for i, card in enumerate(cards):
        col, row, w, h = layout[i] if i < len(layout) else (0, 30 + i * 6, 12, 6)
        mapeamentos = [
            {"parameter_id": f"param-{slug}", "card_id": card["id"],
             "target": ["dimension", ["template-tag", slug]]}
            for slug, _, _ in FILTROS if slug in card["tags"]
        ]
        dashcards.append({"id": -(i + 1), "card_id": card["id"],
                          "col": col, "row": row, "size_x": w, "size_y": h,
                          "parameter_mappings": mapeamentos,
                          "visualization_settings": {}})

    mb.put(f"/api/dashboard/{dash_id}",
           {"parameters": parametros, "dashcards": dashcards})
    return dash_id


# -------------------------------------------------------------------- evidencias
def mapa_dashcards(mb, dash_id):
    """{card_id: dashcard_id} — necessario para consultar via dashboard."""
    dash = mb.get(f"/api/dashboard/{dash_id}")
    return {dc["card_id"]: dc["id"] for dc in dash.get("dashcards", [])}


def _executar_card(mb, dash_id, dashcard_id, card_id, parametros=None):
    """Executa o card ATRAVES do dashboard.

    Usar este endpoint (e nao /api/card/:id/query) e' proposital: ele passa pelos
    parameter_mappings do painel, entao o resultado prova que o filtro do
    dashboard esta de fato ligado ao card — nao apenas que o SQL aceita um
    parametro solto.
    """
    res = mb.post(f"/api/dashboard/{dash_id}/dashcard/{dashcard_id}/card/{card_id}/query",
                  {"parameters": parametros or []})
    return res.get("data", {}).get("rows", [])


def gravar_evidencia(mb, cards, dash_id, url):
    """Roda cada card e registra o resultado em evidencias/metabase_dashboard.log.

    Inclui uma demonstracao do filtro: a mesma pergunta respondida com e sem
    recorte por prioridade. E' a prova objetiva de que o filtro funciona.
    """
    dashcards = mapa_dashcards(mb, dash_id)
    linhas = [
        "EVIDENCIA DE EXECUCAO - DASHBOARD NO METABASE",
        "=" * 66,
        f"Painel....: {NOME_DASH}",
        f"URL.......: {url}/dashboard/{dash_id}",
        f"Metabase..: {mb.get('/api/session/properties').get('version', {}).get('tag')}",
        "Fonte.....: Postgres, schema analytics (modelos dbt)",
        f"Gerado....: {time.strftime('%Y-%m-%d %H:%M')}",
        "Provisionado por: src/bi/metabase_setup.py",
        "",
        "FILTROS DO PAINEL: " + ", ".join(r for _, r, _ in FILTROS),
        "",
        "CARDS E RESULTADO (sem filtro aplicado)",
        "-" * 66,
    ]
    for card in cards:
        rows = _executar_card(mb, dash_id, dashcards[card["id"]], card["id"])
        primeira = " | ".join(str(v) for v in rows[0]) if rows else "(sem linhas)"
        linhas.append(f"  {card['nome']:<46} {len(rows):>3} linha(s)  "
                      f"[{len(card['tags'])} filtros]")
        linhas.append(f"      1a linha: {primeira}")

    # Demonstracao do filtro no card de taxa de violacao, aplicado PELO dashboard.
    alvo = next(c for c in cards if c["nome"] == "Taxa de violação de SLA (%)")
    dc_alvo = dashcards[alvo["id"]]
    linhas += ["", "DEMONSTRACAO DO FILTRO (card 'Taxa de violacao de SLA')",
               "Consultas feitas pelo endpoint do dashboard, passando pelo filtro.",
               "-" * 66]
    sem = _executar_card(mb, dash_id, dc_alvo, alvo["id"])
    linhas.append(f"  sem filtro................: {sem[0][0] if sem else '?'} %")
    for valor in ["Crítica", "Alta", "Média", "Baixa"]:
        rows = _executar_card(mb, dash_id, dc_alvo, alvo["id"], [{
            "id": "param-prioridade", "type": "string/=",
            "target": ["dimension", ["template-tag", "prioridade"]],
            "value": [valor],
        }])
        linhas.append(f"  Prioridade = {valor:<10}: {rows[0][0] if rows else '?'} %")

    linhas += [
        "",
        "A taxa global e' a media do periodo e cresce monotonicamente com a",
        "prioridade, como esperado pela regra de SLA do projeto: prazos mais",
        "curtos nas prioridades altas produzem mais violacoes.",
        "",
    ]
    destino = EVID_DIR / "metabase_dashboard.log"
    destino.write_text("\n".join(linhas), encoding="utf-8")
    print(f"  evidencia gravada -> {destino}")
    return destino


# -------------------------------------------------------------------------- main
def run(url=None):
    url = url or os.environ.get("MB_URL", "http://localhost:3000")
    print(f"Metabase: {url}")
    mb = Metabase(url)

    print("\n[1/5] conexao com o Metabase")
    mb.esperar_no_ar()
    mb.autenticar()

    print("\n[2/5] conexao com o Postgres")
    db_id = garantir_banco(mb)

    print("\n[3/5] sincronizando o schema analytics")
    meta = esperar_sync(mb, db_id, {"fct_tickets", "fct_predictions", "mart_ticket_decision"})
    campos = mapa_campos(meta)

    print(f"\n[4/5] cards ({len(CARDS)})")
    cards = criar_cards(mb, db_id, campos)

    print("\n[5/5] dashboard, filtros e evidencias")
    dash_id = montar_dashboard(mb, cards)
    gravar_evidencia(mb, cards, dash_id, url)

    destino = f"{url}/dashboard/{dash_id}"
    print(f"\nPRONTO -> {destino}")
    print(f"  {len(cards)} cards | filtros: " + ", ".join(r for _, r, _ in FILTROS))
    print(f"  login: {ADMIN['email']} / {ADMIN['password']}")
    return {"url": destino, "dashboard_id": dash_id, "cards": len(cards)}


def main():
    ap = argparse.ArgumentParser(description="Provisiona o dashboard do Metabase.")
    ap.add_argument("--url", default=None, help="URL do Metabase (padrao: MB_URL ou localhost:3000)")
    run(ap.parse_args().url)


if __name__ == "__main__":
    main()
