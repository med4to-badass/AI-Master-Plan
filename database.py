"""
database.py
Camada de persistência SQLite para o Programa Parceiro Isopor.

Tabelas:
- clients
- purchases
- redemptions

Todas as regras de cálculo são aplicadas aqui (usando calculations.py).
Fornece views enriquecidas de clientes com pontos, volume mensal, pacotes etc.
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import math

from calculations import (
    calculate_points_from_packages,
    get_year_month,
)


DB_PATH = Path(__file__).parent / "isopor_parceiro.db"


def get_conn() -> sqlite3.Connection:
    """Conexão com row factory para dicionários fáceis."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Cria as tabelas se não existirem."""
    conn = get_conn()
    try:
        conn.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now', '-3 hours'))
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            purchase_date TEXT NOT NULL,
            amount REAL NOT NULL,
            base_points INTEGER NOT NULL,
            multiplier REAL NOT NULL,
            final_points INTEGER NOT NULL,
            package_quantity INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', '-3 hours')),
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            redemption_date TEXT NOT NULL,
            points_redeemed INTEGER NOT NULL DEFAULT 10,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', '-3 hours')),
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_purchases_client_date ON purchases(client_id, purchase_date);
        CREATE INDEX IF NOT EXISTS idx_redemptions_client_date ON redemptions(client_id, redemption_date);

        -- Tabela de configurações personalizáveis pelo administrador
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT
        );

        -- Nova tabela para recompensas de marco (ex: 500 pacotes comprados)
        CREATE TABLE IF NOT EXISTS milestone_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            reward_date TEXT NOT NULL,
            milestone TEXT NOT NULL,           -- ex: "500_pacotes"
            reward_choice TEXT NOT NULL,       -- "cafeteira" (simples por enquanto)
            reward_description TEXT,           -- rótulo bonito do brinde escolhido
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', '-3 hours')),
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_milestone_client ON milestone_rewards(client_id, reward_date);

        -- Mural de atualizações (avisos para admin e portal do cliente)
        CREATE TABLE IF NOT EXISTS bulletin_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            show_to_clients INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now', '-3 hours')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', '-3 hours'))
        );
        CREATE INDEX IF NOT EXISTS idx_bulletin_active ON bulletin_updates(is_active, show_to_clients);

        -- Histórico de alterações manuais feitas pelo admin
        CREATE TABLE IF NOT EXISTS settings_changelog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            label TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT NOT NULL,
            changed_at TEXT NOT NULL DEFAULT (datetime('now', '-3 hours'))
        );
        """)
        conn.commit()
    finally:
        conn.close()

    # Migração segura para DBs existentes (adiciona coluna de quantidade de pacotes)
    _migrate_add_package_quantity()
    _migrate_create_milestone_table()
    _migrate_create_bulletin_table()
    _migrate_create_settings_changelog()
    _migrate_purge_legacy_multiplier_settings()


def _migrate_add_package_quantity() -> None:
    """Adiciona coluna package_quantity em DBs legados (idempotente)."""
    conn = get_conn()
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(purchases)").fetchall()]
        if "package_quantity" not in cols:
            conn.execute("ALTER TABLE purchases ADD COLUMN package_quantity INTEGER NOT NULL DEFAULT 0")
            conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def _migrate_create_milestone_table() -> None:
    """Garante a tabela de milestone_rewards em DBs antigos."""
    conn = get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS milestone_rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                reward_date TEXT NOT NULL,
                milestone TEXT NOT NULL,
                reward_choice TEXT NOT NULL,
                reward_description TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', '-3 hours')),
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_milestone_client ON milestone_rewards(client_id, reward_date)")
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def _migrate_create_settings_changelog() -> None:
    """Garante a tabela de histórico de alterações em DBs antigos."""
    conn = get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings_changelog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                label TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT NOT NULL,
                changed_at TEXT NOT NULL DEFAULT (datetime('now', '-3 hours'))
            )
        """)
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def _migrate_create_bulletin_table() -> None:
    """Garante a tabela de mural de atualizações em DBs antigos."""
    conn = get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bulletin_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                show_to_clients INTEGER NOT NULL DEFAULT 1,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now', '-3 hours')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', '-3 hours'))
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_bulletin_active ON bulletin_updates(is_active, show_to_clients)"
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def _migrate_purge_legacy_multiplier_settings() -> None:
    """Remove chaves legadas de multiplicadores/bônus por faixa do app_settings.
    Mantém apenas as regras reais + marco de volume + textos.
    Idempotente e seguro.
    """
    legacy_keys = [
        "tier1_max", "tier2_max",
        "multiplier_1x", "multiplier_1_5x", "multiplier_2x",
        "card_show_multiplier",  # não é mais usado
    ]
    conn = get_conn()
    try:
        for key in legacy_keys:
            conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def _compute_client_stats(conn: sqlite3.Connection, client_id: int, today: Optional[date] = None) -> Dict[str, Any]:
    """Calcula estatísticas derivadas de um cliente (pontos, volume, pacotes etc)."""
    if today is None:
        today = date.today()

    cur = conn.cursor()

    # Todos os purchases do cliente (inclui quantidade de pacotes agora)
    purchases = cur.execute("""
        SELECT id, purchase_date, amount, final_points, COALESCE(package_quantity, 0) as package_quantity
        FROM purchases 
        WHERE client_id = ?
        ORDER BY purchase_date
    """, (client_id,)).fetchall()

    # Versão simples: sem resgate de pontos
    # current_points = total de pontos ganhos (1 por pacote comprado)
    total_earned = sum(row["final_points"] for row in purchases)
    current_points = total_earned  # sem subtração de resgates

    # Sem pacotes disponíveis por resgate
    available_packages = 0

    # Volume total lifetime
    total_spent = sum(row["amount"] for row in purchases)

    # Total de pacotes COMPRADOS (nova métrica para marco de 500)
    total_packages_bought = sum(int(row["package_quantity"] or 0) for row in purchases)

    # Volume do mês atual (informação útil, sem qualquer efeito em pontos)
    year, month = get_year_month(today)
    month_str_prefix = f"{year}-{month:02d}"

    monthly_spent = sum(
        row["amount"] for row in purchases
        if row["purchase_date"].startswith(month_str_prefix)
    )

    # Volume do mês anterior (para comparações)
    prev_year = year if month > 1 else year - 1
    prev_month = month - 1 if month > 1 else 12
    prev_prefix = f"{prev_year}-{prev_month:02d}"
    prev_monthly_spent = sum(
        row["amount"] for row in purchases
        if row["purchase_date"].startswith(prev_prefix)
    )

    # Última compra
    last_purchase_date = purchases[-1]["purchase_date"] if purchases else None

    # Verifica se o cliente já resgatou a recompensa do marco de 500 pacotes
    rules = get_program_rules()
    milestone_threshold = int(rules.get("milestone_packages_threshold", 500)) if "milestone_packages_threshold" in rules else 500
    milestone_claim = cur.execute(
        "SELECT reward_choice, reward_description, reward_date FROM milestone_rewards WHERE client_id = ? AND milestone = '500_pacotes' ORDER BY id DESC LIMIT 1",
        (client_id,)
    ).fetchone()
    has_milestone_500 = milestone_claim is not None
    milestone_500_choice = milestone_claim["reward_choice"] if milestone_claim else None
    milestone_500_desc = milestone_claim["reward_description"] if milestone_claim else None
    milestone_500_date = milestone_claim["reward_date"] if milestone_claim else None

    return {
        "current_points": current_points,
        "available_packages": available_packages,
        "total_spent": total_spent,
        "monthly_spent": monthly_spent,
        "prev_monthly_spent": prev_monthly_spent,
        "last_purchase_date": last_purchase_date,
        "total_earned_points": total_earned,
        # Sem resgates na versão simples
        "total_redeemed_points": 0,
        # Métricas da meta de 500 pontos
        "total_packages_bought": total_packages_bought,
        "has_milestone_500": has_milestone_500,
        "milestone_500_choice": milestone_500_choice,
        "milestone_500_desc": milestone_500_desc,
        "milestone_500_date": milestone_500_date,
        "milestone_packages_threshold": milestone_threshold,
    }


