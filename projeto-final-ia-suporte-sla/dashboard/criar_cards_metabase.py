# -*- coding: utf-8 -*-
"""
Provisiona o dashboard do Metabase pela API: conexao com o Postgres, os 10 cards
e o painel "Suporte - Apoio a Decisao" com filtros de prioridade, categoria e canal.

O script e' idempotente: rodar de novo atualiza o que ja' existe em vez de duplicar.

PRE-REQUISITOS
    1. Containers no ar:  docker compose -f infra/docker-compose.yml up -d
    2. Dados carregados:  WAREHOUSE_TARGET=postgres python -m src.warehouse.load_warehouse
                          WAREHOUSE_TARGET=postgres python -m src.warehouse.run_dbt
    3. Metabase configurado: abra http://localhost:3000 e crie o usuario administrador
       (o script nao cria conta nem manipula senha).
    4. Uma chave de API: no Metabase, engrenagem -> Admin -> Authentication -> API keys
       -> "Create API key" (grupo Administrators). Guarde a chave em um arquivo .env
       na raiz do projeto (o .env ja' esta no .gitignore):

           MB_API_KEY=mb_xxxxxxxxxxxxxxxxxxxxx

USO
    python dashboard/criar_cards_metabase.py
    python dashboard/criar_cards_metabase.py --url http://localhost:3000
"""
import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]

PG = {
    "host": os.environ.get("MB_PG_HOST", "postgres"),   # nome do servico no docker-compose
    "port": int(os.environ.get("MB_PG_PORT", "5432")),  # porta INTERNA do container
    "dbname": os.environ.get("MB_PG_DATABASE", "suporte_dw"),
    "user": os.environ.get("MB_PG_USER", "suporte"),
    "password": os.environ.get("MB_PG_PASSWORD", "suporte"),
}
NOME_BANCO = "Suporte DW (Postgres)"
NOME_DASH = "Suporte - Apoio a Decisao"

# --------------------------------------------------------------------------- HTTP
class Metabase:
    def __init__(self, base, api_key=None, user=None, password=None):
        self.base = base.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["x-api-key"] = api_key
        elif user and password:
            tok = self._call("POST", "/api/session",
                             {"username": user, "password": password})["id"]
            self.headers["X-Metabase-Session"] = tok
        else:
            sys.exit("Defina MB_API_KEY (recomendado) ou MB_USER + MB_PASSWORD. "
                     "Veja o cabecalho deste arquivo.")

    def _call(self, metodo, caminho, corpo=None):
        dados = json.dumps(corpo).encode() if corpo is not None else None
        req = urllib.request.Request(self.base + caminho, data=dados,
                                     headers=self.headers, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                txt = r.read().decode()
                return json.loads(txt) if txt else {}
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode()[:400]
            raise SystemExit(f"\n[erro] {metodo} {caminho} -> HTTP {e.code}\n{detalhe}\n")
        except urllib.error.URLError as e:
            raise SystemExit(f"\n[erro] Metabase inacessivel em {self.base}: {e.reason}\n"
                             f"Suba os containers: docker compose -f infra/docker-compose.yml up -d\n")

    get = lambda self, p: self._call("GET", p)
    post = lambda self, p, b: self._call("POST", p, b)
    put = lambda self, p, b: self._call("PUT", p, b)


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


def esperar_sync(mb, db_id, tabelas_esperadas, tentativas=30):
    """O Metabase varre o schema de forma assincrona; espera as tabelas aparecerem."""
    mb.post(f"/api/database/{db_id}/sync_schema", {})
    for i in range(tentativas):
        meta = mb.get(f"/api/database/{db_id}/metadata")
        achadas = {t["name"] for t in meta.get("tables", [])
                   if t.get("schema") == "analytics"}
        if tabelas_esperadas <= achadas:
            print(f"  schema sincronizado ({len(achadas)} tabelas em analytics)")
            return meta
        time.sleep(3)
    raise SystemExit(f"[erro] sync nao completou. Encontradas: {sorted(achadas)}")


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
FILTROS = [("prioridade", "Prioridade", "priority"),
           ("categoria", "Categoria", "category"),
           ("canal", "Canal", "channel")]

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


# -------------------------------------------------------------------------- main
def carregar_env():
    """Le o .env da pasta do projeto ou de ate' dois niveis acima (raiz do repo)."""
    for pasta in (ROOT, ROOT.parent, ROOT.parent.parent):
        env = pasta / ".env"
        if not env.exists():
            continue
        for linha in env.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        print(f"  credenciais lidas de {env.parent}/.env")
        return
    print("  nenhum .env encontrado; usando variaveis de ambiente")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("MB_URL", "http://localhost:3000"))
    args = ap.parse_args()

    carregar_env()
    print(f"Metabase: {args.url}")
    mb = Metabase(args.url, os.environ.get("MB_API_KEY"),
                  os.environ.get("MB_USER"), os.environ.get("MB_PASSWORD"))

    print("\n[1/4] conexao com o Postgres")
    db_id = garantir_banco(mb)

    print("\n[2/4] sincronizando o schema analytics")
    meta = esperar_sync(mb, db_id, {"fct_tickets", "fct_predictions", "mart_ticket_decision"})
    campos = mapa_campos(meta)

    print(f"\n[3/4] cards ({len(CARDS)})")
    cards = criar_cards(mb, db_id, campos)

    print("\n[4/4] dashboard e filtros")
    dash_id = montar_dashboard(mb, cards)

    print(f"\nPRONTO -> {args.url}/dashboard/{dash_id}")
    print(f"  {len(cards)} cards | filtros: " + ", ".join(r for _, r, _ in FILTROS))


if __name__ == "__main__":
    main()
