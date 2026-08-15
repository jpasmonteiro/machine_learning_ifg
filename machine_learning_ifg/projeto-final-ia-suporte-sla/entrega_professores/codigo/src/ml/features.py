"""
Preparacao da matriz de atributos para o modelo.

- One-hot nas variaveis categoricas.
- Padronizacao (z-score) das numericas, com media/desvio estimados SO no treino
  (boa pratica para evitar vazamento do conjunto de teste).
- Split treino/teste estratificado e reprodutivel.
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

CATEGORICAL = ["channel", "product", "category", "priority", "customer_tier", "region"]
NUMERIC = [
    "backlog_at_creation", "first_response_minutes", "reopened",
    "created_hour", "created_weekday", "created_month",
    "body_len", "word_count", "num_question", "num_exclam", "upper_ratio",
    "urgency_hits", "kw_refund", "kw_cancel", "kw_error",
    "n_events", "n_status_changes", "reopened_from_log",
]
TARGET = "sla_breach"


def build_matrix(df: pd.DataFrame):
    df = df.copy()
    X_cat = pd.get_dummies(df[CATEGORICAL], prefix=CATEGORICAL)
    X_num = df[NUMERIC].astype(float)
    X = pd.concat([X_num, X_cat], axis=1)
    y = df[TARGET].astype(int).values
    return X, y


def split_and_scale(df, test_size=0.25, seed=42):
    X, y = build_matrix(df)
    ids = df["ticket_id"].values
    X_tr, X_te, y_tr, y_te, id_tr, id_te = train_test_split(
        X, y, ids, test_size=test_size, random_state=seed, stratify=y
    )
    num_cols = [c for c in X.columns if c in NUMERIC]
    mu = X_tr[num_cols].mean()
    sd = X_tr[num_cols].std().replace(0, 1.0)
    X_tr = X_tr.copy(); X_te = X_te.copy()
    X_tr[num_cols] = (X_tr[num_cols] - mu) / sd
    X_te[num_cols] = (X_te[num_cols] - mu) / sd
    return X_tr, X_te, y_tr, y_te, id_te, list(X.columns)