def get_all_clients_enriched(today: Optional[date] = None) -> List[Dict[str, Any]]:
    """Retorna todos os clientes com todas as métricas calculadas."""
    if today is None:
        today = date.today()

    conn = get_conn()
    try:
        rows = conn.execute("SELECT id, name, phone, created_at FROM clients ORDER BY name").fetchall()
        clients = []
        for row in rows:
            stats = _compute_client_stats(conn, row["id"], today)
            clients.append({
                "id": row["id"],
                "name": row["name"],
                "phone": row["phone"],
                "created_at": row["created_at"],
                **stats
            })
        return clients
    finally:
        conn.close()


def get_client_by_id(client_id: int, today: Optional[date] = None) -> Optional[Dict[str, Any]]:
    """Cliente único enriquecido."""
    if today is None:
        today = date.today()

    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, name, phone, created_at FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
        if not row:
            return None
        stats = _compute_client_stats(conn, row["id"], today)
        return {
            "id": row["id"],
            "name": row["name"],
            "phone": row["phone"],
            "created_at": row["created_at"],
            **stats
        }
    finally:
        conn.close()


def search_clients(query: str, today: Optional[date] = None) -> List[Dict[str, Any]]:
    """Busca case-insensitive por nome ou telefone."""
    if today is None:
        today = date.today()

    q = f"%{query.strip().lower()}%"
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT id, name, phone, created_at 
            FROM clients 
            WHERE LOWER(name) LIKE ? OR LOWER(phone) LIKE ?
            ORDER BY name
        """, (q, q)).fetchall()

        clients = []
        for row in rows:
            stats = _compute_client_stats(conn, row["id"], today)
            clients.append({
                "id": row["id"],
                "name": row["name"],
                "phone": row["phone"],
                "created_at": row["created_at"],
                **stats
            })
        return clients
    finally:
        conn.close()


def add_client(name: str, phone: str) -> int:
    """Cria novo cliente. Retorna o ID."""
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO clients (name, phone) VALUES (?, ?)",
            (name.strip(), phone.strip())
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def register_purchase(
    client_id: int,
    amount: float,
    purchase_date: Optional[date] = None,
    notes: str = "",
    package_quantity: int = 0,
) -> Dict[str, Any]:
    """
    Registra uma compra aplicando TODAS as regras corretamente.
    Agora também registra quantos pacotes físicos foram comprados (para o marco de 500).
    Retorna dict com os pontos calculados e informações.
    """
    if purchase_date is None:
        purchase_date = date.today()

    date_str = purchase_date.isoformat()

    conn = get_conn()
    try:
        qty = max(0, int(package_quantity or 0))

        # VERSÃO SIMPLES: 1 pacote = 1 ponto
        # points = quantidade de pacotes comprados diretamente
        final_points = qty
        base_points = qty

        # Mantemos o campo multiplier por compatibilidade com o schema antigo.
        # TODO para futuro: se adicionar multiplicador, calcular aqui e gravar.
        conn.execute("""
            INSERT INTO purchases 
            (client_id, purchase_date, amount, base_points, multiplier, final_points, package_quantity, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (client_id, date_str, amount, base_points, 1.0, final_points, qty, notes.strip()))

        conn.commit()

        # Retornar resumo simples
        return {
            "final_points": final_points,
            "package_quantity": qty,
            "date": date_str,
            "amount": amount,
        }
    finally:
        conn.close()


