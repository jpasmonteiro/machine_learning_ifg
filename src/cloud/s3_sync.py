"""
Sincronizacao das camadas de dados com o Amazon S3 (uso real de servico AWS).

Envia os arquivos das camadas raw / processed / curated para o bucket S3,
organizando por prefixo (data lake em camadas). A etapa e' ativada quando a
variavel de ambiente S3_BUCKET esta definida pelo provisionamento
CloudFormation da pipeline. Nesta entrega, o upload para S3 e' obrigatorio.

Uso:
    export S3_BUCKET=meu-bucket            # nome do bucket (saida do CloudFormation)
    export S3_PREFIX=suporte-sla           # opcional (default: suporte-sla)
    pip install boto3
    python -m src.cloud.s3_sync
"""
import os
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from config.settings import RAW_DIR, PROCESSED_DIR, CURATED_DIR

LAYERS = {"raw": RAW_DIR, "processed": PROCESSED_DIR, "curated": CURATED_DIR}


def run():
    bucket = os.environ.get("S3_BUCKET")
    if not bucket:
        raise RuntimeError(
            "S3_BUCKET nao definido. A pipeline da entrega deve provisionar "
            "o bucket via CloudFormation antes do upload."
        )

    try:
        import boto3  # import tardio: so e' exigido quando o S3 esta ativo
    except ImportError:
        raise RuntimeError("boto3 nao instalado. Execute: pip install -r requirements.txt")

    prefix = os.environ.get("S3_PREFIX", "suporte-sla").strip("/")
    s3 = boto3.client("s3")
    total = 0
    for layer, directory in LAYERS.items():
        base = pathlib.Path(directory)
        for path in sorted(base.rglob("*")):
            if path.is_file():
                key = f"{prefix}/{layer}/{path.relative_to(base).as_posix()}"
                s3.upload_file(str(path), bucket, key)
                total += 1
    print(f"[s3] {total} arquivos enviados para s3://{bucket}/{prefix}/ "
          f"(camadas: raw, processed, curated)")
    if total == 0:
        raise RuntimeError("Nenhum arquivo foi enviado ao S3.")
    return {"uploaded": total, "skipped": False}


if __name__ == "__main__":
    run()
