"""
Orquestrador do pipeline completo (versao local, sem Airflow).

Roda todas as etapas na ordem correta:
  ingestao -> processamento/atributos -> ML -> carga no warehouse ->
  dbt (build + testes) -> export do dashboard.

Uso:
    python run_pipeline.py

A mesma sequencia de funcoes e' chamada pela DAG do Airflow
(airflow/dags/pipeline_suporte_dag.py).
"""
import time

from src.ingestion import generate_data
from src.processing import process_features
from src.ml import train_evaluate
from src.warehouse import load_warehouse, run_dbt, export_dashboard
from src.cloud import s3_sync

ETAPAS = [
    ("1. Ingestao (dados brutos)", generate_data.generate),
    ("2. Processamento e extracao de atributos", process_features.run),
    ("3. Treino e avaliacao do modelo", train_evaluate.run),
    ("4. Carga no warehouse (Snowflake/DuckDB)", load_warehouse.run),
    ("5. dbt build (modelos + testes)", run_dbt.run),
    ("6. Export do dashboard", export_dashboard.run),
    ("7. Upload das camadas para o S3 (AWS; pulado em modo local)", s3_sync.run),
]


def main():
    print("=" * 64)
    print("PIPELINE DE SUPORTE TECNICO - EXECUCAO COMPLETA")
    print("=" * 64)
    t0 = time.time()
    for nome, func in ETAPAS:
        print(f"\n>>> {nome}")
        ini = time.time()
        func()
        print(f"    (ok em {time.time()-ini:.1f}s)")
    print("\n" + "=" * 64)
    print(f"PIPELINE CONCLUIDO em {time.time()-t0:.1f}s")
    print("=" * 64)


if __name__ == "__main__":
    main()
