# Como subir este projeto no GitHub

Duas formas. A **Forma 1 não exige instalar nada** — recomendada se você nunca usou Git.

---

## Forma 1 — Pelo site do GitHub (mais fácil)

1. Acesse **https://github.com/new**
2. Preencha:
   - **Repository name:** `projeto-final-ia-suporte-sla`
   - **Description:** `Pipeline de dados em nuvem para ML - previsão de violação de SLA (IFG Pós-IA)`
   - Marque **Private** (recomendado até entregar) ou **Public**
   - **NÃO** marque "Add a README file" (já temos um)
3. Clique em **Create repository**
4. Na página que abrir, clique em **"uploading an existing file"**
   (ou vá em **Add file → Upload files**)
5. **Arraste a pasta inteira** `projeto-final-ia-suporte-sla` para a área de upload
   (o navegador sobe todas as subpastas)
6. Em "Commit changes", escreva: `Projeto final - pipeline ELT + ML (KNN/SVM/MLP)`
7. Clique em **Commit changes**

Pronto. O README aparece formatado na página inicial do repositório.

### Dar acesso ao grupo
No repositório: **Settings → Collaborators → Add people** e convide os colegas
pelo usuário/e-mail do GitHub. Assim todos podem editar.

---

## Forma 2 — Pelo terminal (Git)

Requer o Git instalado (https://git-scm.com/downloads).

```bash
# 1. entre na pasta do projeto
cd caminho/para/projeto-final-ia-suporte-sla

# 2. inicialize e faça o primeiro commit
git init
git add .
git commit -m "Projeto final - pipeline ELT + ML (KNN/SVM/MLP)"

# 3. crie o repositório vazio no site (https://github.com/new) e conecte:
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/projeto-final-ia-suporte-sla.git
git push -u origin main
```

> Se pedir senha, use um **Personal Access Token** em vez da senha da conta
> (GitHub → Settings → Developer settings → Personal access tokens).

---

## Depois: como o grupo trabalha nele

```bash
# cada um baixa uma vez
git clone https://github.com/SEU-USUARIO/projeto-final-ia-suporte-sla.git
cd projeto-final-ia-suporte-sla
pip install -r requirements.txt
python run_pipeline.py          # gera os dados e roda tudo (~7s)

# ao mexer em algo
git add .
git commit -m "descreva o que mudou"
git push

# para pegar as mudanças dos outros
git pull
```

---

## O que já está configurado

- **`.gitignore`**: os dados gerados (`data/`) **não** vão para o Git, porque são
  reproduzíveis — basta rodar `python run_pipeline.py` para recriá-los em ~7 segundos.
  Isso mantém o repositório leve (1,6 MB) e é boa prática.
- **`evidencias/`**: vai para o Git (métricas, matriz de confusão, curva ROC e
  print do dashboard), pois o enunciado pede evidências de execução.
- **`docs/`**: contém o relatório (.docx), a apresentação (.pptx), o dicionário de
  dados, o checklist de requisitos e os guias do grupo.

## Dica de organização

Se quiserem que os slides e o relatório apareçam com destaque, deixem um link
para eles no topo do `README.md`, por exemplo:

```markdown
📊 [Apresentação](docs/Apresentacao_Projeto_Final.pptx) · 📄 [Relatório](docs/Relatorio_Projeto_Final.docx)
```