# RESGATE REMOVIDO na versão simples
# Não existe mais "10 pontos = 1 pacote grátis"
# def redeem_packages(...):
#     raise NotImplementedError("Resgate removido nesta versão simples. Apenas a meta de 500 pontos existe.")


def claim_milestone_reward(
    client_id: int,
    milestone: str = "500_pacotes",
    reward_choice: str = "cafeteira",
    reward_description: str = "Cafeteira",
    notes: str = "",
) -> Dict[str, Any]:
    """
    Registra a concessão de uma recompensa especial de marco (ex: 500 pacotes).
    O cliente escolhe entre desconto, pix ou brinde físico.
    Retorna resumo da operação.
    """
    today_str = date.today().isoformat()

    conn = get_conn()
    try:
        # Evita duplicado para o mesmo marco (um cliente só ganha 1x)
        already = conn.execute(
            "SELECT id FROM milestone_rewards WHERE client_id = ? AND milestone = ?",
            (client_id, milestone)
        ).fetchone()
        if already:
            raise ValueError("Este cliente já recebeu a recompensa deste marco.")

        conn.execute("""
            INSERT INTO milestone_rewards 
            (client_id, reward_date, milestone, reward_choice, reward_description, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (client_id, today_str, milestone, reward_choice, reward_description, notes.strip()))

        conn.commit()

        return {
            "milestone": milestone,
            "reward_choice": reward_choice,
            "reward_description": reward_description,
            "date": today_str,
        }
    finally:
        conn.close()


def get_client_history(client_id: int) -> List[Dict[str, Any]]:
    """
    Histórico unificado (compras + resgates + recompensas de marco).
    Tipos: 'purchase', 'redemption', 'milestone_reward'.
    """
    conn = get_conn()
    try:
        purchases = conn.execute("""
            SELECT 
                'purchase' as type,
                purchase_date as tx_date,
                amount,
                final_points as points,
                multiplier,
                COALESCE(package_quantity, 0) as package_quantity,
                notes,
                id
            FROM purchases
            WHERE client_id = ?
        """, (client_id,)).fetchall()

        redemptions = conn.execute("""
            SELECT 
                'redemption' as type,
                redemption_date as tx_date,
                NULL as amount,
                -points_redeemed as points,
                NULL as multiplier,
                0 as package_quantity,
                notes,
                id
            FROM redemptions
            WHERE client_id = ?
        """, (client_id,)).fetchall()

        milestones = conn.execute("""
            SELECT 
                'milestone_reward' as type,
                reward_date as tx_date,
                NULL as amount,
                0 as points,
                NULL as multiplier,
                0 as package_quantity,
                ('Recompensa 500 pacotes: ' || COALESCE(reward_description, reward_choice)) as notes,
                id
            FROM milestone_rewards
            WHERE client_id = ?
        """, (client_id,)).fetchall()

        history = []
        for p in purchases:
            history.append({
                "type": "purchase",
                "date": p["tx_date"],
                "amount": p["amount"],
                "points": p["points"],
                "multiplier": p["multiplier"],
                "package_quantity": int(p["package_quantity"] or 0),
                "notes": p["notes"] or "",
                "id": p["id"]
            })
        for r in redemptions:
            history.append({
                "type": "redemption",
                "date": r["tx_date"],
                "amount": None,
                "points": r["points"],
                "multiplier": None,
                "package_quantity": 0,
                "notes": r["notes"] or "",
                "id": r["id"]
            })
        for m in milestones:
            history.append({
                "type": "milestone_reward",
                "date": m["tx_date"],
                "amount": None,
                "points": 0,
                "multiplier": None,
                "package_quantity": 0,
                "notes": m["notes"] or "",
                "id": m["id"]
            })

        # Ordena por data desc + id desc (mais recente primeiro)
        history.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
        return history
    finally:
        conn.close()


def get_dashboard_kpis(today: Optional[date] = None) -> Dict[str, Any]:
    """KPIs principais para os cards do topo."""
    if today is None:
        today = date.today()

    conn = get_conn()
    try:
        clients = conn.execute("SELECT COUNT(*) as total FROM clients").fetchone()["total"]

        # Pontos distribuídos hoje
        today_str = today.isoformat()
        points_today = conn.execute("""
            SELECT COALESCE(SUM(final_points), 0) as pts
            FROM purchases
            WHERE purchase_date = ?
        """, (today_str,)).fetchone()["pts"]

        # Pacotes resgatados este mês
        year, month = get_year_month(today)
        month_prefix = f"{year}-{month:02d}%"
        packages_this_month = conn.execute("""
            SELECT COALESCE(SUM(points_redeemed), 0) / 10 as pkgs
            FROM redemptions
            WHERE redemption_date LIKE ?
        """, (month_prefix,)).fetchone()["pkgs"] or 0

        # Volume total este mês
        volume_this_month = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) as vol
            FROM purchases
            WHERE purchase_date LIKE ?
        """, (month_prefix,)).fetchone()["vol"] or 0

        # Pontos em circulação (todos os clientes)
        # Soma de todos os pontos já ganhos - resgatados
        total_earned = conn.execute("SELECT COALESCE(SUM(final_points), 0) FROM purchases").fetchone()[0]
        total_redeemed = conn.execute("SELECT COALESCE(SUM(points_redeemed), 0) FROM redemptions").fetchone()[0]
        circulating_points = max(0, total_earned - total_redeemed)

        # Versão simples: sem pacotes por resgate
        # Contamos clientes que já atingiram a meta
        milestone_clients = sum(1 for c in get_all_clients_enriched() if c.get("has_milestone_500"))

        return {
            "total_clients": clients,
            "points_today": points_today,
            "packages_redeemed_month": int(packages_this_month),
            "volume_month": volume_this_month,
            "circulating_points": circulating_points,
            "milestone_clients": milestone_clients,
        }
    finally:
        conn.close()


