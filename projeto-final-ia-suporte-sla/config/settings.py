"""
Configuracao central do projeto.
Todos os caminhos e constantes de negocio ficam aqui para garantir reprodutibilidade.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CURATED_DIR = DATA_DIR / "curated"
WAREHOUSE_DIR = DATA_DIR / "curated"
DUCKDB_PATH = WAREHOUSE_DIR / "warehouse.duckdb"
EVID_DIR = ROOT / "evidencias"

for _d in (RAW_DIR, PROCESSED_DIR, CURATED_DIR, EVID_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SEED = 42
N_TICKETS = 8000

CHANNELS = ["Email", "Chat", "Telefone", "Formulário Web", "Redes Sociais"]
PRODUCTS = ["Plataforma Web", "App Mobile", "API", "Integrações", "Faturamento", "Relatórios"]
CATEGORIES = [
    "Acesso e Conta", "Problema Técnico", "Bug / Defeito", "Faturamento",
    "Dúvida / Como Fazer", "Solicitação de Recurso", "Cancelamento",
]
PRIORITIES = ["Baixa", "Média", "Alta", "Crítica"]
TIERS = ["Free", "Basic", "Premium", "Enterprise"]
REGIONS = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]

# SLA de resolucao (minutos) por prioridade -> define a variavel-alvo sla_breach
SLA_RESOLUTION_MINUTES = {"Crítica": 240, "Alta": 480, "Média": 1440, "Baixa": 2880}

# lexico de urgencia (ASCII; o casamento ignora acentos no process_features)
URGENCY_LEXICON = [
    "urgente", "parado", "imediato", "agora", "critico", "nao funciona",
    "perdendo", "prejuizo", "travado", "caiu", "fora do ar", "erro",
    "bloqueado", "reembolso", "cancelar", "insatisfeito", "ja",
]
