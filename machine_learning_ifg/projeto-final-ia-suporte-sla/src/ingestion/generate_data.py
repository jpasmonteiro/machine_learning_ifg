"""
Ingestao / geracao do conjunto de dados (camada RAW - bronze).

Gera, de forma reproduzivel (seed fixa), 3 fontes que simulam o historico de um
service desk de suporte tecnico:

  1. tickets.csv           -> dados ESTRUTURADOS (tabela de chamados)
  2. ticket_messages.jsonl -> dados NAO ESTRUTURADOS (texto livre do cliente)
  3. ticket_events.json    -> dados SEMIESTRUTURADOS (logs de eventos em JSON)

Optamos por dados sinteticos por reprodutibilidade e privacidade, mas o esquema
espelha o "Customer Support Ticket Dataset" citado no enunciado. Para usar dados
reais, basta trocar os arquivos em data/raw mantendo os mesmos campos.
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from config.settings import (
    RAW_DIR, SEED, N_TICKETS, CHANNELS, PRODUCTS, CATEGORIES,
    PRIORITIES, TIERS, REGIONS, SLA_RESOLUTION_MINUTES,
)

rng = np.random.default_rng(SEED)

CAT_BASE_MIN = {
    "Acesso e Conta": 130, "Problema Técnico": 620, "Bug / Defeito": 900,
    "Faturamento": 300, "Dúvida / Como Fazer": 90,
    "Solicitação de Recurso": 1500, "Cancelamento": 240,
}
PRIORITY_HANDLING = {"Crítica": 0.60, "Alta": 0.82, "Média": 1.00, "Baixa": 1.20}
TIER_FACTOR = {"Free": 1.25, "Basic": 1.00, "Premium": 0.85, "Enterprise": 0.70}
CHANNEL_FACTOR = {"Email": 1.10, "Chat": 0.85, "Telefone": 0.80,
                  "Formulário Web": 1.00, "Redes Sociais": 1.20}
CAT_REOPEN_P = {
    "Acesso e Conta": 0.05, "Problema Técnico": 0.12, "Bug / Defeito": 0.22,
    "Faturamento": 0.07, "Dúvida / Como Fazer": 0.03,
    "Solicitação de Recurso": 0.10, "Cancelamento": 0.06,
}

TEXT_TEMPLATES = {
    "Acesso e Conta": [
        "Não consigo acessar minha conta, a senha não é aceita.",
        "Estou bloqueado após várias tentativas de login. Preciso entrar.",
        "O código de autenticação de dois fatores não chega no meu email.",
    ],
    "Problema Técnico": [
        "O sistema está muito lento e trava ao carregar os dados.",
        "A página fica em branco quando tento gerar o relatório.",
        "Recebo um erro inesperado toda vez que salvo as alterações.",
    ],
    "Bug / Defeito": [
        "Encontrei um erro: o valor total está sendo calculado errado.",
        "O botão de exportar não funciona, dá erro 500.",
        "Os dados somem depois que atualizo a tela. Parece um defeito.",
    ],
    "Faturamento": [
        "Fui cobrado duas vezes na fatura deste mês, quero o reembolso.",
        "Minha nota fiscal veio com o valor incorreto.",
        "Não reconheço essa cobrança no meu cartão, podem verificar?",
    ],
    "Dúvida / Como Fazer": [
        "Como faço para adicionar um novo usuário na minha equipe?",
        "Gostaria de saber como exportar os dados em planilha.",
        "Qual o passo a passo para integrar com outra ferramenta?",
    ],
    "Solicitação de Recurso": [
        "Seria possível adicionar um filtro por data no relatório?",
        "Sugiro um modo escuro para a plataforma.",
        "Gostaria que houvesse integração nativa com o WhatsApp.",
    ],
    "Cancelamento": [
        "Quero cancelar minha assinatura, não vou mais utilizar.",
        "Por favor cancelem o plano, estou insatisfeito com o serviço.",
        "Desejo encerrar a conta e interromper as cobranças.",
    ],
}
URGENCY_SUFFIX = [
    " Isso é urgente, estou com a operação parada!",
    " Preciso de uma solução imediata, por favor.",
    " Estou perdendo dinheiro com isso.",
    "", "", "",
]
AGENT_NOTE = [
    "Reproduzido o cenário e encaminhado ao time responsável.",
    "Solicitado print e logs adicionais ao cliente.",
    "Aplicado contorno temporário; monitorando.",
    "Escalado para o nível 2 de suporte.",
    "Orientação enviada ao cliente; aguardando retorno.",
]


def _choice(options, p=None):
    return options[rng.choice(len(options), p=p)]


def generate():
    start = datetime(2025, 1, 1)
    tickets, messages, events = [], [], []

    cat_p = np.array([0.16, 0.20, 0.14, 0.13, 0.17, 0.10, 0.10]); cat_p /= cat_p.sum()
    pri_p = np.array([0.30, 0.40, 0.22, 0.08])
    tier_p = np.array([0.35, 0.30, 0.22, 0.13])
    ch_p = np.array([0.34, 0.24, 0.16, 0.16, 0.10])

    for i in range(N_TICKETS):
        tid = f"TCK-{i+1:06d}"
        category = _choice(CATEGORIES, cat_p)
        priority = _choice(PRIORITIES, pri_p)
        tier = _choice(TIERS, tier_p)
        channel = _choice(CHANNELS, ch_p)
        product = _choice(PRODUCTS)
        region = _choice(REGIONS)
        customer_id = f"CUST-{rng.integers(1, 2600):05d}"
        agent_id = f"AGT-{rng.integers(1, 70):03d}"

        created = start + timedelta(minutes=int(rng.integers(0, 365 * 24 * 60)))
        hour = created.hour
        backlog = int(max(0, rng.normal(40 + (12 if 9 <= hour <= 18 else -10), 18)))

        base_text = _choice(TEXT_TEMPLATES[category])
        urgent = priority in ("Alta", "Crítica") and rng.random() < 0.6
        body = base_text + (_choice(URGENCY_SUFFIX) if urgent else _choice(URGENCY_SUFFIX[3:]))
        if rng.random() < 0.15:
            body = body + " " + base_text + " Detalhando melhor o ocorrido para o time."

        reopened = int(rng.random() < CAT_REOPEN_P[category] * (1.4 if priority in ("Alta", "Crítica") else 1.0))

        fr_base = {"Crítica": 12, "Alta": 35, "Média": 110, "Baixa": 220}[priority]
        first_response = max(1.0, rng.lognormal(mean=np.log(fr_base * CHANNEL_FACTOR[channel]), sigma=0.5) + backlog * 0.6)

        base = CAT_BASE_MIN[category]
        text_factor = 1.0 + min(len(body), 200) / 600.0
        handling = (base * PRIORITY_HANDLING[priority] * TIER_FACTOR[tier]
                    * CHANNEL_FACTOR[channel] * text_factor
                    * (1.5 if reopened else 1.0)
                    * rng.lognormal(mean=0.0, sigma=0.45) + backlog * 1.2)
        resolution = float(first_response + max(5.0, handling))

        sla = SLA_RESOLUTION_MINUTES[priority]
        sla_breach = int(resolution > sla)

        if rng.random() < 0.60:
            mean_csat = 4.4 - 1.6 * sla_breach - 0.4 * reopened
            csat = int(np.clip(round(rng.normal(mean_csat, 0.7)), 1, 5))
        else:
            csat = None

        tickets.append({
            "ticket_id": tid, "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
            "channel": channel, "product": product, "category": category,
            "priority": priority, "customer_tier": tier, "customer_id": customer_id,
            "agent_id": agent_id, "region": region, "backlog_at_creation": backlog,
            "first_response_minutes": round(first_response, 1),
            "resolution_minutes": round(resolution, 1),
            "reopened": reopened, "csat_score": csat,
        })
        messages.append({
            "ticket_id": tid, "subject": f"[{category}] {product}",
            "body": body, "agent_note": _choice(AGENT_NOTE), "lang": "pt-BR",
        })

        evlist = [{"ts": created.strftime("%Y-%m-%d %H:%M:%S"), "event": "created",
                   "actor": "customer", "from_status": None, "to_status": "Aberto"}]
        t_fr = created + timedelta(minutes=float(first_response))
        evlist.append({"ts": t_fr.strftime("%Y-%m-%d %H:%M:%S"), "event": "first_response",
                       "actor": agent_id, "from_status": "Aberto", "to_status": "Em Atendimento"})
        if reopened:
            t_ro = t_fr + timedelta(minutes=float(handling) * 0.6)
            evlist.append({"ts": t_ro.strftime("%Y-%m-%d %H:%M:%S"), "event": "reopened",
                           "actor": "customer", "from_status": "Resolvido", "to_status": "Reaberto"})
        t_res = created + timedelta(minutes=float(resolution))
        evlist.append({"ts": t_res.strftime("%Y-%m-%d %H:%M:%S"), "event": "resolved",
                       "actor": agent_id, "from_status": "Em Atendimento", "to_status": "Resolvido"})
        events.append({"ticket_id": tid, "events": evlist})

    df = pd.DataFrame(tickets)
    df.to_csv(RAW_DIR / "tickets.csv", index=False)
    with open(RAW_DIR / "ticket_messages.jsonl", "w", encoding="utf-8") as f:
        for m in messages:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    with open(RAW_DIR / "ticket_events.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=0)

    sla_map = df["priority"].map(SLA_RESOLUTION_MINUTES)
    breach_rate = df["resolution_minutes"].gt(sla_map).mean()
    print(f"[ingestion] {len(df)} tickets gerados em {RAW_DIR}")
    print(f"[ingestion] taxa de violacao de SLA (alvo positivo): {breach_rate:.1%}")
    return df


if __name__ == "__main__":
    generate()