def get_monthly_purchase_history(months_back: int = 6) -> List[Dict[str, Any]]:
    """Histórico mensal agregado para gráficos (últimos N meses)."""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT 
                strftime('%Y-%m', purchase_date) as month,
                SUM(amount) as volume,
                SUM(final_points) as points_awarded,
                COUNT(*) as num_purchases
            FROM purchases
            GROUP BY month
            ORDER BY month DESC
            LIMIT ?
        """, (months_back,)).fetchall()

        # Reverter para ordem cronológica
        data = []
        for r in reversed(rows):
            data.append({
                "month": r["month"],
                "volume": r["volume"] or 0,
                "points_awarded": r["points_awarded"] or 0,
                "num_purchases": r["num_purchases"]
            })
        return data
    finally:
        conn.close()


def get_top_clients_by_points(limit: int = 10, today: Optional[date] = None) -> List[Dict[str, Any]]:
    """Top clientes por pontos totais ganhos (não saldo atual)."""
    if today is None:
        today = date.today()

    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT 
                c.id, c.name, c.phone,
                COALESCE(SUM(p.final_points), 0) as total_points_earned
            FROM clients c
            LEFT JOIN purchases p ON p.client_id = c.id
            GROUP BY c.id
            ORDER BY total_points_earned DESC
            LIMIT ?
        """, (limit,)).fetchall()

        result = []
        for r in rows:
            stats = _compute_client_stats(conn, r["id"], today)
            result.append({
                "id": r["id"],
                "name": r["name"],
                "phone": r["phone"],
                "total_points_earned": r["total_points_earned"],
                "current_points": stats["current_points"],
                "available_packages": stats["available_packages"],
            })
        return result
    finally:
        conn.close()


def get_clients_by_tier_distribution(today: Optional[date] = None) -> Dict[str, int]:
    """Todos os clientes usam o mesmo sistema (acumulação simples sem multiplicadores)."""
    clients = get_all_clients_enriched(today)
    return {"acumulação_simples": len(clients)}


