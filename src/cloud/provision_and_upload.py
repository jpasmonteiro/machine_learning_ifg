# -*- coding: utf-8 -*-
"""
Etapa de nuvem em UM unico processo: provisiona o bucket e envia as camadas.

Por que existe: `provision_s3_bucket()` publica o nome do bucket em
os.environ["S3_BUCKET"], que so' vale dentro do processo atual. Chamar o
provisionamento e o upload em dois comandos separados faz o segundo perder a
variavel. O run_pipeline.py ja' roda tudo no mesmo processo; este modulo da' a
mesma garantia para a task do Airflow.

Uso:
    python -m src.cloud.provision_and_upload
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.cloud.aws_runtime import provision_s3_bucket
from src.cloud import s3_sync


def run():
    bucket = provision_s3_bucket()
    resultado = s3_sync.run()
    return {"bucket": bucket, **resultado}


if __name__ == "__main__":
    run()
