# Entrega - Projeto Final IA Suporte SLA

Reunimos nesta pasta os artefatos finais do projeto: código executável, relatório, apresentação e
roteiro para a apresentação gravada.

## Conteúdo

- `codigo/`: arquivos necessários para executar o trabalho localmente, incluindo os dados brutos em `codigo/data/raw/`.
- `codigo/README_EXECUCAO.md`: instruções completas de instalação, execução e validação.
- `relatorio/Projeto_Final.pdf`: relatório final em PDF.
- `relatorio/Relatorio_Projeto_Final.docx`: relatório em versão editável.
- `apresentacao/Apresentacao_Projeto_Final.pptx`: apresentação do projeto.
- `apresentacao/README_ROTEIRO_APRESENTACAO.md`: storytelling, sequência, falas e frases-chave da apresentação gravada.

## Link do repositório

Repositório com códigos, instruções de execução, documentação técnica, relatório e evidências:

```text
https://github.com/jpasmonteiro/machine_learning_ifg/tree/main/projeto-final-ia-suporte-sla
```

## Como validar rapidamente

Para executar o pipeline completo localmente, primeiro crie `codigo/.env-aws` a partir de
`codigo/.env-aws.example` com as credenciais AWS. A execução exige CloudFormation + S3.

Depois execute:

```bash
cd codigo
make run
```

Ao final da execução, o pipeline usa os dados brutos já incluídos na entrega, provisiona um bucket
S3 via CloudFormation, gera atributos, modelos, warehouse DuckDB, modelos dbt, métricas,
evidências, dados do dashboard, envia as camadas para o S3 e destrói o bucket/stack na limpeza
final.

## Resultado entregue

O projeto implementa uma solução de apoio à decisão para prever risco de violação de SLA em chamados
de suporte técnico. A entrega cobre ingestão de dados, processamento, modelagem dbt, aprendizagem de
máquina, validação em nuvem com Amazon S3, evidências e dashboard para priorização da fila.