def get_recent_activity(limit: int = 8) -> List[Dict[str, Any]]:
    """Últimas movimentações (compras, resgates e recompensas especiais de marco)."""
    conn = get_conn()
    try:
        # Últimas compras
        purchases = conn.execute("""
            SELECT 
                'purchase' as type,
                p.purchase_date as tx_date,
                c.name as client_name,
                p.amount,
                p.final_points as points,
                p.multiplier,
                p.notes
            FROM purchases p
            JOIN clients c ON c.id = p.client_id
            ORDER BY p.purchase_date DESC, p.id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        # Últimos resgates
        redemptions = conn.execute("""
            SELECT 
                'redemption' as type,
                r.redemption_date as tx_date,
                c.name as client_name,
                NULL as amount,
                -r.points_redeemed as points,
                NULL as multiplier,
                r.notes
            FROM redemptions r
            JOIN clients c ON c.id = r.client_id
            ORDER BY r.redemption_date DESC, r.id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        # Últimas recompensas de marco (500 pacotes etc)
        milestones = conn.execute("""
            SELECT 
                'milestone_reward' as type,
                m.reward_date as tx_date,
                c.name as client_name,
                NULL as amount,
                0 as points,
                NULL as multiplier,
                ('Recompensa especial: ' || COALESCE(m.reward_description, m.reward_choice)) as notes
            FROM milestone_rewards m
            JOIN clients c ON c.id = m.client_id
            ORDER BY m.reward_date DESC, m.id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        all_tx = []
        for p in purchases:
            all_tx.append(dict(p))
        for r in redemptions:
            all_tx.append(dict(r))
        for m in milestones:
            all_tx.append(dict(m))

        # Ordena e limita
        all_tx.sort(key=lambda x: (x["tx_date"], 0 if x["type"] == "purchase" else (1 if x["type"] == "redemption" else 2)), reverse=True)
        return all_tx[:limit]
    finally:
        conn.close()


# ================== SISTEMA DE CONFIGURAÇÕES PERSONALIZÁVEIS ==================

DEFAULT_SETTINGS = {
    # Regras SIMPLES (versão básica para teste)
    # 1 pacote = 1 ponto
    # Sem resgate de pacotes grátis
    # Meta: 500 pontos = Cafeteira

    "milestone_packages_threshold": "500",
    "milestone_reward": "Cafeteira",

    # Textos e conteúdo da interface (totalmente personalizáveis)
    "program_name": "Programa Parceiro Isopor",
    "program_subtitle": "IsoSoluções • Dashboard de Fidelidade • Gestão de Parceiros",
    "admin_welcome": "Olá, Sofia! Este é o seu painel completo de controle do programa.",
    "sidebar_rules_text": """**Regras Simples (teste)**\n- 1 pacote comprado = 1 ponto\n\n**Meta especial**\n- Ao comprar 500 pacotes (500 pontos) → ganha 1 Cafeteira\n\nSem resgate de pontos. Link do painel enviado por WhatsApp.""",
    "footer_text": "IsoSoluções • Programa Parceiro Isopor • Desenvolvido com carinho\nDados armazenados localmente em SQLite • Tudo 100% offline e seguro",

    # Templates de WhatsApp (o admin pode editar livremente, use {placeholders})
    "whatsapp_purchase": """Olá {first_name}! 👋

+{final_points} ponto(s) (1 por pacote comprado)

Saldo atual: {current_points} pontos

{package_message}

{progress_message}

Obrigado! 💚""",

    "whatsapp_monthly": """Resumo do seu mês no {program_name}, {first_name}!

📅 Pacotes comprados este mês: *{monthly_spent}*
⭐ Pontos totais: *{points_this_month}*

Continue comprando! Ao chegar em 500 pontos você ganha uma Cafeteira.

Obrigado! 💚""",

    "whatsapp_promo": """🌟 {program_name} 🌟

1 pacote comprado = 1 ponto

Ao atingir 500 pontos: ganha 1 Cafeteira

Acompanhe seus pontos pelo link que enviamos.

Quer participar? É só falar comigo! 💚""",

    "whatsapp_milestone_500": """Parabéns {first_name}! 🏆🎉

Você atingiu 500 pontos!

Seu brinde: **Cafeteira**

Obrigado! Pode retirar quando quiser.

Acompanhe seu painel: {client_link}""",

    # Textos do Portal do Cliente (o que o cliente vê)
    "client_portal_title": "Seu Painel de Pontos",
    "client_portal_intro": "Acompanhe seus pontos e a meta da Cafeteira.",
    "client_how_it_works": "Como funciona:\n• 1 pacote comprado = 1 ponto\n• Ao atingir 500 pontos: ganha 1 Cafeteira\n\nAcompanhe tudo aqui pelo link que enviamos por WhatsApp.",

    # URL pública base para gerar links do portal do cliente (edite aqui para deixar online)
    "public_base_url": "http://localhost:8501",

    # Automação de avisos WhatsApp
    "auto_notify_whatsapp": "true",
    "auto_open_whatsapp": "true",

    # Cartão estático de pontos (PNG personalizável)
    "card_title": "Parabéns! Você ganhou pontos!",
    "card_subtitle": "Programa Parceiro Isopor",
    "card_footer": "IsoSoluções • Aura Project • Qualidade e fidelidade",
    "card_emoji": "🎉",
    "card_primary_color": "#0D9488",
    "card_secondary_color": "#0f172a",
    "card_accent_color": "#10b981",
    "card_show_balance": "true",
}

def _replace_multiplicador_text(text: str) -> str:
    """Substitui a palavra 'multiplicador' por 'bônus' em textos salvos."""
    replacements = [
        ("Multiplicadores", "Bônus"),
        ("Multiplicador", "Bônus"),
        ("multiplicadores", "bônus"),
        ("multiplicador", "bônus"),
        ("MULTIPLICADOR", "BÔNUS"),
    ]
    result = text
    for old, new in replacements:
        result = result.replace(old, new)
    return result


def migrate_remove_multiplicador_word() -> None:
    """Atualiza textos já salvos no banco que ainda usam a palavra multiplicador."""
    conn = get_conn()
    try:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
        for row in rows:
            if "multiplicador" in row["value"].lower():
                conn.execute(
                    "UPDATE app_settings SET value = ? WHERE key = ?",
                    (_replace_multiplicador_text(row["value"]), row["key"]),
                )
        conn.commit()
    finally:
        conn.close()


def init_settings() -> None:
    """Cria e popula as configurações padrão se não existirem."""
    conn = get_conn()
    try:
        # Garante que a tabela existe (já criada no init_db)
        for key, value in DEFAULT_SETTINGS.items():
            exists = conn.execute("SELECT 1 FROM app_settings WHERE key = ?", (key,)).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO app_settings (key, value, description) VALUES (?, ?, ?)",
                    (key, value, "")
                )
        conn.commit()
        migrate_remove_multiplicador_word()
    finally:
        conn.close()

def get_setting(key: str, default: str = "") -> str:
    """Retorna o valor de uma configuração."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()

_SETTING_LABELS = {
    "program_name":                 "Nome do Programa",
    "program_subtitle":             "Subtítulo do dashboard",
    "admin_welcome":                "Saudação do admin",
    "client_portal_title":          "Título do portal do cliente",
    "client_portal_intro":          "Introdução do portal do cliente",
    "whatsapp_purchase":            "Mensagem WhatsApp (compra)",
    "whatsapp_monthly":             "Mensagem WhatsApp (resumo mensal)",
    "whatsapp_promo":               "Mensagem WhatsApp (divulgação)",
    "whatsapp_milestone_500":       "Mensagem WhatsApp (meta atingida)",
    "auto_notify_whatsapp":         "Aviso automático ao conceder pontos",
    "auto_open_whatsapp":           "Abrir WhatsApp automaticamente",
    "sidebar_rules_text":           "Regras visíveis ao cliente",
    "milestone_packages_threshold": "Meta de pontos",
    "milestone_reward":             "Recompensa da meta",
    "card_title":                   "Título do cartão (PNG)",
    "card_subtitle":                "Subtítulo do cartão (PNG)",
    "card_footer":                  "Rodapé do cartão (PNG)",
    "card_emoji":                   "Emoji do cartão (PNG)",
    "card_primary_color":           "Cor primária do cartão",
    "card_secondary_color":         "Cor de fundo do cartão",
    "card_accent_color":            "Cor de destaque do cartão",
    "card_show_balance":            "Exibir saldo no cartão",
    "footer_text":                  "Texto do rodapé do dashboard",
}


def set_setting(key: str, value: str, _log: bool = True) -> None:
    """Atualiza (ou insere) uma configuração e registra a alteração no histórico."""
    conn = get_conn()
    try:
        old_row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        old_value = old_row["value"] if old_row else None

        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            (key, value)
        )

        if _log and old_value != value:
            label = _SETTING_LABELS.get(key, key)
            conn.execute(
                "INSERT INTO settings_changelog (key, label, old_value, new_value) VALUES (?, ?, ?, ?)",
                (key, label, old_value, value)
            )

        conn.commit()
    finally:
        conn.close()


def get_settings_changelog(limit: int = 100) -> list:
    """Retorna o histórico de alterações manuais, do mais recente ao mais antigo."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT label, old_value, new_value, changed_at FROM settings_changelog "
            "ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def clear_settings_changelog() -> None:
    """Apaga o histórico de alterações (chamado pelo reset de dados)."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM settings_changelog")
        conn.commit()
    finally:
        conn.close()

