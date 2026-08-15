"""
Gera o diagrama da arquitetura equivalente 100% em AWS (PNG + SVG).
Conforme item 4.5 do enunciado.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

LARANJA = "#ec7211"  # cor AWS
AZUL = "#2563eb"; ROXO = "#7c3aed"; VERDE = "#16a34a"; CINZA = "#475569"

def box(ax, x, y, w, h, titulo, sub="", cor=LARANJA, fc="#fff7ef"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                 linewidth=1.6, edgecolor=cor, facecolor=fc))
    ax.text(x + w/2, y + h*0.62, titulo, ha="center", va="center",
            fontsize=9.2, fontweight="bold", color="#1f2937")
    if sub:
        ax.text(x + w/2, y + h*0.26, sub, ha="center", va="center",
                fontsize=7.4, color=CINZA)

def arrow(ax, x1, y1, x2, y2, cor=CINZA):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                 mutation_scale=13, linewidth=1.4, color=cor))

fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")
ax.text(8, 8.6, "Arquitetura equivalente 100% em AWS - Pipeline de Suporte Técnico",
        ha="center", fontsize=14, fontweight="bold", color="#0f172a")

# Banda de orquestracao (topo)
ax.add_patch(FancyBboxPatch((0.4, 7.2), 15.2, 0.9, boxstyle="round,pad=0.02,rounding_size=0.05",
             linewidth=1.4, edgecolor=ROXO, facecolor="#f5f3ff"))
ax.text(8, 7.65, "Orquestração - Amazon MWAA (Apache Airflow gerenciado): agenda e encadeia todas as etapas",
        ha="center", va="center", fontsize=9, fontweight="bold", color=ROXO)

# Fluxo principal (linha do meio)
y = 4.6; h = 1.1
box(ax, 0.4, y, 1.9, h, "Fontes", "chamados, textos, logs", cor=CINZA, fc="#f1f5f9")
box(ax, 2.7, y, 2.0, h, "AWS Lambda", "ingestão", cor=LARANJA)
box(ax, 5.1, y, 2.0, h, "Amazon S3", "raw / processed / curated", cor=VERDE, fc="#f0fdf4")
box(ax, 7.5, y, 2.0, h, "Snowflake", "carga analítica", cor=AZUL, fc="#eff6ff")
box(ax, 9.9, y, 2.0, h, "dbt", "staging/dims/facts + testes", cor=AZUL, fc="#eff6ff")
box(ax, 12.3, y, 1.7, h, "Amazon SageMaker", "treino e inferência ML", cor=LARANJA)
box(ax, 14.2, y, 1.4, h, "Metabase", "EC2 / ECS", cor=VERDE, fc="#f0fdf4")

xs = [2.3, 2.7, 4.7, 5.1, 7.1, 7.5, 9.5, 9.9, 11.9, 12.3, 14.0, 14.2]
pairs = [(2.3,2.7),(4.7,5.1),(7.1,7.5),(9.5,9.9),(11.9,12.3),(14.0,14.2)]
for x1, x2 in pairs:
    arrow(ax, x1, y + h/2, x2, y + h/2)

# setas da orquestracao descendo para cada etapa
for cx in [3.7, 6.1, 8.5, 10.9, 13.15]:
    arrow(ax, cx, 7.2, cx, y + h, cor=ROXO)

ax.text(5.8, 3.85, "Camadas do data lake no S3: raw (bronze) -> processed (silver) -> curated (gold)",
        ha="center", fontsize=8.2, color=CINZA, style="italic")

# Banda inferior (esquerda/centro): monitoramento, seguranca e IaC
box(ax, 0.4, 2.45, 3.5, 0.95, "Amazon CloudWatch", "logs e métricas (monitoramento)", cor=LARANJA, fc="#fff7ef")
box(ax, 4.05, 2.45, 3.5, 0.95, "AWS IAM + KMS", "permissões e criptografia", cor=LARANJA, fc="#fff7ef")
box(ax, 7.7, 2.45, 3.6, 0.95, "AWS CloudFormation", "infra como código (YAML)", cor=LARANJA, fc="#fff7ef")

# Consumidor da decisao: logo abaixo do Metabase, com seta VERTICAL limpa
box(ax, 11.95, 2.45, 3.65, 0.95, "Gestor de Suporte", "prioriza a fila pelo risco de SLA", cor=VERDE, fc="#ecfdf5")
arrow(ax, 14.9, y, 14.9, 3.40, cor=VERDE)

out = pathlib.Path(__file__).resolve().parent
fig.savefig(out / "arquitetura_aws.png", dpi=140, bbox_inches="tight")
fig.savefig(out / "arquitetura_aws.svg", bbox_inches="tight")
print("diagrama salvo em infra/arquitetura_aws.png e .svg")
