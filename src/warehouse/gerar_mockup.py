# -*- coding: utf-8 -*-
"""
Gera dashboard/mockup.html a partir de data/curated/dashboard/dashboard_data.json.

O painel oficial da entrega e' o do Metabase (src/bi/metabase_setup.py). Este
HTML e' a versao offline: abre com duplo clique, sem Docker e sem internet, e
serve de plano B na apresentacao e de registro nas evidencias.

Ele NAO e' um print estatico: os filtros de prioridade, categoria e canal
reagregam os numeros no navegador, a partir do cubo exportado pelo
export_dashboard.py. Os totais batem com os do Metabase porque saem dos mesmos
modelos dbt.

Uso:
    python -m src.warehouse.gerar_mockup
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from config.settings import CURATED_DIR

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESTINO = ROOT / "dashboard" / "mockup.html"
ORIGEM = CURATED_DIR / "dashboard" / "dashboard_data.json"

TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Suporte - Apoio à Decisão</title>
<!-- Chart.js versionado em dashboard/vendor: o painel abre sem internet. -->
<script src="vendor/chart.umd.min.js"></script>
<style>
  :root{--azul:#1f5fa8;--azul2:#4a90d9;--bg:#f0f3f8;--card:#fff;--txt:#243b53;
        --cinza:#5b6770;--verm:#c0392b;--verde:#27ae60;--laranja:#e67e22;--borda:#dce5f0}
  *{box-sizing:border-box;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif}
  body{margin:0;background:var(--bg);color:var(--txt)}
  header{background:var(--azul);color:#fff;padding:16px 24px}
  header h1{margin:0;font-size:18px} header p{margin:4px 0 0;font-size:13px;opacity:.9}
  .wrap{padding:18px 24px;max-width:1200px;margin:0 auto}
  .filtros{background:var(--card);border:1px solid var(--borda);border-radius:10px;
           padding:12px 14px;margin-bottom:16px;display:flex;gap:14px;align-items:flex-end;flex-wrap:wrap}
  .filtros .campo{display:flex;flex-direction:column;gap:4px}
  .filtros label{font-size:11px;color:var(--cinza);font-weight:600;text-transform:uppercase;letter-spacing:.03em}
  .filtros select{padding:7px 10px;border:1px solid var(--borda);border-radius:7px;
                  font-size:13px;color:var(--txt);background:#fff;min-width:170px}
  .filtros button{padding:8px 14px;border:1px solid var(--azul);background:#fff;color:var(--azul);
                  border-radius:7px;font-size:13px;cursor:pointer;font-weight:600}
  .filtros button:hover{background:var(--azul);color:#fff}
  .filtros .resumo{font-size:12px;color:var(--cinza);margin-left:auto;text-align:right;line-height:1.5}
  .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:16px}
  .kpi{background:var(--card);border:1px solid var(--borda);border-radius:10px;padding:14px;text-align:center}
  .kpi .v{font-size:26px;font-weight:700;color:var(--azul)}
  .kpi .l{font-size:12px;color:var(--cinza);margin-top:4px}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  .panel{background:var(--card);border:1px solid var(--borda);border-radius:10px;padding:14px}
  .panel h3{margin:0 0 10px;font-size:13.5px;color:var(--txt)}
  table{width:100%;border-collapse:collapse;font-size:12px}
  th,td{padding:6px 8px;border-bottom:1px solid #eef2f7;text-align:left}
  th{color:var(--cinza);font-weight:600}
  .badge{padding:2px 8px;border-radius:10px;color:#fff;font-size:11px}
  .full{grid-column:1/3}
  .note{font-size:12px;color:var(--cinza);margin-top:6px}
  .vazio{padding:18px;text-align:center;color:var(--cinza);font-size:13px}
</style>
</head>
<body>
<header>
  <h1>Suporte Técnico &middot; Painel de Apoio à Decisão</h1>
  <p>Previsão de violação de SLA &middot; dados do warehouse (modelos dbt) &middot;
     versão offline do painel publicado no Metabase</p>
</header>
<div class="wrap">

  <div class="filtros">
    <div class="campo"><label for="fPri">Prioridade</label><select id="fPri"></select></div>
    <div class="campo"><label for="fCat">Categoria</label><select id="fCat"></select></div>
    <div class="campo"><label for="fCan">Canal</label><select id="fCan"></select></div>
    <button id="limpar" type="button">Limpar filtros</button>
    <div class="resumo" id="resumo"></div>
  </div>

  <div class="kpis" id="kpis"></div>
  <div class="grid">
    <div class="panel"><h3>Taxa de violação de SLA por prioridade (%)</h3><canvas id="cPri" height="150"></canvas></div>
    <div class="panel"><h3>Taxa de violação por categoria (%)</h3><canvas id="cCat" height="150"></canvas></div>
    <div class="panel"><h3>Evolução mensal da violação de SLA (%)</h3><canvas id="cMes" height="150"></canvas></div>
    <div class="panel"><h3>Fila por faixa de risco previsto</h3><canvas id="cRisco" height="150"></canvas></div>
    <div class="panel full"><h3>Fila priorizada por risco (chamados a atacar agora)</h3>
      <div id="tabela"></div>
      <div class="note">Card que apoia diretamente a decisão: o gestor realoca agentes para
        estes chamados antes de o SLA estourar. Os filtros acima recortam toda a página.</div></div>
  </div>
</div>
<script>
const D = __DADOS__;

// ---------------------------------------------------------------- filtros
// O cubo traz SOMAS por (prioridade, categoria, canal, mes). Reagregar a partir
// dele da' o mesmo numero que o SQL faria no warehouse, para qualquer recorte.
const F = {priority: "", category: "", channel: ""};
const unicos = (k) => [...new Set(D.cubo.map(r => r[k]))].sort((a, b) => String(a).localeCompare(String(b), 'pt-BR'));
const ORDEM_PRI = ["Crítica", "Alta", "Média", "Baixa"];

function casa(r){
  return (!F.priority || r.priority === F.priority)
      && (!F.category || r.category === F.category)
      && (!F.channel  || r.channel  === F.channel);
}
const linhas    = () => D.cubo.filter(casa);
const linhasRis = () => D.cubo_risco.filter(casa);

function soma(rs, campo){ return rs.reduce((a, r) => a + (Number(r[campo]) || 0), 0); }

function agrupa(rs, chave){
  const m = new Map();
  rs.forEach(r => {
    const k = r[chave];
    const o = m.get(k) || {chamados: 0, violacoes: 0};
    o.chamados  += Number(r.chamados)  || 0;
    o.violacoes += Number(r.violacoes) || 0;
    m.set(k, o);
  });
  return [...m.entries()].map(([k, o]) => ({
    chave: k, chamados: o.chamados,
    taxa: o.chamados ? +(100 * o.violacoes / o.chamados).toFixed(1) : 0,
  }));
}

// ------------------------------------------------------------------ render
const fmt = n => Number(n).toLocaleString('pt-BR');
const AZ = '#1f5fa8', AZ2 = '#4a90d9', VM = '#c0392b';
const COR_RISCO = {Alto: '#c0392b', 'Médio': '#e67e22', Baixo: '#27ae60'};
const graficos = {};

function desenha(id, cfg){
  if (graficos[id]) graficos[id].destroy();
  graficos[id] = new Chart(document.getElementById(id), cfg);
}

function render(){
  const rs = linhas();
  const n  = soma(rs, 'chamados');
  const v  = soma(rs, 'violacoes');
  const nc = soma(rs, 'n_csat');

  // KPIs recalculados a partir das somas do recorte atual.
  const kpis = [
    ['Chamados', fmt(n)],
    ['Violação de SLA', n ? (100 * v / n).toFixed(1) + '%' : '—'],
    ['Tempo médio resolução', n ? (soma(rs, 'soma_resolucao_min') / n / 60).toFixed(1) + ' h' : '—'],
    ['CSAT médio', nc ? (soma(rs, 'soma_csat') / nc).toFixed(2) + ' / 5' : '—'],
  ];
  document.getElementById('kpis').innerHTML =
    kpis.map(k => `<div class="kpi"><div class="v">${k[1]}</div><div class="l">${k[0]}</div></div>`).join('');

  const porPri = agrupa(rs, 'priority').sort((a, b) => ORDEM_PRI.indexOf(a.chave) - ORDEM_PRI.indexOf(b.chave));
  desenha('cPri', {type: 'bar',
    data: {labels: porPri.map(r => r.chave), datasets: [{data: porPri.map(r => r.taxa), backgroundColor: AZ}]},
    options: {plugins: {legend: {display: false}}, scales: {y: {beginAtZero: true}}}});

  const porCat = agrupa(rs, 'category').sort((a, b) => b.taxa - a.taxa);
  desenha('cCat', {type: 'bar',
    data: {labels: porCat.map(r => r.chave), datasets: [{data: porCat.map(r => r.taxa), backgroundColor: AZ2}]},
    options: {indexAxis: 'y', plugins: {legend: {display: false}}, scales: {x: {beginAtZero: true}}}});

  const porMes = agrupa(rs, 'mes').sort((a, b) => a.chave - b.chave);
  desenha('cMes', {type: 'line',
    data: {labels: porMes.map(r => r.chave), datasets: [{data: porMes.map(r => r.taxa),
           borderColor: VM, backgroundColor: VM, tension: .3}]},
    options: {plugins: {legend: {display: false}}}});

  const ordemRisco = {Alto: 1, 'Médio': 2, Baixo: 3};
  const porRisco = agrupa(linhasRis(), 'faixa_risco').sort((a, b) => ordemRisco[a.chave] - ordemRisco[b.chave]);
  desenha('cRisco', {type: 'bar',
    data: {labels: porRisco.map(r => r.chave), datasets: [{data: porRisco.map(r => r.chamados),
           backgroundColor: porRisco.map(r => COR_RISCO[r.chave] || '#5b6770')}]},
    options: {plugins: {legend: {display: false}}, scales: {y: {beginAtZero: true}}}});

  // Tabela da fila priorizada, recortada pelos mesmos filtros.
  const fila = D.top_risco.filter(casa).slice(0, 12);
  document.getElementById('tabela').innerHTML = fila.length
    ? '<table><tr><th>Chamado</th><th>Prioridade</th><th>Categoria</th><th>Canal</th>'
      + '<th>Produto</th><th>Tier</th><th>Prob. violação</th></tr>'
      + fila.map(r => `<tr><td>${r.ticket_id}</td><td>${r.priority}</td><td>${r.category}</td>`
        + `<td>${r.channel}</td><td>${r.product}</td><td>${r.customer_tier}</td>`
        + `<td><span class="badge" style="background:#c0392b">${(r.prob_violacao * 100).toFixed(0)}%</span></td></tr>`).join('')
      + '</table>'
    : '<div class="vazio">Nenhum chamado de risco alto neste recorte.</div>';

  const ativos = Object.entries(F).filter(([, x]) => x).length;
  document.getElementById('resumo').innerHTML = ativos
    ? `<b>${ativos} filtro(s) ativo(s)</b><br>${fmt(n)} de ${fmt(D.kpis.total_chamados)} chamados`
    : `sem filtro<br>${fmt(n)} chamados`;
}

// ------------------------------------------------------------------- setup
[['fPri', 'priority', 'Todas as prioridades'],
 ['fCat', 'category', 'Todas as categorias'],
 ['fCan', 'channel',  'Todos os canais']].forEach(([id, campo, rotulo]) => {
  const sel = document.getElementById(id);
  let vals = unicos(campo);
  if (campo === 'priority') vals = ORDEM_PRI.filter(p => vals.includes(p));
  sel.innerHTML = `<option value="">${rotulo}</option>`
    + vals.map(v => `<option value="${v}">${v}</option>`).join('');
  sel.addEventListener('change', e => { F[campo] = e.target.value; render(); });
});
document.getElementById('limpar').addEventListener('click', () => {
  Object.keys(F).forEach(k => F[k] = "");
  document.querySelectorAll('.filtros select').forEach(s => s.value = "");
  render();
});
render();
</script>
</body>
</html>
"""


def run():
    if not ORIGEM.exists():
        raise SystemExit(f"[mockup] {ORIGEM} nao encontrado. "
                         f"Rode antes: python -m src.warehouse.export_dashboard")
    dados = json.loads(ORIGEM.read_text(encoding="utf-8"))
    # Compacto no HTML (sem indentacao) para o arquivo abrir instantaneamente;
    # o JSON de data/curated continua legivel.
    inline = json.dumps(dados, ensure_ascii=False, separators=(",", ":"), default=str)
    DESTINO.write_text(TEMPLATE.replace("__DADOS__", inline), encoding="utf-8")
    kb = DESTINO.stat().st_size / 1024
    print(f"[mockup] {DESTINO} gerado ({kb:.0f} KB, {len(dados['cubo'])} linhas de cubo)")
    print(f"[mockup] filtros: prioridade, categoria e canal (reagregacao no navegador)")
    return {"arquivo": str(DESTINO)}


if __name__ == "__main__":
    run()