def get_all_settings() -> dict:
    """Retorna todas as configurações como dict."""
    conn = get_conn()
    try:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
        return {row["key"]: row["value"] for row in rows}
    finally:
        conn.close()

def get_program_rules() -> dict:
    """
    Regras SIMPLES (versão básica para teste):
    - 1 pacote = 1 ponto
    - 500 pontos = Cafeteira (única recompensa)
    """
    settings = get_all_settings()
    return {
        "milestone_packages_threshold": int(settings.get("milestone_packages_threshold", DEFAULT_SETTINGS.get("milestone_packages_threshold", 500))),
        "milestone_reward": settings.get("milestone_reward", "Cafeteira"),
    }

def get_program_texts() -> dict:
    """Retorna todos os textos personalizáveis."""
    return get_all_settings()

def get_public_base_url() -> str:
    """Retorna a URL base pública configurada para links do portal do cliente."""
    return get_setting("public_base_url", "http://localhost:8501").rstrip("/")

def detect_ngrok_url() -> str | None:
    """
    Tenta detectar automaticamente a URL pública do túnel ativo.
    Ordem: ngrok (API local) → Cloudflare quick tunnel (.logs/tunnel.url).
    Retorna a URL HTTPS se disponível, senão None.
    """
    import os
    import requests

    try:
        resp = requests.get("http://localhost:4040/api/tunnels", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            tunnels = data.get("tunnels", [])
            for t in tunnels:
                if t.get("proto") == "https":
                    return t.get("public_url", "").rstrip("/")
            if tunnels:
                return tunnels[0].get("public_url", "").rstrip("/")
    except Exception:
        pass

    tunnel_file = os.path.join(os.path.dirname(__file__), ".logs", "tunnel.url")
    try:
        with open(tunnel_file, encoding="utf-8") as f:
            url = f.read().strip()
            if url.startswith("https://"):
                return url.rstrip("/")
    except Exception:
        pass

    return None

def auto_set_ngrok_url() -> str | None:
    """
    Detecta ngrok e salva automaticamente na configuração public_base_url.
    Retorna a URL detectada ou None se não encontrou.
    """
    url = detect_ngrok_url()
    if url:
        set_setting("public_base_url", url)
        return url
    return None

# ================== MURAL DE ATUALIZAÇÕES ==================

def get_bulletin_updates(
    active_only: bool = True,
    client_view: bool = False,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Lista avisos do mural. Em client_view, retorna só os visíveis ao cliente."""
    conn = get_conn()
    try:
        query = "SELECT * FROM bulletin_updates WHERE 1=1"
        params: list = []

        if active_only:
            query += " AND is_active = 1"
        if client_view:
            query += " AND show_to_clients = 1"

        query += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_bulletin_update(
    title: str,
    content: str,
    show_to_clients: bool = True,
    is_active: bool = True,
) -> int:
    """Cria um novo aviso no mural. Retorna o ID."""
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO bulletin_updates (title, content, show_to_clients, is_active)
            VALUES (?, ?, ?, ?)
            """,
            (
                title.strip(),
                content.strip(),
                1 if show_to_clients else 0,
                1 if is_active else 0,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_bulletin_update(
    update_id: int,
    title: str,
    content: str,
    show_to_clients: bool = True,
    is_active: bool = True,
) -> None:
    """Atualiza um aviso existente no mural."""
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE bulletin_updates
            SET title = ?, content = ?, show_to_clients = ?, is_active = ?,
                updated_at = datetime('now', '-3 hours')
            WHERE id = ?
            """,
            (
                title.strip(),
                content.strip(),
                1 if show_to_clients else 0,
                1 if is_active else 0,
                update_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_bulletin_update(update_id: int) -> None:
    """Remove um aviso do mural."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM bulletin_updates WHERE id = ?", (update_id,))
        conn.commit()
    finally:
        conn.close()


def seed_bulletin_updates() -> None:
    """Popula avisos de exemplo se o mural estiver vazio."""
    conn = get_conn()
    try:
        count = conn.execute("SELECT COUNT(*) FROM bulletin_updates").fetchone()[0]
        if count > 0:
            return

        samples = [
            (
                "Programa de fidelidade ativo",
                "Acumule pontos a cada compra (R$38 = 1 pt) e troque por pacotes grátis. "
                "Seus pontos são cumulativos — cada ponto soma ao seu saldo anterior.",
                1,
                1,
            ),
            (
                "Recompensa especial — 500 pacotes",
                "Ao atingir 500 pacotes comprados, você escolhe entre desconto, Pix ou brinde. "
                "Acompanhe seu progresso no painel.",
                1,
                1,
            ),
        ]
        for title, content, show_clients, active in samples:
            conn.execute(
                """
                INSERT INTO bulletin_updates (title, content, show_to_clients, is_active)
                VALUES (?, ?, ?, ?)
                """,
                (title, content, show_clients, active),
            )
        conn.commit()
    finally:
        conn.close()


def reset_client_data(keep_settings: bool = True) -> None:
    """
    Zera completamente todos os dados de clientes, compras e resgates.
    Mantém as configurações personalizadas por padrão.
    Use para deixar o sistema pronto para uso real (sem dados de demonstração).
    """
    conn = get_conn()
    try:
        conn.execute("DELETE FROM redemptions")
        conn.execute("DELETE FROM purchases")
        conn.execute("DELETE FROM clients")
        conn.execute("DELETE FROM settings_changelog")
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('clients', 'purchases', 'redemptions')")
        conn.commit()
    finally:
        conn.close()

# ================== SEED DEMO DATA (para impressionar) ==================

DEMO_CLIENTS = [
    ("Ana Paula Costa", "(11) 98765-4321"),
    ("Bruno Mendes Silva", "(11) 97654-3210"),
    ("Carla Rodrigues", "(21) 96543-2109"),
    ("Daniel Oliveira", "(31) 95432-1098"),
    ("Eduarda Santos", "(41) 94321-0987"),
    ("Felipe Almeida", "(51) 93210-9876"),
    ("Gabriela Ferreira", "(61) 92109-8765"),
    ("Henrique Lima", "(71) 91098-7654"),
    ("Isabela Martins", "(81) 90987-6543"),
    ("João Pedro Souza", "(85) 99876-5432"),
    ("Laura Beatriz", "(11) 98711-2233"),
    ("Marcos Vinicius", "(19) 97622-3344"),
]

def seed_demo_data(force: bool = False) -> None:
    """Popula dados bonitos de demonstração se o banco estiver vazio."""
    conn = get_conn()
    try:
        count = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        if count > 0 and not force:
            return

        # Limpa se force
        if force:
            conn.executescript("DELETE FROM redemptions; DELETE FROM purchases; DELETE FROM clients;")

        # Insere clientes
        client_ids = {}
        for name, phone in DEMO_CLIENTS:
            cur = conn.execute("INSERT INTO clients (name, phone) VALUES (?, ?)", (name, phone))
            client_ids[name] = cur.lastrowid

        # Compras de demonstração (datas em 2026, especialmente junho)
        # Mês atual: 2026-06 (hoje é 2026-06-14)
        from datetime import timedelta
        import random

        random.seed(42)  # Reprodutível

        today = date(2026, 6, 14)

        # Compras variadas (acumulação simples — sem bônus por faixa)
        # package_quantity usado para o marco de 500 pacotes
        sample_purchases = [
            # Ana Paula Costa
            (client_ids["Ana Paula Costa"], today - timedelta(days=1), 820.0, 22, "Compra grande - material de embalagem"),
            (client_ids["Ana Paula Costa"], today - timedelta(days=5), 690.0, 18, ""),
            (client_ids["Ana Paula Costa"], today - timedelta(days=12), 450.0, 12, ""),
            (client_ids["Ana Paula Costa"], date(2026, 5, 20), 1250.0, 35, "Pedido mensal"),

            # Bruno Mendes Silva
            (client_ids["Bruno Mendes Silva"], today - timedelta(days=2), 380.0, 10, ""),
            (client_ids["Bruno Mendes Silva"], today - timedelta(days=3), 290.0, 8, ""),
            (client_ids["Bruno Mendes Silva"], today - timedelta(days=9), 540.0, 14, "Reforço de estoque"),
            (client_ids["Bruno Mendes Silva"], date(2026, 5, 15), 310.0, 8, ""),

            # Carla - volume baixo
            (client_ids["Carla Rodrigues"], today - timedelta(days=0), 114.0, 3, "Urgente"),
            (client_ids["Carla Rodrigues"], today - timedelta(days=7), 228.0, 6, ""),
            (client_ids["Carla Rodrigues"], date(2026, 5, 28), 76.0, 2, ""),

            # Daniel - alto histórico + este mês alto (vamos fazer ele passar fácil de 500 com ajuste posterior no seed)
            (client_ids["Daniel Oliveira"], today - timedelta(days=4), 1520.0, 42, "Grande pedido industrial"),
            (client_ids["Daniel Oliveira"], today - timedelta(days=10), 380.0, 10, ""),
            (client_ids["Daniel Oliveira"], date(2026, 5, 3), 890.0, 24, ""),
            (client_ids["Daniel Oliveira"], date(2026, 4, 22), 670.0, 18, ""),

            # Outros clientes com atividade variada
            (client_ids["Eduarda Santos"], today - timedelta(days=6), 152.0, 4, ""),
            (client_ids["Eduarda Santos"], date(2026, 5, 10), 418.0, 11, ""),
            (client_ids["Felipe Almeida"], today - timedelta(days=8), 532.0, 14, "Promoção do mês"),
            (client_ids["Gabriela Ferreira"], today - timedelta(days=11), 266.0, 7, ""),
            (client_ids["Henrique Lima"], today - timedelta(days=1), 190.0, 5, ""),
            (client_ids["Isabela Martins"], date(2026, 6, 5), 874.0, 23, ""),
            (client_ids["João Pedro Souza"], today - timedelta(days=13), 418.0, 11, ""),
            (client_ids["Laura Beatriz"], today - timedelta(days=3), 95.0, 2, ""),
            (client_ids["Marcos Vinicius"], today - timedelta(days=5), 760.0, 20, "Pedido especial"),
        ]

        for cid, pdate, amt, qty, note in sample_purchases:
            # Insere diretamente — pontos base simples (sem bônus mensal)
            base_pts = math.floor(amt / 38.0)
            final_pts = base_pts
            mult = 1.0

            conn.execute("""
                INSERT INTO purchases (client_id, purchase_date, amount, base_points, multiplier, final_points, package_quantity, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cid, pdate.isoformat(), amt, base_pts, mult, final_pts, int(qty), note))

        # Alguns resgates bonitos para mostrar atividade
        # Ana resgatou 2 pacotes recentemente
        conn.execute("""
            INSERT INTO redemptions (client_id, redemption_date, points_redeemed, notes)
            VALUES (?, ?, ?, ?)
        """, (client_ids["Ana Paula Costa"], (today - timedelta(days=2)).isoformat(), 20, "Resgate de 2 pacotes"))

        conn.execute("""
            INSERT INTO redemptions (client_id, redemption_date, points_redeemed, notes)
            VALUES (?, ?, ?, ?)
        """, (client_ids["Daniel Oliveira"], (today - timedelta(days=7)).isoformat(), 10, "1 pacote grande"))

        conn.execute("""
            INSERT INTO redemptions (client_id, redemption_date, points_redeemed, notes)
            VALUES (?, ?, ?, ?)
        """, (client_ids["Bruno Mendes Silva"], (today - timedelta(days=4)).isoformat(), 10, ""))

        # --- DEMO DO NOVO MARCO DE 500 PACOTES ---
        # Daniel recebe um "ajuste grande" (compra com qty alta) + já reivindicou a recompensa especial
        # (para mostrar o fluxo completo na demo sem precisar de 500 compras reais)
        daniel_large = date(2026, 6, 10)
        conn.execute("""
            INSERT INTO purchases (client_id, purchase_date, amount, base_points, multiplier, final_points, package_quantity, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (client_ids["Daniel Oliveira"], daniel_large.isoformat(), 0.0, 0, 1.0, 0, 420, "Ajuste de volume histórico (demo 500 pacotes)"))

        # Concede a recompensa de marco para Daniel (escolheu Pix como exemplo)
        conn.execute("""
            INSERT INTO milestone_rewards (client_id, reward_date, milestone, reward_choice, reward_description, notes)
            VALUES (?, ?, '500_pacotes', 'cafeteira', 'Cafeteira', 'Meta automática')
        """, (client_ids["Daniel Oliveira"], (today - timedelta(days=1)).isoformat() ))

        # Ana fica "quase lá" para mostrar o progresso (soma ~87 dos itens acima + mais alguns)
        # (deixamos como está para o admin poder testar o botão de concessão)

        conn.commit()
        seed_bulletin_updates()
        print("✅ Dados de demonstração criados com sucesso! (incluindo demo do marco 500 pacotes)")
    finally:
        conn.close()
