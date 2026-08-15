"""
Orquestrador do pipeline completo da entrega (execucao direta, sem Airflow).

Nesta versao de entrega, os arquivos brutos ja' ficam materializados em
data/raw/. A pipeline exige credenciais AWS em .env-aws, provisiona um bucket
S3 via CloudFormation, valida os arquivos brutos e segue para:
  processamento/atributos -> ML -> carga no warehouse -> dbt (build + testes)
  -> export do dashboard -> publicacao no Postgres -> dashboard no Metabase
  -> upload S3.

As duas etapas de BI sobem sozinhas os containers de Postgres e Metabase
(infra/docker-compose.yml). Sem Docker na maquina, elas sao puladas com aviso e
o restante do pipeline continua normalmente. Para pular de proposito: SKIP_BI=1.

Ao final, os recursos AWS permanecem ativos para inspeção. Use `make destroy`
para esvaziar o bucket e destruir a stack CloudFormation.

Uso:
    python run_pipeline.py

A DAG do Airflow (airflow/dags/) roda exatamente estas mesmas etapas de forma
orquestrada; veja `make airflow-run`.
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


def publish_bi_step():
    """Republica a modelagem no Postgres, fonte lida pelo Metabase.

    Sobe os containers se preciso. Sem Docker, a etapa e' pulada com aviso.
    """
    from src.bi import stack, publish_bi
    if not stack.garantir_stack():
        return {"pulado": True}
    return publish_bi.run()


def metabase_step():
    """Cria/atualiza o painel 'Suporte - Apoio a Decisao' com os 3 filtros."""
    from src.bi import stack, metabase_setup
    if not stack.garantir_stack():
        return {"pulado": True}
    return metabase_setup.run()


def s3_upload_step():
    from src.cloud import s3_sync
    return s3_sync.run()


ETAPAS = [
    ("1. Validacao dos dados brutos existentes", validate_raw_files),
    ("2. Processamento e extracao de atributos", process_features_step),
    ("3. Treino e avaliacao do modelo", train_evaluate_step),
    ("4. Carga no warehouse (DuckDB)", load_warehouse_step),
    ("5. dbt build (modelos + testes)", run_dbt_step),
    ("6. Export do dashboard", export_dashboard_step),
    ("7. Publicacao da camada analitica no Postgres (BI)", publish_bi_step),
    ("8. Dashboard no Metabase (cards + filtros)", metabase_step),
    ("9. Upload obrigatorio das camadas para o S3", s3_upload_step),
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

    resultados = {}
    for nome, func in ETAPAS:
        print(f"\n>>> {nome}")
        ini = time.time()
        resultados[nome] = func()
        print(f"    (ok em {time.time()-ini:.1f}s)")

    print("\n" + "=" * 64)
    print(f"PIPELINE CONCLUIDO em {time.time()-t0:.1f}s")

    painel = resultados.get("8. Dashboard no Metabase (cards + filtros)") or {}
    if painel.get("url"):
        print(f"Dashboard no Metabase: {painel['url']}")
        print("Airflow (orquestracao): http://localhost:8081  (admin / admin)")
    else:
        print("Etapas de BI puladas (sem Docker). Para o dashboard: make stack-up && make bi")

    print("Recursos AWS mantidos para validacao. Para remover, execute: make destroy")
    print("=" * 64)


if __name__ == "__main__":
    main()
