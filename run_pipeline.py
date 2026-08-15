"""
Orquestrador do pipeline completo da entrega (versao local, sem Airflow).

Nesta versao de entrega, os arquivos brutos ja' ficam materializados em
data/raw/. A pipeline exige credenciais AWS em .env-aws, provisiona um bucket
S3 via CloudFormation, valida os arquivos brutos e segue para:
  processamento/atributos -> ML -> carga no warehouse ->
  dbt (build + testes) -> export do dashboard -> upload S3.

Ao final, os recursos AWS permanecem ativos para inspeção. Use `make destroy`
para esvaziar o bucket e destruir a stack CloudFormation.

Uso:
    python run_pipeline.py

A DAG do Airflow continua disponivel como referencia de orquestracao.
"""
from pathlib import Path
import time

from config.settings import RAW_DIR
from src.cloud.aws_runtime import provision_s3_bucket

RAW_FILES = [
    RAW_DIR / "tickets.csv",
    RAW_DIR / "ticket_messages.jsonl",
    RAW_DIR / "ticket_events.json",
]


def validate_raw_files():
    missing = [str(path) for path in RAW_FILES if not Path(path).is_file()]
    if missing:
        raise FileNotFoundError(
            "Arquivos brutos ausentes. Esta entrega espera os dados ja' "
            "materializados em data/raw/. Faltando: " + ", ".join(missing)
        )
    print("[raw] arquivos de entrada encontrados:")
    for path in RAW_FILES:
        print(f"[raw] - {path}")


def process_features_step():
    from src.processing import process_features
    return process_features.run()


def train_evaluate_step():
    from src.ml import train_evaluate
    return train_evaluate.run()


def load_warehouse_step():
    from src.warehouse import load_warehouse
    return load_warehouse.run()


def run_dbt_step():
    from src.warehouse import run_dbt
    return run_dbt.run()


def export_dashboard_step():
    from src.warehouse import export_dashboard
    return export_dashboard.run()


def s3_upload_step():
    from src.cloud import s3_sync
    return s3_sync.run()


ETAPAS = [
    ("1. Validacao dos dados brutos existentes", validate_raw_files),
    ("2. Processamento e extracao de atributos", process_features_step),
    ("3. Treino e avaliacao do modelo", train_evaluate_step),
    ("4. Carga no warehouse (Snowflake/DuckDB)", load_warehouse_step),
    ("5. dbt build (modelos + testes)", run_dbt_step),
    ("6. Export do dashboard", export_dashboard_step),
    ("7. Upload obrigatorio das camadas para o S3", s3_upload_step),
]


def main():
    print("=" * 64)
    print("PIPELINE DE SUPORTE TECNICO - EXECUCAO COMPLETA")
    print("=" * 64)
    t0 = time.time()
    print("\n>>> 0. Provisionamento AWS obrigatorio (CloudFormation + S3)")
    ini = time.time()
    provision_s3_bucket()
    print(f"    (ok em {time.time()-ini:.1f}s)")

    for nome, func in ETAPAS:
        print(f"\n>>> {nome}")
        ini = time.time()
        func()
        print(f"    (ok em {time.time()-ini:.1f}s)")

    print("\n" + "=" * 64)
    print(f"PIPELINE CONCLUIDO em {time.time()-t0:.1f}s")
    print("Recursos AWS mantidos para validacao. Para remover, execute: make destroy")
    print("=" * 64)


if __name__ == "__main__":
    main()
