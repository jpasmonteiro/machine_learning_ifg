"""
Gera uma imagem (PNG) do dashboard de apoio a decisao, a partir do JSON
exportado dos marts. Usada no relatorio e na apresentacao. O dashboard
"de verdade" e' o Metabase conectado ao warehouse (ver README_metabase.md).
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from config.settings import CURATED_DIR, EVID_DIR

AZUL = "#1f5fa8"; AZUL2 = "#4a90d9"; CINZA = "#5b6770"; VERM = "#c0392b"; VERDE = "#27ae60"


def card(ax, titulo, valor, sub=""):
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                 facecolor="#f4f7fb", edgecolor="#d6e0ee", lw=1.2))
    ax.text(0.5, 0.62, valor, ha="center", va="center", fontsize=22,
            fontweight="bold", color=AZUL, transform=ax.transAxes)
    ax.text(0.5, 0.26, titulo, ha="center", va="center", fontsize=9.5,
            color=CINZA, transform=ax.transAxes)
    if sub:
        ax.text(0.5, 0.08, sub, ha="center", va="center", fontsize=8,
                color=CINZA, transform=ax.transAxes)


def run():
    d = json.load(open(CURATED_DIR / "dashboard" / "dashboard_data.json", encoding="utf-8"))
    k = d["kpis"]
    fig = plt.figure(figsize=(14, 9.2), facecolor="white")
    gs = GridSpec(4, 4, figure=fig, height_ratios=[0.7, 1, 1, 1], hspace=0.55, wspace=0.3)
    fig.suptitle("Suporte Técnico - Painel de Apoio à Decisão (previsão de violação de SLA)",
                 fontsize=15, fontweight="bold", color="#243b53", x=0.5, y=0.975)

    # KPIs
    card(fig.add_subplot(gs[0, 0]), "Chamados", f"{int(k['total_chamados']):,}".replace(",", "."))
    card(fig.add_subplot(gs[0, 1]), "Violação de SLA", f"{k['taxa_violacao_pct']:.1f}%")
    card(fig.add_subplot(gs[0, 2]), "Tempo médio resolução", f"{k['tempo_medio_resolucao_min']/60:.1f} h")
    card(fig.add_subplot(gs[0, 3]), "CSAT médio", f"{k['csat_medio']:.2f} / 5")

    # violacao por prioridade
    ax = fig.add_subplot(gs[1, 0:2])
    pr = d["por_prioridade"]
    ax.bar([r["priority"] for r in pr], [r["taxa_violacao_pct"] for r in pr], color=AZUL)
    ax.set_title("Taxa de violação de SLA por prioridade (%)", fontsize=10, fontweight="bold")
    ax.set_ylabel("%"); ax.grid(axis="y", alpha=0.25)
    for i, r in enumerate(pr):
        ax.text(i, r["taxa_violacao_pct"] + 1, f"{r['taxa_violacao_pct']:.0f}", ha="center", fontsize=8)

    # violacao por categoria
    ax = fig.add_subplot(gs[1, 2:4])
    cat = sorted(d["por_categoria"], key=lambda r: r["taxa_violacao_pct"])
    ax.barh([r["category"] for r in cat], [r["taxa_violacao_pct"] for r in cat], color=AZUL2)
    ax.set_title("Taxa de violação por categoria (%)", fontsize=10, fontweight="bold")
    ax.grid(axis="x", alpha=0.25); ax.tick_params(labelsize=8)

    # serie por mes
    ax = fig.add_subplot(gs[2, 0:2])
    mes = d["por_mes"]
    ax.plot([r["mes"] for r in mes], [r["taxa_violacao_pct"] for r in mes], marker="o", color=VERM)
    ax.set_title("Evolução mensal da violação de SLA (%)", fontsize=10, fontweight="bold")
    ax.set_xlabel("Mês"); ax.grid(alpha=0.25)

    # distribuicao de risco
    ax = fig.add_subplot(gs[2, 2:4])
    ri = d["distribuicao_risco"]
    cores = {"Alto": VERM, "Médio": "#e67e22", "Baixo": VERDE}
    ax.bar([r["faixa_risco"] for r in ri], [r["chamados"] for r in ri],
           color=[cores.get(r["faixa_risco"], CINZA) for r in ri])
    ax.set_title("Fila por faixa de risco previsto (conjunto de teste)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Chamados"); ax.grid(axis="y", alpha=0.25)

    # matriz de confusao
    ax = fig.add_subplot(gs[3, 0:2])
    cm = np.zeros((2, 2), dtype=int)
    for r in d["matriz_confusao"]:
        cm[int(r["real"]), int(r["previsto"])] = int(r["n"])
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(["Não viola", "Viola"]); ax.set_yticklabels(["Não viola", "Viola"])
    ax.set_xlabel("Previsto"); ax.set_ylabel("Real")
    ax.set_title(f"Matriz de confusão - {d['modelo_producao']}", fontsize=10, fontweight="bold")
    for (r, c), v in np.ndenumerate(cm):
        ax.text(c, r, str(v), ha="center", va="center",
                color="white" if v > cm.max()/2 else "black", fontsize=11)

    # metricas do modelo
    ax = fig.add_subplot(gs[3, 2:4]); ax.axis("off")
    m = d["metricas_modelo"][d["modelo_producao"]]
    linhas = [f"Modelo de produção: {d['modelo_producao']}",
              f"Acurácia:  {m['accuracy']:.3f}",
              f"Precisão:  {m['precision']:.3f}",
              f"Recall:    {m['recall']:.3f}",
              f"F1-score:  {m['f1']:.3f}",
              f"ROC-AUC:   {m['roc_auc']:.3f}"]
    ax.text(0.02, 0.95, "Desempenho do modelo", fontsize=11, fontweight="bold",
            color="#243b53", va="top")
    ax.text(0.02, 0.74, "\n".join(linhas), fontsize=10, family="monospace",
            color="#243b53", va="top")

    fig.savefig(EVID_DIR / "dashboard_mockup.png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"[dashboard] imagem -> {EVID_DIR/'dashboard_mockup.png'}")


if __name__ == "__main__":
    run()
