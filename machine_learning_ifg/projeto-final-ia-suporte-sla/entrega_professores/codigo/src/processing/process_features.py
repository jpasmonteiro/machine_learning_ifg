"""
Processamento e extracao de atributos (camada PROCESSED - silver).

Le as 3 fontes brutas e produz tabelas tratadas e tabulares:
  - tickets_clean.csv : dados estruturados limpos + partes de data + alvo (sla_breach)
  - text_features.csv : atributos extraidos do texto livre (nao estruturado)
  - log_features.csv  : agregacoes extraidas dos logs de eventos (semiestruturado)
  - ml_features.csv    : tabela unica (join) pronta para o modelo

Decisao de modelagem: o ponto de decisao e' logo apos a PRIMEIRA RESPOSTA do
agente. Por isso usamos como atributos apenas o que ja' e' conhecido nesse
momento (categoria, prioridade, canal, tier, fila, 1a resposta, texto, logs).
NAO usamos resolution_minutes nem csat como atributos (sao desfechos) para
evitar vazamento de dados (data leakage).
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import json
import re
import unicodedata
import numpy as np
import pandas as pd

from config.settings import RAW_DIR, PROCESSED_DIR, SLA_RESOLUTION_MINUTES, URGENCY_LEXICON


def load_raw():
    tickets = pd.read_csv(RAW_DIR / "tickets.csv")
    messages = pd.read_json(RAW_DIR / "ticket_messages.jsonl", lines=True)
    with open(RAW_DIR / "ticket_events.json", encoding="utf-8") as f:
        events = json.load(f)
    return tickets, messages, events


def clean_structured(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["created_at"] = pd.to_datetime(df["created_at"])
    # padronizacao de texto categorico
    for c in ["channel", "product", "category", "priority", "customer_tier", "region"]:
        df[c] = df[c].astype(str).str.strip()
    # tratamento de ausentes: csat ausente vira flag (nao imputa o alvo!)
    df["csat_missing"] = df["csat_score"].isna().astype(int)
    # partes de data uteis para analise e dashboard
    df["created_date"] = df["created_at"].dt.date.astype(str)
    df["created_hour"] = df["created_at"].dt.hour
    df["created_weekday"] = df["created_at"].dt.weekday
    df["created_month"] = df["created_at"].dt.month
    # alvo: violacao do SLA de resolucao
    df["sla_minutes"] = df["priority"].map(SLA_RESOLUTION_MINUTES)
    df["sla_breach"] = (df["resolution_minutes"] > df["sla_minutes"]).astype(int)
    return df


def extract_text_features(messages: pd.DataFrame) -> pd.DataFrame:
    rows = []
    lex = [w.lower() for w in URGENCY_LEXICON]
    for _, m in messages.iterrows():
        body = str(m["body"])
        low = body.lower()
        low_a = "".join(c for c in unicodedata.normalize("NFKD", low) if not unicodedata.combining(c))
        words = re.findall(r"\w+", low)
        n_alpha = sum(ch.isalpha() for ch in body)
        n_upper = sum(ch.isupper() for ch in body)
        rows.append({
            "ticket_id": m["ticket_id"],
            "body_len": len(body),
            "word_count": len(words),
            "num_question": body.count("?"),
            "num_exclam": body.count("!"),
            "upper_ratio": round(n_upper / n_alpha, 4) if n_alpha else 0.0,
            "urgency_hits": sum(low_a.count(w) for w in lex),
            "kw_refund": int("reembolso" in low_a or "cobrad" in low_a),
            "kw_cancel": int("cancel" in low_a),
            "kw_error": int("erro" in low_a or "nao funciona" in low_a or "defeito" in low_a),
        })
    return pd.DataFrame(rows)


def extract_log_features(events: list) -> pd.DataFrame:
    rows = []
    for rec in events:
        evs = rec["events"]
        statuses = [e["to_status"] for e in evs if e.get("to_status")]
        rows.append({
            "ticket_id": rec["ticket_id"],
            "n_events": len(evs),
            "n_status_changes": max(0, len(statuses) - 1),
            "reopened_from_log": int(any(e["event"] == "reopened" for e in evs)),
        })
    return pd.DataFrame(rows)


def run():
    tickets, messages, events = load_raw()
    clean = clean_structured(tickets)
    text = extract_text_features(messages)
    logs = extract_log_features(events)

    clean.to_csv(PROCESSED_DIR / "tickets_clean.csv", index=False)
    text.to_csv(PROCESSED_DIR / "text_features.csv", index=False)
    logs.to_csv(PROCESSED_DIR / "log_features.csv", index=False)

    # tabela unica para o modelo (apenas atributos sem vazamento + alvo)
    feat_cols = [
        "ticket_id", "channel", "product", "category", "priority",
        "customer_tier", "region", "backlog_at_creation", "first_response_minutes",
        "reopened", "created_hour", "created_weekday", "created_month", "sla_breach",
    ]
    ml = clean[feat_cols].merge(text, on="ticket_id").merge(logs, on="ticket_id")
    ml.to_csv(PROCESSED_DIR / "ml_features.csv", index=False)

    print(f"[processing] tickets_clean: {clean.shape}, text: {text.shape}, logs: {logs.shape}")
    print(f"[processing] ml_features: {ml.shape} -> {PROCESSED_DIR/'ml_features.csv'}")
    print(f"[processing] taxa de sla_breach: {clean['sla_breach'].mean():.1%}")
    return ml


if __name__ == "__main__":
    run()
