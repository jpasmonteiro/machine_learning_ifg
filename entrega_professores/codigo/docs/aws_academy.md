# Rodando na AWS Academy (Learner Lab)

O Learner Lab da AWS Academy tem restricoes importantes:

- **Nao e' possivel criar IAM Roles/Policies** (`iam:CreateRole` bloqueado). Use o papel
  pre-existente **`LabRole`**.
- Regiao travada em **us-east-1**; orcamento pequeno; a sessao expira (~4h) e os recursos
  podem ser apagados ao encerrar o lab.
- Servicos gerenciados como **MWAA nao estao disponiveis**. SageMaker pode ter limitacoes.

## O que isso muda no projeto

Nada essencial. O requisito do enunciado e' *usar pelo menos um servico da AWS* + entregar o
*diagrama da arquitetura equivalente 100% AWS* (que e' uma proposta em diagrama, nao precisa
rodar MWAA/SageMaker). O servico que usamos de fato e' o **S3**, que **nao precisa de role**:
funciona com as credenciais temporarias do proprio lab.

## Passo a passo

### 1. Pegar as credenciais do lab
No painel do Learner Lab, clique em **"AWS Details" > "AWS CLI"** e copie as credenciais
(incluem `aws_session_token`). No terminal:

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
export AWS_DEFAULT_REGION=us-east-1
```

### 2. (Opcional) Provisionar S3 + Logs via CloudFormation compativel com Academy
Use o template `infra/cloudformation-academy.yaml` (NAO cria role; usa o LabRole):

```bash
aws cloudformation deploy \
  --template-file infra/cloudformation-academy.yaml \
  --stack-name suporte-ia
# nao precisa de --capabilities: o template nao cria recursos IAM
```

> Para incluir a Lambda opcional (usando o LabRole):
> `--parameter-overrides CriarLambda=sim`

Descubra o nome do bucket criado:
```bash
aws cloudformation describe-stacks --stack-name suporte-ia \
  --query "Stacks[0].Outputs[?OutputKey=='RawBucketName'].OutputValue" --output text
```

### 3. Enviar os dados para o S3 (uso real do servico AWS)
Sem criar role nenhuma:
```bash
pip install boto3
export S3_BUCKET=<nome-do-bucket>       # ex.: suporte-ia-raw-123456789012
export S3_PREFIX=suporte-sla
python -m src.cloud.s3_sync             # sobe raw/processed/curated para o S3
```

Se preferir sem CloudFormation, da' pra criar o bucket na mao e usar o mesmo comando:
```bash
aws s3 mb s3://meu-bucket-suporte
export S3_BUCKET=meu-bucket-suporte
python -m src.cloud.s3_sync
```

## Para a apresentacao (transformar a limitacao em ponto forte)

Deixe claro que voces entenderam a restricao do Academy: usaram **S3 + LabRole** (sem criar
roles), mantiveram o restante como **arquitetura de referencia** no diagrama, e o pipeline roda
localmente com DuckDB espelhando o Snowflake. Isso mostra dominio do trade-off, que e'
exatamente o que um professor exigente valoriza.
