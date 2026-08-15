import os
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env-aws"
TEMPLATE_FILE = ROOT / "infra" / "cloudformation-s3-pipeline.yaml"

REQUIRED_ENV = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"]

PERMISSIONS_MESSAGE = """
[aws] Arquivo .env-aws nao encontrado ou incompleto.

Crie o arquivo entrega_professores/codigo/.env-aws com este formato:

AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...   # obrigatorio no AWS Academy; opcional fora dele
AWS_DEFAULT_REGION=us-east-1
CFN_STACK_NAME=suporte-sla-entrega
PROJECT_NAME=suporte-sla-entrega
S3_PREFIX=suporte-sla

Permissoes minimas necessarias para o usuario/credencial AWS:

- sts:GetCallerIdentity
- cloudformation:CreateStack
- cloudformation:UpdateStack
- cloudformation:DescribeStacks
- cloudformation:DescribeStackEvents
- cloudformation:DeleteStack
- s3:CreateBucket
- s3:PutEncryptionConfiguration
- s3:PutBucketPublicAccessBlock
- s3:PutObject
- s3:ListBucket
- s3:GetBucketLocation
- s3:DeleteObject
- s3:DeleteBucket

No AWS Academy, copie as credenciais temporarias em "AWS Details > AWS CLI".
"""


def load_env_file(path: pathlib.Path = ENV_FILE):
    if not path.is_file():
        print(PERMISSIONS_MESSAGE)
        raise SystemExit(2)

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value and not value.startswith("preencher"):
            os.environ[key.strip()] = value

    missing = [key for key in REQUIRED_ENV if not os.environ.get(key)]
    if missing:
        print(PERMISSIONS_MESSAGE)
        print("[aws] Campos obrigatorios ausentes no .env-aws: " + ", ".join(missing))
        raise SystemExit(2)

    token = os.environ.get("AWS_SESSION_TOKEN", "")
    if token and len(token) < 100:
        print("[aws] AWS_SESSION_TOKEN parece invalido: o valor informado esta muito curto.")
        print("[aws] No AWS Academy, copie o token completo em AWS Details > AWS CLI.")
        print("[aws] Se estiver usando usuario IAM comum, remova a linha AWS_SESSION_TOKEN do .env-aws.")
        raise SystemExit(2)

    os.environ.setdefault("CFN_STACK_NAME", "suporte-sla-entrega")
    os.environ.setdefault("PROJECT_NAME", "suporte-sla-entrega")
    os.environ.setdefault("S3_PREFIX", "suporte-sla")


def _client(service):
    try:
        import boto3
    except ImportError:
        print("[aws] boto3 nao instalado. Execute: pip install -r requirements.txt")
        raise
    return boto3.client(service, region_name=os.environ["AWS_DEFAULT_REGION"])


def _get_stack(cfn, stack_name):
    try:
        return cfn.describe_stacks(StackName=stack_name)["Stacks"][0]
    except Exception as exc:
        code = getattr(exc, "response", {}).get("Error", {}).get("Code")
        message = getattr(exc, "response", {}).get("Error", {}).get("Message", "")
        if code == "ValidationError" and "does not exist" in message:
            return None
        raise


def _stack_exists(cfn, stack_name):
    return _get_stack(cfn, stack_name) is not None


def _print_recent_stack_events(cfn, stack_name, limit=8):
    try:
        events = cfn.describe_stack_events(StackName=stack_name)["StackEvents"][:limit]
    except Exception:
        return
    print("[aws] Eventos recentes da stack:")
    for event in events:
        logical_id = event.get("LogicalResourceId")
        resource_type = event.get("ResourceType")
        status = event.get("ResourceStatus")
        reason = event.get("ResourceStatusReason")
        print(f"[aws] - {logical_id} ({resource_type}): {status}")
        if reason:
            print(f"[aws]   motivo: {reason}")


def _delete_stack_if_rolled_back(cfn, stack_name):
    stack = _get_stack(cfn, stack_name)
    if not stack:
        return False
    status = stack.get("StackStatus")
    if status not in {"ROLLBACK_COMPLETE", "CREATE_FAILED", "UPDATE_ROLLBACK_COMPLETE"}:
        return False
    print(f"[aws] stack {stack_name} esta em {status}; removendo antes de recriar")
    cfn.delete_stack(StackName=stack_name)
    cfn.get_waiter("stack_delete_complete").wait(StackName=stack_name)
    return True


