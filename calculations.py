"""
calculations.py
Regras de negócio SIMPLES do Programa Parceiro Isopor (versão básica para teste do pai).

REGRAS ATUAIS:
- 1 pacote comprado = 1 ponto
- Não existe resgate de pontos por pacotes grátis
- Única recompensa: ao atingir 500 pontos → ganha 1 Cafeteira

FUTURO (fácil de adicionar):
- Adicionar resgate de pacotes grátis (10 pontos = 1 pacote)
- Adicionar taxa por valor (R$ X = 1 ponto)
- Adicionar múltiplas opções de brinde na meta de 500
- Adicionar multiplicadores por volume
"""

import math
from datetime import date, datetime
from typing import Tuple


# ================== CONSTANTES PADRÃO ==================
MILESTONE_THRESHOLD = 500
MILESTONE_REWARD = "Cafeteira"


def get_year_month(d: date | datetime | str | None = None) -> Tuple[int, int]:
    """Retorna (ano, mês) para uma data. Aceita date, datetime, str ISO ou None (=hoje)."""
    if d is None:
        d = date.today()
    elif isinstance(d, str):
        d = datetime.fromisoformat(d).date()
    elif isinstance(d, datetime):
        d = d.date()
    return d.year, d.month


def calculate_points_from_packages(package_quantity: int) -> int:
    """
    1 pacote comprado = 1 ponto.
    """
    if package_quantity <= 0:
        return 0
    return int(package_quantity)


def format_currency(value: float) -> str:
    """Formata valor em Reais brasileiro."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_points(points: int) -> str:
    return f"{points} pt{'s' if points != 1 else ''}"


def get_milestone_progress(total_bought: int, threshold: int = 500) -> dict:
    """Retorna progresso visual para a meta de 500 pontos (pacotes comprados)."""
    if threshold <= 0:
        threshold = 500
    pct = min(100.0, (total_bought / threshold) * 100.0)
    remaining = max(0, threshold - total_bought)
    reached = total_bought >= threshold
    return {
        "total_bought": total_bought,
        "threshold": threshold,
        "percent": round(pct, 1),
        "remaining": remaining,
        "reached": reached,
        "progress_text": f"{total_bought} / {threshold}" + (f" • Faltam {remaining}" if not reached else " • META ATINGIDA!"),
    }


def get_rewards_status(current_points: int, total_packages_bought: int, rules: dict = None) -> dict:
    """Resumo simples focado apenas na meta de 500."""
    if rules is None:
        rules = {}
    milestone_threshold = rules.get("milestone_packages_threshold", 500)
    mile = get_milestone_progress(total_packages_bought, milestone_threshold)

    return {
        "milestone_500": mile,
        "summary_text": mile["progress_text"],
    }