def _aws_error_message(exc):
    response = getattr(exc, "response", {})
    error = response.get("Error", {})
    code = error.get("Code", "")
    message = error.get("Message", str(exc))

    if code in {"InvalidClientTokenId", "UnrecognizedClientException", "SignatureDoesNotMatch"}:
        return (
            "Credenciais AWS invalidas. Confira AWS_ACCESS_KEY_ID, "
            "AWS_SECRET_ACCESS_KEY e AWS_SESSION_TOKEN no .env-aws."
        )
    if code in {"ExpiredToken", "RequestExpired"}:
        return "Credenciais AWS expiradas. Gere novas credenciais e atualize o .env-aws."
    if code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}:
        return "Credenciais sem permissao suficiente: " + message
    return f"Erro AWS ({code or 'sem codigo'}): {message}"


def provision_s3_bucket():
    load_env_file()

    sts = _client("sts")
    try:
        identity = sts.get_caller_identity()
    except Exception as exc:
        print("[aws] Nao foi possivel validar as credenciais com STS.")
        print("[aws] " + _aws_error_message(exc))
        raise SystemExit(2)
    print(f"[aws] credenciais carregadas para conta {identity.get('Account')}")

    stack_name = os.environ["CFN_STACK_NAME"]
    project_name = os.environ["PROJECT_NAME"]
    cfn = _client("cloudformation")
    template_body = TEMPLATE_FILE.read_text(encoding="utf-8")
    params = [{"ParameterKey": "ProjectName", "ParameterValue": project_name}]

    try:
        _delete_stack_if_rolled_back(cfn, stack_name)
        if _stack_exists(cfn, stack_name):
            print(f"[aws] atualizando stack CloudFormation: {stack_name}")
            try:
                cfn.update_stack(StackName=stack_name, TemplateBody=template_body, Parameters=params)
                cfn.get_waiter("stack_update_complete").wait(StackName=stack_name)
            except Exception as exc:
                message = getattr(exc, "response", {}).get("Error", {}).get("Message", "")
                if "No updates are to be performed" not in message:
                    raise
                print("[aws] stack ja estava atualizada")
        else:
            print(f"[aws] criando stack CloudFormation: {stack_name}")
            cfn.create_stack(StackName=stack_name, TemplateBody=template_body, Parameters=params)
            try:
                cfn.get_waiter("stack_create_complete").wait(StackName=stack_name)
            except Exception:
                _print_recent_stack_events(cfn, stack_name)
                raise

        stack = cfn.describe_stacks(StackName=stack_name)["Stacks"][0]
    except Exception as exc:
        print("[aws] Falha no provisionamento CloudFormation.")
        print("[aws] " + _aws_error_message(exc))
        print("[aws] Garanta que a credencial tenha as permissoes CloudFormation e S3 listadas no README_EXECUCAO.md.")
        raise SystemExit(2)

    outputs = {item["OutputKey"]: item["OutputValue"] for item in stack.get("Outputs", [])}
    bucket = outputs["BucketName"]
    os.environ["S3_BUCKET"] = bucket
    print(f"[aws] bucket provisionado: s3://{bucket}")
    return bucket


def empty_bucket(bucket):
    s3 = _client("s3")
    print(f"[aws] removendo objetos de s3://{bucket}")
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if objects:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objects})


def destroy_s3_stack(bucket=None):
    stack_name = os.environ.get("CFN_STACK_NAME", "suporte-sla-entrega")
    cfn = _client("cloudformation")

    stack = _get_stack(cfn, stack_name)
    if not stack:
        print(f"[aws] stack {stack_name} nao existe; nada para destruir")
        return

    if bucket is None:
        outputs = {item["OutputKey"]: item["OutputValue"] for item in stack.get("Outputs", [])}
        bucket = outputs.get("BucketName") or os.environ.get("S3_BUCKET")

    if bucket:
        try:
            empty_bucket(bucket)
        except Exception as exc:
            print(f"[aws] aviso: nao foi possivel esvaziar o bucket automaticamente: {exc}")

    print(f"[aws] destruindo stack CloudFormation: {stack_name}")
    cfn.delete_stack(StackName=stack_name)
    waiter = cfn.get_waiter("stack_delete_complete")
    waiter.wait(StackName=stack_name)
    print("[aws] stack e bucket removidos")

