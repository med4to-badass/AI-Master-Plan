"""
app.py
Dashboard Principal - Programa Parceiro Isopor
Aura Project

Interface profissional, moderna e escura com:
- Cards de KPI grandes e bonitos
- Gráficos interativos com Plotly (cores verde/azul)
- Busca, filtros e ações em tempo real
- Registro de compra com 1 clique
- Resgate de pacotes
- Histórico completo do cliente
- Mensagens prontas para WhatsApp
- Exportação Excel completa

Para rodar:
    streamlit run app.py

Tema: Dark moderno + verde esmeralda (#10b981) + azul profissional (#3b82f6)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
from io import BytesIO
import os
import subprocess
import time

# Módulos locais
from database import (
    init_db,
    seed_demo_data,
    init_settings,
    get_all_clients_enriched,
    get_client_by_id,
    search_clients,
    add_client,
    register_purchase,
    claim_milestone_reward,
    get_client_history,
    get_dashboard_kpis,
    get_monthly_purchase_history,
    get_top_clients_by_points,
    get_recent_activity,
    get_program_rules,
    get_all_settings,
    set_setting,
    get_setting,
    get_program_texts,
    reset_client_data,
    get_public_base_url,
    seed_bulletin_updates,
)
from calculations import (
    format_currency,
    format_points,
    get_milestone_progress,
    get_rewards_status,
)
from utils import (
    create_welcome_purchase_message,
    create_redemption_message,
    create_monthly_summary_message,
    create_promotional_message,
    export_full_report,
)
from notifications import (
    init_notification_log,
    build_purchase_message,
    build_milestone_reward_message,
    build_whatsapp_url,
    log_notification,
    get_recent_notifications,
)
from notification_card import generate_points_card
from manual_pdf import generate_user_manual, save_user_manual, MANUAL_PDF_PATH
from tunnel import ensure_online, get_public_url
from bulletin_board import render_bulletin_board, render_bulletin_admin_panel

# ================== CONFIGURAÇÃO DA PÁGINA ==================
st.set_page_config(
    page_title="IsoSoluções | Programa Parceiro Isopor",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Meta viewport para melhor responsividade em dispositivos móveis
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
""", unsafe_allow_html=True)

# ================== TEMA ESCURO + CSS PROFISSIONAL ==================
st.markdown("""
<style>
/* ==================== ROOT DARK THEME - IsoSoluções Palette ==================== */
:root {
    --bg-primary: #0b1120;
    --bg-secondary: #0f172a;
    --bg-card: #1e2937;
    --bg-card-hover: #334155;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --accent-red: #B91C1C;
    --accent-red-dark: #991B1B;
    --accent-teal: #0D9488;
    --accent-teal-dark: #0F766E;
    --accent-cyan: #06B6D4;
    --accent-amber: #f59e0b;
    --border: #475569;
}

/* Fundo principal */
.stApp {
    background: linear-gradient(145deg, #0b1120 0%, #0f172a 100%);
    color: var(--text-primary);
}

/* Remove espaçamento excessivo do streamlit */
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}

/* ==================== HEADER ==================== */
.main-header {
    background: linear-gradient(90deg, #1e2937 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 1.25rem 2rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
}

.main-header h1 {
    margin: 0;
    font-size: 1.85rem;
    font-weight: 700;
    background: linear-gradient(90deg, var(--accent-teal), var(--accent-cyan));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.main-header .subtitle {
    color: #94a3b8;
    font-size: 0.95rem;
    margin-top: 0.25rem;
}

/* ==================== KPI CARDS ==================== */
.kpi-card {
    background: #1e2937;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 1.1rem 1.35rem;
    height: 100%;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}

.kpi-card:hover {
    transform: translateY(-2px);
    border-color: #10b981;
    box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
}

.kpi-card .kpi-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.35rem;
}

.kpi-card .kpi-value {
    font-size: 1.85rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1.1;
}

.kpi-card .kpi-accent {
    position: absolute;
    top: 0;
    left: 0;
    width: 5px;
    height: 100%;
    background: linear-gradient(180deg, var(--accent-teal), var(--accent-cyan));
}

.kpi-card.blue .kpi-accent {
    background: linear-gradient(180deg, var(--accent-red), var(--accent-red-dark));
}

.kpi-card.amber .kpi-accent {
    background: linear-gradient(180deg, var(--accent-amber), #fbbf24);
}

/* ==================== SECTION HEADERS ==================== */
.section-header {
    font-size: 1.15rem;
    font-weight: 700;
    color: #f1f5f9;
    margin: 1.5rem 0 0.75rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.section-header::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right, #334155, transparent);
}

/* ==================== CLIENT CARD / SELECTED ==================== */
.client-selected {
    background: linear-gradient(135deg, #1e2937 0%, #0f172a 100%);
    border: 2px solid var(--accent-teal);
    border-radius: 18px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}

.client-name {
    font-size: 1.45rem;
    font-weight: 700;
    color: #f1f5f9;
}

.client-phone {
    color: #64748b;
    font-size: 0.95rem;
}

/* ==================== BUTTONS ==================== */
.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    transition: all 0.2s ease;
}

.stButton > button[kind="primary"] {
    background: var(--accent-teal) !important;
    color: white !important;
    border: none !important;
}

.stButton > button[kind="primary"]:hover {
    background: var(--accent-teal-dark) !important;
    transform: translateY(-1px);
}

.stButton > button.secondary-green {
    background: transparent !important;
    color: #10b981 !important;
    border: 1px solid #10b981 !important;
}

/* ==================== TABLES & DATAFRAMES ==================== */
.stDataFrame {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #334155;
}

/* ==================== INPUTS ==================== */
.stTextInput input, .stNumberInput input, .stDateInput input {
    background-color: #1e2937 !important;
    border: 1px solid #475569 !important;
    color: #f1f5f9 !important;
    border-radius: 10px !important;
}

.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1) !important;
}

/* ==================== SUCCESS / INFO BOXES ==================== */
.stSuccess, .stInfo, .stWarning {
    border-radius: 12px;
    border-left-width: 5px;
}

/* ==================== SIDEBAR ==================== */
[data-testid="stSidebar"] {
    background: #0f172a;
    border-right: 1px solid #334155;
}

[data-testid="stSidebar"] .stButton > button {
    width: 100%;
}

/* ==================== WHATSAPP BOX ==================== */
.whatsapp-box {
    background: #052e16;
    border: 1px solid var(--accent-teal-dark);
    border-radius: 12px;
    padding: 1rem;
    font-family: ui-monospace, monospace;
    white-space: pre-wrap;
    color: #5eead4;
    font-size: 0.9rem;
    line-height: 1.4;
}

/* ==================== BADGES ==================== */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.3px;
}

.badge-green { background: #052e16; color: #4ade80; }
.badge-blue { background: #1e3a8a; color: #60a5fa; }
.badge-slate { background: #334155; color: #cbd5e1; }

/* ==================== MOBILE RESPONSIVENESS ==================== */
@media (max-width: 768px) {
    .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }

    .main-header {
        padding: 0.75rem 1rem !important;
        margin-bottom: 1rem !important;
    }

    .main-header h1 {
        font-size: 1.4rem !important;
    }

    .kpi-card {
        padding: 0.7rem 0.9rem !important;
        margin-bottom: 0.5rem;
    }

    .kpi-card .kpi-value {
        font-size: 1.4rem !important;
    }

    .section-header {
        font-size: 1rem !important;
    }

    .client-selected {
        padding: 0.9rem 1rem !important;
    }

    .client-name {
        font-size: 1.15rem !important;
    }

    /* Force columns to stack nicely on mobile */
    [data-testid="column"] {
        min-width: 100% !important;
    }

    /* Bigger touch targets */
    .stButton > button, .stForm button {
        min-height: 44px !important;
        font-size: 1rem !important;
    }

    /* Better tables on mobile */
    .stDataFrame {
        font-size: 0.85rem !important;
    }

    /* Progress bars */
    .stProgress {
        margin-bottom: 0.5rem;
    }
}

/* Extra tight for very small phones */
@media (max-width: 480px) {
    .kpi-card .kpi-value {
        font-size: 1.2rem !important;
    }
}

/* ==================== PROGRESS ==================== */
.stProgress > div > div {
    background: linear-gradient(90deg, var(--accent-teal), var(--accent-cyan));
}

/* ==================== CHARTS CONTAINER ==================== */
.chart-container {
    background: #1e2937;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 0.75rem 1rem;
}

/* ==================== MURAL DE ATUALIZAÇÕES ==================== */
.bulletin-board {
    background: rgba(30, 41, 55, 0.75);
    border: 1px solid #334155;
    border-left: 4px solid #64748b;
    border-radius: 10px;
    padding: 0.65rem 1rem;
    margin-bottom: 1rem;
}

.bulletin-board-client {
    border-left-color: #0D9488;
    margin-top: 0.5rem;
    margin-bottom: 1.25rem;
}

.bulletin-board-header {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 0.5rem;
}

.bulletin-board-icon {
    font-size: 0.85rem;
    opacity: 0.8;
}

.bulletin-board-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}

.bulletin-board-items {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
}

.bulletin-item {
    padding: 0.35rem 0;
    border-bottom: 1px solid rgba(51, 65, 85, 0.5);
}

.bulletin-item:last-child {
    border-bottom: none;
    padding-bottom: 0;
}

.bulletin-item-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.75rem;
    flex-wrap: wrap;
}

.bulletin-item-title {
    font-size: 0.88rem;
    font-weight: 600;
    color: #e2e8f0;
}

.bulletin-item-content {
    font-size: 0.82rem;
    color: #94a3b8;
    line-height: 1.4;
    margin-top: 0.15rem;
}

.bulletin-item-date {
    font-size: 0.7rem;
    color: #64748b;
    white-space: nowrap;
}

.bulletin-board-client .bulletin-item-title {
    font-size: 0.85rem;
}

.bulletin-board-client .bulletin-item-content {
    font-size: 0.8rem;
}

/* ==================== FOOTER ==================== */
.footer {
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid #334155;
    color: #475569;
    font-size: 0.8rem;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)


# ================== INICIALIZAÇÃO ==================
@st.cache_resource
def initialize_database():
    init_db()
    init_settings()   # Garante que todas as configs personalizáveis existem
    init_notification_log()
    seed_demo_data()  # Só popula se estiver vazio
    seed_bulletin_updates()  # Avisos de exemplo se o mural estiver vazio
    return True


initialize_database()

# Garante manual PDF salvo no disco
if not MANUAL_PDF_PATH.exists():
    try:
        save_user_manual(get_all_settings())
    except Exception:
        pass

# Carrega configurações personalizáveis (sempre atualizadas)
ALL_SETTINGS = get_all_settings()
RULES = get_program_rules()

# ================== SUPORTE A PORTAL DO CLIENTE (o que você envia pro cliente) ==================
# Se a URL tiver ?view=cliente&phone=... ou ?cliente_id=... mostramos a visão limpa para o cliente
query_params = st.query_params

def get_first_name(full_name: str) -> str:
    return full_name.split()[0] if full_name else "Parceiro"

def render_client_portal():
    """Visão simplificada e bonita para o cliente (o que o admin envia por link ou WhatsApp)."""
    # Tenta identificar o cliente
    client = None
    if "cliente_id" in query_params:
        try:
            cid = int(query_params["cliente_id"])
            client = get_client_by_id(cid)
        except:
            pass
    elif "phone" in query_params:
        phone = query_params["phone"]
        # Busca por telefone exato ou parcial
        matches = search_clients(phone)
        if matches:
            client = matches[0]
    elif "id" in query_params:
        try:
            client = get_client_by_id(int(query_params["id"]))
        except:
            pass

    if not client:
        st.error("Cliente não encontrado. Peça um novo link para a equipe IsoSoluções.")
        st.stop()

    # Carrega regras e textos atuais
    rules = get_program_rules()
    texts = get_program_texts()
    # Sem threshold de resgate
    threshold = 10  # dummy, não usado
    rate = 1.0  # dummy

    st.set_page_config(page_title=f"{client['name']} | IsoSoluções", page_icon="♻️", layout="centered")

    # Header bonito para cliente
    st.markdown('<div style="text-align:center; font-size:1.9rem; font-weight:700; margin-bottom:4px;"><span style="color:#0D9488;">Iso</span><span style="color:#B91C1C;">Soluções</span></div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align:center; padding: 0.5rem 0 1rem;">
        <h1 style="font-size:1.25rem; margin-bottom:0.15rem; background: linear-gradient(90deg, #0D9488, #06B6D4); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
            {texts.get('program_name', 'Programa Parceiro Isopor')}
        </h1>
        <p style="color:#94a3b8; margin:0; font-size:0.95rem;">{texts.get('client_portal_title', 'Seu Painel de Fidelidade')}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"**Olá, {get_first_name(client['name'])}!** 👋")
    st.caption(texts.get("client_portal_intro", "Acompanhe seus pontos e benefícios."))

    render_bulletin_board(client_view=True, max_items=3)

    # Cards principais para o cliente (bonitos e grandes)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("⭐ Seus Pontos (1 por pacote)", client["current_points"])
    with c2:
        st.metric("Progresso para Cafeteira", f"{client.get('total_packages_bought', 0)} / 500")

    # Progresso simples para a meta (sem resgate)
    rewards = get_rewards_status(client["current_points"], client.get("total_packages_bought", 0))

    mile = rewards["milestone_500"]
    pct = mile["percent"] / 100.0
    st.markdown("**🎯 Progresso para Cafeteira (500 pontos)**")
    st.progress(pct, text=mile["progress_text"])

    # Apresentação das 5 opções para o cliente escolher (novo)
    total_bought = client.get("total_packages_bought", 0)
    milestone_th = client.get("milestone_packages_threshold", 500)
    has_milestone = client.get("has_milestone_500", False)
    if total_bought >= milestone_th and not has_milestone:
        st.markdown("---")
        st.markdown("### 🏆🎁 **Você atingiu 500 pontos!**")
        st.success("Brinde: **Cafeteira**")

        texts = get_program_texts()
        program_name = texts.get("program_name", "Programa Parceiro Isopor")
        first_name = get_first_name(client["name"])

        if st.button("📱 Avisar por WhatsApp que quero a Cafeteira", type="primary"):
            wa_msg = f"Olá! Atingi 500 pontos no {program_name}. Quero a Cafeteira como brinde!"
            wa_url = build_whatsapp_url(client["phone"], wa_msg)
            st.markdown(f"[Abrir WhatsApp]({wa_url})", unsafe_allow_html=True)

    # Volume do mês (informação útil — não afeta pontos)
    st.markdown(f"**Volume este mês:** {format_currency(client['monthly_spent'])}")

    # Como funciona (texto personalizável pelo admin)
    with st.expander("📖 Como funciona o programa (regras atuais)", expanded=False):
        st.markdown(texts.get("client_how_it_works", "Regras do programa de fidelidade."))
        st.markdown(f"""
        - **1 pacote** = **1 ponto**
        - **10 pontos** = **1 pacote grátis**
        - Seus pontos são diretos (cada pacote soma)
        - **🏆 500 pontos**: ganha **Cafeteira**
        """)

    # Histórico recente (últimas 6)
    st.markdown("**🕒 Suas últimas movimentações**")
    history = get_client_history(client["id"])[:6]
    if history:
        for h in history:
            if h["type"] == "purchase":
                st.write(f"💰 **{h['date']}** — Compra de {format_currency(h['amount'])} → **+{h['points']} pts**")
            elif h["type"] == "redemption":
                st.write(f"🎁 **{h['date']}** — Resgate de pacote(s) → **{h['points']} pts**")
            else:
                st.write(f"🏆 **{h['date']}** — {h['notes']}")
    else:
        st.caption("Nenhuma movimentação ainda. Comece a comprar e acumule!")

    # Ação principal: Falar com a equipe
    st.divider()
    st.markdown("**Quer resgatar ou tirar dúvida?**")
    contact_msg = f"Olá! Sou {client['name']} (tel {client['phone']}). Meu saldo atual é de {client['current_points']} pontos. Quando chego em 500 ganho a Cafeteira!"
    _newline = '\n'
    wa_link = f"https://wa.me/?text={contact_msg.replace(' ', '%20').replace(_newline, '%0A')}"

    if st.button("💬 Falar no WhatsApp com a equipe", type="primary", width='stretch'):
        st.markdown(f"[Abrir WhatsApp]({wa_link})", unsafe_allow_html=True)

    st.caption("Link gerado com seus dados atuais. A equipe Aura pode confirmar seu resgate.")

    # Rodapé
    st.markdown(f"<div style='text-align:center; font-size:0.8rem; color:#475569; margin-top:2rem;'>{texts.get('footer_text', 'IsoSoluções')}</div>", unsafe_allow_html=True)

    st.stop()  # Não mostra mais nada do dashboard admin

# Detecta se estamos no modo cliente
if query_params.get("view") == "cliente" or "phone" in query_params or "cliente_id" in query_params or "id" in query_params:
    render_client_portal()


@st.cache_resource
def _ensure_client_portal_online():
    """Sobe o túnel público uma vez ao abrir o painel admin."""
    url, _ = ensure_online()
    if url:
        set_setting("public_base_url", url)
    return url


PUBLIC_PORTAL_URL = _ensure_client_portal_online()
if PUBLIC_PORTAL_URL:
    ALL_SETTINGS = get_all_settings()


def refresh_data():
    """Limpa caches para refletir alterações imediatamente."""
    st.cache_data.clear()


# ================== ESTADO GLOBAL ==================
if "selected_client_id" not in st.session_state:
    st.session_state.selected_client_id = None

if "last_action_message" not in st.session_state:
    st.session_state.last_action_message = None

if "pending_notification" not in st.session_state:
    st.session_state.pending_notification = None


def select_client(client_id: int):
    st.session_state.selected_client_id = client_id
    st.session_state.last_action_message = None
    st.session_state.pending_notification = None


def prepare_points_notification(client, result, notification_type="purchase"):
    """Prepara mensagem, cartão PNG e link WhatsApp após conceder pontos."""
    whatsapp_msg = build_purchase_message(client, result)
    # Passa dados de progresso para o cartão profissional (avisos de "quanto falta")
    pkg_info = points_remaining_for_next_package(client["current_points"])
    card_buffer = generate_points_card(
        client_name=client["name"],
        points_earned=result["final_points"],
        current_points=client["current_points"],
        amount=result["amount"],
        settings=get_all_settings(),
        available_packages=0,  # sem resgate
        points_to_next_package=pkg_info,
        total_packages_bought=client.get("total_packages_bought", 0),
        milestone_remaining=client.get("milestone_packages_threshold", 500) - client.get("total_packages_bought", 0),
    )
    wa_url = build_whatsapp_url(client["phone"], whatsapp_msg)
    log_notification(
        client_id=client["id"],
        notification_type=notification_type,
        message=whatsapp_msg,
        phone=client["phone"],
        status="prepared",
    )
    return {
        "type": notification_type,
        "client_name": client["name"],
        "phone": client["phone"],
        "message": whatsapp_msg,
        "wa_url": wa_url,
        "card_png": card_buffer.getvalue(),
        "points": result["final_points"],
    }


def render_notification_panel(notification: dict):
    """Exibe painel de aviso automático com cartão estático e botão WhatsApp."""
    if not notification:
        return

    settings = get_all_settings()
    auto_open = settings.get("auto_open_whatsapp", "true").lower() == "true"

    st.markdown("---")
    if notification.get("type") == "milestone":
        st.markdown("### 🏆 Aviso Automático — Recompensa 500 Pacotes")
    else:
        st.markdown("### 📲 Aviso Automático de Pontos")

    if notification["type"] == "purchase":
        st.success(
            f"**+{notification['points']} pontos** concedidos para **{notification['client_name']}**. "
            "Mensagem e cartão prontos para envio!"
        )
    elif notification.get("type") == "milestone":
        st.success(f"**Recompensa especial concedida** para **{notification['client_name']}**. Mensagem WhatsApp pronta!")
    else:
        st.success(f"Aviso preparado para **{notification['client_name']}**.")

    has_card = notification.get("card_png") is not None
    if has_card:
        notif_col1, notif_col2 = st.columns([1, 1])
    else:
        notif_col2 = st.container()

    if has_card:
        with notif_col1:
            st.image(notification["card_png"], caption="Cartão estático de pontos", width='stretch')
            st.download_button(
                label="⬇️ Baixar Cartão de Pontos (PNG)",
                data=notification["card_png"],
                file_name=f"cartao_pontos_{notification['client_name'].split()[0].lower()}.png",
                mime="image/png",
                width='stretch',
            )

    with notif_col2:
        st.markdown("**Mensagem para WhatsApp:**")
        st.code(notification["message"], language=None)
        st.link_button(
            "📱 Enviar no WhatsApp",
            notification["wa_url"],
            type="primary",
            width='stretch',
        )
        st.caption(
            "Clique para abrir o WhatsApp com a mensagem já preenchida. "
            "Envie também o cartão PNG baixado acima."
        )

        # Automação: após clicar no WhatsApp, o admin pode limpar o painel de aviso
        if st.button("✅ Limpar este aviso (após enviar)", key=f"clear_notif_{notification.get('client_name','')}", width='stretch'):
            st.session_state.pending_notification = None
            st.rerun()

    if auto_open and notification["type"] == "purchase":
        import json
        safe_url = json.dumps(notification["wa_url"])
        st.components.v1.html(
            f"""
            <script>
                window.open({safe_url}, "_blank");
            </script>
            """,
            height=0,
        )
        st.info("WhatsApp aberto automaticamente (configurável em Personalizar Programa).")


def clear_selection():
    st.session_state.selected_client_id = None


# ================== CABEÇALHO IMPRESSIONANTE (usa textos personalizáveis) ==================
program_name = ALL_SETTINGS.get("program_name", "Programa Parceiro Isopor")
program_subtitle = ALL_SETTINGS.get("program_subtitle", "IsoSoluções • Dashboard de Fidelidade • Gestão de Parceiros")
admin_welcome = ALL_SETTINGS.get("admin_welcome", "Olá, Sofia! Este é o seu painel completo de controle do programa.")

st.markdown(f"""
<div class="main-header">
    <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap;">
        <div style="font-size:1.7rem; font-weight:700; line-height:1;">
            <span style="color:#0D9488;">Iso</span><span style="color:#B91C1C;">Soluções</span>
        </div>
        <div>
            <h1 style="font-size:1.45rem; margin:0; background: linear-gradient(90deg, #0D9488, #06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{program_name}</h1>
            <div class="subtitle" style="margin-top:-4px; font-size:0.85rem;">{program_subtitle}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Saudação dinâmica
col_greet, col_date = st.columns([3, 1])
with col_greet:
    today_str = date.today().strftime('%d de %B de %Y').replace('June', 'Junho')
    st.markdown(f"**{admin_welcome}** Hoje é **{today_str}**.")
with col_date:
    st.caption(f"Atualizado em {datetime.now().strftime('%H:%M')}")

render_bulletin_board(client_view=False, max_items=4)

# ================== KPIs DO TOPO ==================
kpis = get_dashboard_kpis()

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-accent"></div>
        <div class="kpi-label">👥 Total de Clientes</div>
        <div class="kpi-value">{kpis['total_clients']}</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col2:
    st.markdown(f"""
    <div class="kpi-card blue">
        <div class="kpi-accent"></div>
        <div class="kpi-label">⭐ Pontos Distribuídos Hoje</div>
        <div class="kpi-value">{kpis['points_today']}</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-accent"></div>
        <div class="kpi-label">📦 Pacotes Resgatados (Mês)</div>
        <div class="kpi-value">{kpis['packages_redeemed_month']}</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col4:
    st.markdown(f"""
    <div class="kpi-card amber">
        <div class="kpi-accent"></div>
        <div class="kpi-label">💰 Volume de Compras (Mês)</div>
        <div class="kpi-value">{format_currency(kpis['volume_month'])}</div>
    </div>
    """, unsafe_allow_html=True)

# KPIs secundários (linha menor)
kpi2_col1, kpi2_col2, kpi2_col3 = st.columns(3)

with kpi2_col1:
    st.markdown(f"""
    <div class="kpi-card" style="padding:0.65rem 1rem; font-size:0.9rem;">
        <div class="kpi-label" style="font-size:0.7rem;">🏆 Clientes com Cafeteira</div>
        <div class="kpi-value" style="font-size:1.35rem;">{kpis.get('milestone_clients', 0)}</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2_col2:
    st.markdown(f"""
    <div class="kpi-card" style="padding:0.65rem 1rem; font-size:0.9rem;">
        <div class="kpi-label" style="font-size:0.7rem;">🔄 Pontos em Circulação</div>
        <div class="kpi-value" style="font-size:1.35rem;">{kpis['circulating_points']}</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2_col3:
    # Mini resumo (pacotes disponíveis no sistema — acumulação simples)
    st.markdown(f"""
    <div class="kpi-card" style="padding:0.65rem 1rem; font-size:0.9rem;">
        <div class="kpi-label" style="font-size:0.7rem;">🎯 Clientes na meta 500</div>
        <div class="kpi-value" style="font-size:1.35rem;">{kpis.get('milestone_clients', 0)}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ================== GRÁFICOS ==================
st.markdown('<div class="section-header">📊 Visão Geral do Programa</div>', unsafe_allow_html=True)

chart_col1, chart_col2 = st.columns(2)

# --- Gráfico 1: Evolução Mensal de Compras e Pontos ---
with chart_col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    monthly_data = get_monthly_purchase_history(months_back=7)

    if monthly_data:
        df_month = pd.DataFrame(monthly_data)
        df_month["month_label"] = df_month["month"].apply(
            lambda m: datetime.strptime(m, "%Y-%m").strftime("%b/%y").replace("Jan", "Jan").replace("Feb", "Fev")
            .replace("Mar", "Mar").replace("Apr", "Abr").replace("May", "Mai").replace("Jun", "Jun")
            .replace("Jul", "Jul").replace("Aug", "Ago").replace("Sep", "Set").replace("Oct", "Out")
            .replace("Nov", "Nov").replace("Dec", "Dez")
        )

        fig1 = go.Figure()
        fig1.add_trace(go.Bar(
            x=df_month["month_label"],
            y=df_month["volume"],
            name="Volume (R$)",
            marker_color="#B91C1C",
            yaxis="y",
            hovertemplate="%{x}<br>Volume: R$ %{y:,.2f}<extra></extra>"
        ))
        fig1.add_trace(go.Scatter(
            x=df_month["month_label"],
            y=df_month["points_awarded"],
            name="Pontos Concedidos",
            mode="lines+markers",
            line=dict(color="#0D9488", width=3),
            marker=dict(size=8),
            yaxis="y2",
            hovertemplate="%{x}<br>Pontos: %{y}<extra></extra>"
        ))

        fig1.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2937",
            plot_bgcolor="#1e2937",
            title=dict(text="Evolução Mensal — Volume vs Pontos", font=dict(size=14, color="#f1f5f9")),
            height=320,
            margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(gridcolor="#334155", tickfont=dict(color="#94a3b8")),
            yaxis=dict(title="Volume R$", gridcolor="#334155", tickfont=dict(color="#94a3b8")),
            yaxis2=dict(title="Pontos", overlaying="y", side="right", gridcolor="#334155", tickfont=dict(color="#94a3b8")),
            font=dict(color="#cbd5e1"),
        )
        st.plotly_chart(fig1, width='stretch', config={"displayModeBar": False})
    else:
        st.info("Sem dados de histórico mensal ainda.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- Info do programa (livre de multiplicadores) ---
with chart_col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown("**📌 Acumulação Simples**")
    st.markdown("""
    Os pontos são **100% cumulativos**: cada ponto conquistado se soma diretamente ao saldo anterior.<br>
    <strong>Sem multiplicadores ou bônus por faixa de volume.</strong> Quanto mais você compra, mais pacotes grátis acumula.
    """)
    st.caption("1 pacote = 1 ponto • 10 pontos = 1 pacote grátis • 500 pontos = Cafeteira")
    st.markdown('</div>', unsafe_allow_html=True)

# --- Top 10 + Linha extra ---
chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    top_clients = get_top_clients_by_points(limit=10)

    if top_clients:
        df_top = pd.DataFrame(top_clients)
        df_top = df_top.sort_values("total_points_earned", ascending=True)

        fig3 = px.bar(
            df_top,
            x="total_points_earned",
            y="name",
            orientation="h",
            color="total_points_earned",
            color_continuous_scale=["#B91C1C", "#0D9488"],
            labels={"total_points_earned": "Pontos Totais Ganhos", "name": ""},
        )
        fig3.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2937",
            plot_bgcolor="#1e2937",
            title=dict(text="🏆 Top 10 Clientes Mais Fiéis (Pontos Acumulados)", font=dict(size=14, color="#f1f5f9")),
            height=340,
            margin=dict(l=10, r=10, t=35, b=10),
            coloraxis_showscale=False,
            xaxis=dict(gridcolor="#334155"),
            yaxis=dict(gridcolor="#334155", tickfont=dict(size=11)),
            font=dict(color="#cbd5e1"),
        )
        st.plotly_chart(fig3, width='stretch', config={"displayModeBar": False})
    else:
        st.info("Sem clientes suficientes para ranking.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- Atividade Recente ---
with chart_col4:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown("**🕒 Últimas Movimentações**", unsafe_allow_html=True)

    recent = get_recent_activity(limit=7)
    if recent:
        for act in recent:
            if act["type"] == "purchase":
                icon = "💰"
                color = "#10b981"
                detail = f"+{act['points']} pts • {format_currency(act['amount'])}"
            else:
                icon = "🎁"
                color = "#f59e0b"
                detail = f"-{abs(act['points'])} pts • Resgate de pacote(s)"

            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between; align-items:center; 
                            background:#0f172a; border:1px solid #334155; border-radius:10px; 
                            padding:6px 12px; margin-bottom:6px; font-size:0.875rem;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:1.1rem;">{icon}</span>
                        <span style="color:#f1f5f9; font-weight:600;">{act['client_name']}</span>
                    </div>
                    <div style="text-align:right; color:#94a3b8;">
                        <div style="color:{color}; font-weight:600;">{detail}</div>
                        <div style="font-size:0.7rem;">{act['tx_date']}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.caption("Nenhuma movimentação registrada ainda.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ================== SEÇÃO DE GESTÃO DE CLIENTES ==================
st.markdown('<div class="section-header">👥 Gestão de Clientes</div>', unsafe_allow_html=True)

# Filtros e busca (sistema puro de acumulação simples)
filter_col1, filter_col2, filter_col3 = st.columns([2.4, 1.2, 1.3])

with filter_col1:
    search_query = st.text_input(
        "🔍 Buscar por nome ou telefone",
        placeholder="Ex: Ana ou 98765...",
        label_visibility="collapsed",
    )

with filter_col2:
    min_points = st.number_input(
        "Mín. pontos",
        min_value=0,
        value=0,
        step=5,
        label_visibility="visible",
    )

# Busca e filtro (sem filtro de pacotes)
if search_query.strip():
    clients = search_clients(search_query)
else:
    clients = get_all_clients_enriched()

# Aplicar filtros (acumulação simples)
filtered_clients = []
for c in clients:
    if min_points > 0 and c["current_points"] < min_points:
        continue
    # filtro de pacotes removido (sem resgate)
        continue
    filtered_clients.append(c)

# Tabela bonita de clientes
if filtered_clients:
    client_df = pd.DataFrame([
        {
            "ID": c["id"],
            "Nome": c["name"],
            "Telefone": c["phone"],
            "Pontos Atuais": c["current_points"],
            # Pacotes Disp. removido (sem resgate)
            "Volume Mês": round(c["monthly_spent"], 2),
            "Total Gasto": round(c["total_spent"], 2),
        }
        for c in filtered_clients
    ])

    # Mostrar tabela com seleção via clique (usamos um selectbox + dataframe)
    st.dataframe(
        client_df.drop(columns=["ID"]),
        width='stretch',
        hide_index=True,
        column_config={
            "Nome": st.column_config.TextColumn(width="medium"),
            "Pontos Atuais": st.column_config.NumberColumn(format="%d", help="Saldo atual de pontos (acumulado)"),
            "Pacotes Disp.": st.column_config.NumberColumn(help="Pacotes que podem ser resgatados agora"),
            "Volume Mês": st.column_config.NumberColumn(format="R$ %.2f"),
            "Total Gasto": st.column_config.NumberColumn(format="R$ %.2f"),
        },
    )

    # Seletor de cliente
    client_options = {f"{c['name']}  •  {c['phone']}  •  {c['current_points']} pts": c["id"]
                      for c in filtered_clients}

    selected_label = st.selectbox(
        "Selecione um cliente para registrar compra, resgatar ou ver histórico:",
        options=["— Selecione um cliente —"] + list(client_options.keys()),
        index=0,
    )

    if selected_label != "— Selecione um cliente —":
        st.session_state.selected_client_id = client_options[selected_label]
    else:
        if st.session_state.selected_client_id and not any(
            c["id"] == st.session_state.selected_client_id for c in filtered_clients
        ):
            st.session_state.selected_client_id = None

else:
    st.warning("Nenhum cliente encontrado com os filtros atuais.")

# ================== PAINEL DO CLIENTE SELECIONADO ==================
if st.session_state.selected_client_id:
    client = get_client_by_id(st.session_state.selected_client_id)

    if client:
        st.markdown("---")
        st.markdown('<div class="section-header">🎯 Cliente Selecionado</div>', unsafe_allow_html=True)

        # Card grande do cliente (acumulação simples sem multiplicadores)
        # redemption_threshold removido (sem resgate)
        # Sem resgate, mostrar progresso para 500
        remaining_pts = max(0, 500 - client.get("total_packages_bought", 0))

        st.markdown(f"""
        <div class="client-selected">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
                <div>
                    <div class="client-name">{client['name']}</div>
                    <div class="client-phone">📞 {client['phone']}</div>
                </div>
            </div>

            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap:12px; margin-top:1rem;">
                <div>
                    <div style="font-size:0.75rem; color:#64748b;">SALDO DE PONTOS</div>
                    <div style="font-size:2rem; font-weight:800; color:#10b981;">{client['current_points']}</div>
                </div>
                <div>
                    <div style="font-size:0.75rem; color:#64748b;">PACOTES DISPONÍVEIS</div>
                    <div style="font-size:2rem; font-weight:800; color:#f59e0b;">{client.get('total_packages_bought', 0)} / 500</div>
                </div>
                <div>
                    <div style="font-size:0.75rem; color:#64748b;">VOLUME ESTE MÊS</div>
                    <div style="font-size:1.35rem; font-weight:700;">{format_currency(client['monthly_spent'])}</div>
                </div>
                <div>
                    <div style="font-size:0.75rem; color:#64748b;">TOTAL GASTO (VITALÍCIO)</div>
                    <div style="font-size:1.35rem; font-weight:700;">{format_currency(client['total_spent'])}</div>
                </div>
                <div>
                    <div style="font-size:0.75rem; color:#64748b;">PACOTES COMPRADOS</div>
                    <div style="font-size:1.35rem; font-weight:700; color:#f59e0b;">{client.get('total_packages_bought', 0)}</div>
                </div>
            </div>

            <!-- Progresso para o novo marco de 500 pacotes (especial) -->
            <div style="margin-top:0.7rem;">
                <div style="font-size:0.75rem; color:#64748b; margin-bottom:3px;">
                    🏆 PROGRESSO MARCO 500 PACOTES (recompensa especial)
                </div>
                <div style="background:#334155; border-radius:999px; height:9px; overflow:hidden;">
                    <div style="width:{min(100, (client.get('total_packages_bought',0) / max(1, client.get('milestone_packages_threshold',500))) * 100)}%; 
                                background:linear-gradient(90deg,#f59e0b,#fbbf24); height:100%;"></div>
                </div>
                <div style="font-size:0.72rem; color:#94a3b8; margin-top:2px;">
                    {client.get('total_packages_bought', 0)} / {client.get('milestone_packages_threshold', 500)} pacotes
                    {" • 🎁 MARCO ATINGIDO!" if client.get('has_milestone_500') else f" • Faltam {max(0, client.get('milestone_packages_threshold',500) - client.get('total_packages_bought',0))}"}
                </div>
            </div>

            <!-- Sem progresso de resgate - versão simples -->
        </div>
        """, unsafe_allow_html=True)

        # NOVO: Resumo rico de prêmios (usando o helper que criamos)
        rewards = get_rewards_status(
            client['current_points'],
            client.get('total_packages_bought', 0),
        )
        st.markdown(
            f"""<div style="background:#0f172a; border:1px solid #334155; border-radius:10px; padding:10px 14px; margin: 4px 0 10px;">
                <div style="font-size:0.82rem; color:#94a3b8;">🎯 PRÓXIMOS PRÊMIOS</div>
                <div style="font-size:0.95rem; font-weight:600; color:#f1f5f9; line-height:1.35;">
                    {rewards['summary_text']}
                </div>
            </div>""",
            unsafe_allow_html=True
        )

        # AÇÕES RÁPIDAS
        action_col1, action_col2 = st.columns([1, 1])

        # ---- REGISTRAR COMPRA ----
        with action_col1:
            st.markdown("**💰 Registrar Nova Compra**")

            with st.form("register_purchase_form", clear_on_submit=True):
                purchase_amount = st.number_input(
                    "Valor da compra (R$) - opcional para histórico",
                    min_value=1.0,
                    value=190.0,
                    step=38.0,
                    format="%.2f",
                )
                purchase_qty = st.number_input(
                    "Quantidade de pacotes ★ (cada um = +1 ponto)",
                    min_value=0,
                    value=5,
                    step=1,
                    help="1 pacote = 1 ponto. Meta: 500 pontos = Cafeteira",
                )
                purchase_date = st.date_input("Data da compra", value=date.today())

                submitted = st.form_submit_button("✅ Registrar Compra e Conceder Pontos", type="primary", width='stretch')

                if submitted:
                    try:
                        result = register_purchase(
                            client_id=client["id"],
                            amount=purchase_amount,
                            purchase_date=purchase_date,
                            package_quantity=int(purchase_qty),
                        )

                        client = get_client_by_id(client["id"])
                        settings = get_all_settings()
                        auto_notify = settings.get("auto_notify_whatsapp", "true").lower() == "true"

                        # Automação de contato WhatsApp: sempre preparamos o cartão + mensagem + link após a ação
                        # (o admin só precisa clicar em "Enviar no WhatsApp")
                        st.session_state.pending_notification = prepare_points_notification(
                            client, result, notification_type="purchase"
                        )
                        st.session_state.last_action_message = st.session_state.pending_notification["message"]

                        # ============================================================
                        # TOTALMENTE AUTOMATIZADO: Marco de 500 pacotes
                        # Se esta compra cruzou o limite e ainda não foi concedida,
                        # concedemos automaticamente (default: Pix R$ 200) e preparamos
                        # o aviso WhatsApp da recompensa especial. Zero intervenção manual
                        # necessária para a recompensa de volume.
                        # ============================================================
                        client = get_client_by_id(client["id"])  # refresh stats
                        settings = get_all_settings()
                        milestone_th = int(settings.get("milestone_packages_threshold", "500"))
                        if (
                            client.get("total_packages_bought", 0) >= milestone_th
                            and not client.get("has_milestone_500")
                        ):
                            try:
                                claim_milestone_reward(
                                    client_id=client["id"],
                                    milestone="500_pacotes",
                                    reward_choice="cafeteira",
                                    reward_description="Cafeteira",
                                    notes="Concedido automaticamente ao atingir 500 pontos.",
                                )
                                client = get_client_by_id(client["id"])
                                wa_msg = build_milestone_reward_message(client, default_label)
                                wa_url = build_whatsapp_url(client["phone"], wa_msg)
                                log_notification(
                                    client_id=client["id"],
                                    notification_type="milestone",
                                    message=wa_msg,
                                    phone=client["phone"],
                                    status="prepared",
                                )
                                st.session_state.pending_notification = {
                                    "type": "milestone",
                                    "client_name": client["name"],
                                    "phone": client["phone"],
                                    "message": wa_msg,
                                    "wa_url": wa_url,
                                    "card_png": None,
                                    "points": 0,
                                }
                                st.session_state.last_action_message = wa_msg
                                st.balloons()
                            except Exception:
                                # Já concedido ou erro — o painel normal de pontos continua
                                pass

                        refresh_data()
                        st.rerun()

                    except Exception as e:
                        st.error(f"Erro ao registrar compra: {e}")

        # RESGATE REMOVIDO - versão simples
        with action_col2:
            st.markdown("**🎁 Recompensa**")
            st.caption("Apenas Cafeteira aos 500 pontos. Sem resgate.")
            if client.get("has_milestone_500"):
                st.success("Cafeteira conquistada!")
            else:
                st.caption("Meta: 500 pontos = Cafeteira")

        # ========== NOVA SEÇÃO: RECOMPENSA ESPECIAL 500 PACOTES ==========
        threshold = client.get("milestone_packages_threshold", 500)
        total_bought = client.get("total_packages_bought", 0)
        has_claimed = client.get("has_milestone_500", False)

        if total_bought >= threshold and not has_claimed:
            st.markdown("---")
            with st.container(border=True):
                st.markdown("### 🏆🎁 **Recompensa Especial — 500 Pacotes Comprados**")
                st.success("Parabéns! Este cliente atingiu o marco de **500 pacotes**. Escolha o brinde/valor que ele deseja receber.")

                # Opções vindas das configurações (totalmente editáveis)
                texts = get_all_settings()
                reward = texts.get("milestone_reward", "Cafeteira")
                st.info(f"Recompensa automática: **{reward}** (meta simples de 500 pontos)")
                selected_label = reward
                selected_choice = "cafeteira"

                col_claim1, col_claim2 = st.columns([2, 1])
                with col_claim1:
                    claim_notes = st.text_input("Observação (opcional)", value="", key=f"milestone_notes_{client['id']}",
                                                placeholder="Ex: Entregar na próxima visita / Pix para (tel) / etc.")
                with col_claim2:
                    if st.button(f"🎉 CONCEDER {selected_label.upper()}", type="primary", width='stretch', key=f"btn_claim_{client['id']}"):
                        try:
                            claim_result = claim_milestone_reward(
                                client_id=client["id"],
                                milestone="500_pacotes",
                                reward_choice=selected_choice,
                                reward_description=selected_label,
                                notes=claim_notes,
                            )
                            # Mensagem WhatsApp
                            wa_msg = build_milestone_reward_message(client, selected_label)
                            wa_url = build_whatsapp_url(client["phone"], wa_msg)
                            log_notification(
                                client_id=client["id"],
                                notification_type="milestone",
                                message=wa_msg,
                                phone=client["phone"],
                                status="prepared",
                            )

                            st.session_state.pending_notification = {
                                "type": "milestone",
                                "client_name": client["name"],
                                "phone": client["phone"],
                                "message": wa_msg,
                                "wa_url": wa_url,
                                "card_png": None,
                                "points": 0,
                            }
                            st.session_state.last_action_message = wa_msg
                            st.balloons()
                            refresh_data()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao conceder recompensa: {e}")
        elif has_claimed:
            st.caption(f"✅ Recompensa 500 pacotes já concedida: **{client.get('milestone_500_desc', client.get('milestone_500_choice'))}** em {client.get('milestone_500_date','')}")

        # Painel de aviso automático (após compra ou resgate)
        if st.session_state.pending_notification:
            render_notification_panel(st.session_state.pending_notification)

        # HISTÓRICO DO CLIENTE
        st.markdown("**📜 Histórico Completo do Cliente**")

        history = get_client_history(client["id"])

        if history:
            hist_df = pd.DataFrame([
                {
                    "Data": h["date"],
                    "Tipo": (
                        "💰 COMPRA" if h["type"] == "purchase" else
                        ("🎁 RESGATE" if h["type"] == "redemption" else "🏆 RECOMPENSA ESPECIAL")
                    ),
                    "Valor": format_currency(h["amount"]) if h["amount"] else "—",
                    "Pontos": h["points"],
                    "Observação": h["notes"] or "—",
                }
                for h in history
            ])

            st.dataframe(
                hist_df,
                width='stretch',
                hide_index=True,
                column_config={
                    "Pontos": st.column_config.NumberColumn(format="%+d"),
                },
            )

            # Mini gráfico de pontos acumulados do cliente
            cumulative = 0
            cum_data = []
            for h in reversed(history):  # do mais antigo pro mais novo
                cumulative += h["points"]
                cum_data.append({"Data": h["date"], "Pontos Acumulados": max(0, cumulative)})

            if len(cum_data) > 1:
                df_cum = pd.DataFrame(cum_data)
                fig_cum = px.line(
                    df_cum,
                    x="Data",
                    y="Pontos Acumulados",
                    markers=True,
                    title=f"Evolução de Pontos de {client['name']}",
                )
                fig_cum.update_traces(line_color="#0D9488", marker=dict(color="#0D9488", size=6))
                fig_cum.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#1e2937",
                    height=220,
                    margin=dict(l=10, r=10, t=30, b=10),
                )
                st.plotly_chart(fig_cum, width='stretch', config={"displayModeBar": False})
        else:
            st.caption("Ainda não há movimentações para este cliente.")

        # ================== ENVIAR PORTAL DO CLIENTE (O QUE VOCÊ MANDA PRO CLIENTE) ==================
        st.markdown("---")
        st.markdown("**📤 Enviar Portal do Cliente (o que você envia pro cliente)**")

        texts = get_program_texts()
        program_name = texts.get("program_name", "Programa Parceiro Isopor")

        # Gera link do portal usando a URL pública configurada pelo admin
        base_url = get_public_base_url()
        client_link = f"{base_url}/?view=cliente&id={client['id']}"

        st.info(f"**Link para enviar ao cliente:**\n`{client_link}`")

        col_link1, col_link2 = st.columns(2)
        with col_link1:
            if st.button("📋 Copiar Link do Portal", width='stretch'):
                st.code(client_link)
                st.success("Link copiado! Cole no WhatsApp ou e-mail do cliente.")

        with col_link2:
            first = get_first_name(client['name'])
            link_msg = f"Olá {first}! Aqui está o seu painel de fidelidade do {program_name}. Acompanhe seus pontos e pacotes: {client_link}"
            if st.button("📱 Gerar WhatsApp com o Link", width='stretch'):
                st.code(link_msg)
                st.caption("Copie e envie para o cliente. O link abre a visão limpa e bonita só dele.")

        with st.expander("👀 Preview do que o cliente vê"):
            st.markdown(f"**{client['name']}** — {client['phone']}")
            st.markdown(f"Pontos: **{client['current_points']}** / 500")
            st.caption("Interface limpa, sem ferramentas de admin. Perfeita para enviar. (Pontos são cumulativos.)")

        # MENSAGENS WHATSAPP PRONTAS
        st.markdown("**💬 Mensagens Prontas para WhatsApp**")

        msg_col1, msg_col2 = st.columns(2)

        with msg_col1:
            if st.button("📋 Gerar Resumo Mensal", width='stretch'):
                summary_msg = create_monthly_summary_message(
                    client["name"],
                    client["monthly_spent"],
                    client["total_earned_points"] - client.get("total_redeemed_points", 0),
                    0,  # sem resgate
                )
                st.code(summary_msg, language=None)
                st.session_state.last_action_message = summary_msg

        with msg_col2:
            if st.button("📋 Mensagem Promocional Geral", width='stretch'):
                promo = create_promotional_message()
                st.code(promo, language=None)
                st.session_state.last_action_message = promo

        # Botão limpar seleção
        if st.button("✖ Fechar painel deste cliente", on_click=clear_selection, type="secondary", width='stretch'):
            pass

# ================== SIDEBAR - AÇÕES RÁPIDAS E EXPORT ==================
with st.sidebar:
    st.markdown("### 🌐 Portal dos Clientes + Servidor Público")

    portal_url = PUBLIC_PORTAL_URL or get_public_url() or get_public_base_url()
    is_public = portal_url and "localhost" not in portal_url and "127.0.0.1" not in portal_url

    if is_public:
        st.success("✅ **PORTAL PÚBLICO ATIVO**")
        st.code(portal_url, language=None)
        st.caption("Links dos clientes funcionam para qualquer pessoa com o endereço.")
    else:
        st.error("🔗 Links dos clientes ainda estão locais (localhost)")

        # ==================== ATALHO PRINCIPAL (o que o usuário pediu) ====================
        st.markdown("**Clique uma única vez para ativar tudo:**")
        if st.button(
            "🚀 ATIVAR AGORA\nLinks dos Clientes + Túnel + Estrutura Completa",
            type="primary",
            width='stretch',
            key="activate_public_portal_btn"
        ):
            with st.spinner("Iniciando estrutura completa do servidor e túnel público..."):
                try:
                    # Executa o serve.sh de forma detached (ele sobe o túnel cloudflared + salva a URL no banco)
                    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".logs", "activate_portal.log")
                    os.makedirs(os.path.dirname(log_path), exist_ok=True)

                    subprocess.Popen(
                        ["bash", "./serve.sh"],
                        cwd=os.path.dirname(os.path.abspath(__file__)),
                        stdout=open(log_path, "a"),
                        stderr=subprocess.STDOUT,
                        start_new_session=True,   # O processo sobrevive depois que o botão termina
                        env=os.environ.copy(),
                    )

                    st.success("✅ Comando enviado com sucesso!")
                    st.info("O túnel (cloudflared) está sendo iniciado. Aguarde 15~40 segundos e atualize a página.")
                    time.sleep(2.5)
                    st.rerun()

                except Exception as e:
                    st.error(f"Não foi possível iniciar automaticamente: {e}")
                    st.markdown("**Solução manual rápida:**")
                    st.code("./serve.sh", language="bash")
                    st.caption("Abra outro terminal na pasta do projeto e rode o comando acima.")

        st.caption("Isso sobe o Streamlit (se necessário) + o túnel público e salva a URL automaticamente no sistema.")

    # Botão auxiliar rápido
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Verificar URL agora", width='stretch'):
            # Força re-execução da detecção de túnel (o _ensure já faz isso no rerun)
            st.cache_resource.clear()
            st.success("Verificando... recarregando")
            time.sleep(0.8)
            st.rerun()
    with col2:
        if st.button("📋 Copiar ./serve.sh", width='stretch'):
            st.code("./serve.sh", language="bash")

    st.divider()
    render_bulletin_admin_panel()

    st.divider()
    st.markdown("### ⚙️ Ações Rápidas")

    with st.expander("➕ Cadastrar Novo Cliente", expanded=False):
        with st.form("new_client_form"):
            new_name = st.text_input("Nome completo *")
            new_phone = st.text_input("Telefone (com DDD) *", placeholder="(11) 99999-0000")

            if st.form_submit_button("Cadastrar Cliente", type="primary"):
                if new_name.strip() and new_phone.strip():
                    try:
                        new_id = add_client(new_name, new_phone)
                        st.success(f"Cliente **{new_name}** cadastrado com sucesso!")
                        select_client(new_id)
                        refresh_data()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e} (telefone pode já existir)")
                else:
                    st.warning("Preencha nome e telefone.")

    st.divider()

    # Exportar Excel
    st.markdown("### 📥 Exportar Relatório")

    if st.button("📊 Gerar Excel Completo", type="primary", width='stretch'):
        with st.spinner("Gerando relatório profissional..."):
            all_clients = get_all_clients_enriched()
            monthly_hist = get_monthly_purchase_history(months_back=12)
            top10 = get_top_clients_by_points(10)
            recent = get_recent_activity(20)

            excel_buffer = export_full_report(
                clients=all_clients,
                kpis=kpis,
                monthly_history=monthly_hist,
                top_clients=top10,
                recent_activity=recent,
            )

            st.download_button(
                label="⬇️ Baixar Relatório Excel (.xlsx)",
                data=excel_buffer,
                file_name=f"parceiro_isopor_relatorio_{date.today().isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='stretch',
            )

    st.caption("O Excel contém 5 abas: Resumo, Clientes, Histórico Mensal, Top Fiéis e Atividade Recente.")

    st.divider()

    st.markdown("### 📘 Manual de Uso")
    if MANUAL_PDF_PATH.exists():
        st.caption(f"Arquivo salvo em: `{MANUAL_PDF_PATH.name}`")
    if st.button("📄 Gerar / Atualizar Manual (PDF)", type="primary", width='stretch'):
        with st.spinner("Gerando manual em PDF..."):
            saved_path = save_user_manual(get_all_settings())
            pdf_buffer = generate_user_manual(get_all_settings())
            st.success(f"Manual salvo em `{saved_path}`")
            st.download_button(
                label="⬇️ Baixar Manual de Uso (PDF)",
                data=pdf_buffer,
                file_name=f"manual_parceiro_isopor_{date.today().isoformat()}.pdf",
                mime="application/pdf",
                width='stretch',
            )

    st.divider()

    st.markdown("### 📲 Avisos Recentes")
    recent_notifs = get_recent_notifications(5)
    if recent_notifs:
        for n in recent_notifs:
            icon = "💰" if n["notification_type"] == "purchase" else ("🎁" if n["notification_type"] == "redemption" else "🏆")
            st.caption(f"{icon} **{n['client_name']}** — {n['created_at'][:16]} — {n['status']}")
    else:
        st.caption("Nenhum aviso enviado ainda. Registre uma compra para gerar o primeiro.")

    st.divider()

    # ================== PERSONALIZAÇÃO TOTAL PELO ADMIN ==================
    with st.expander("⚙️ Personalizar Programa (totalmente editável)", expanded=False):
        st.markdown("**Edite as regras e todos os textos. Tudo é salvo automaticamente.**")

        current_rules = get_program_rules()
        current_texts = get_all_settings()

        with st.form("personalization_form"):
            st.markdown("**Regras (versão simples)**")
            st.caption("1 pacote = 1 ponto. Sem resgate de pacotes. Apenas meta 500.")

            st.markdown("**Textos e Conteúdo da Interface**")
            new_program_name = st.text_input("Nome do Programa", value=current_texts.get("program_name", ""))
            new_subtitle = st.text_input("Subtítulo (admin)", value=current_texts.get("program_subtitle", ""))
            new_admin_welcome = st.text_area("Saudação inicial (admin)", value=current_texts.get("admin_welcome", ""), height=60)

            st.markdown("**Textos do Portal do Cliente**")
            new_client_title = st.text_input("Título no portal do cliente", value=current_texts.get("client_portal_title", ""))
            new_client_intro = st.text_area("Introdução para o cliente", value=current_texts.get("client_portal_intro", ""), height=60)

            st.markdown("**Templates de WhatsApp (use {first_name}, {program_name}, {amount} etc.)**")
            new_wa_purchase = st.text_area("Mensagem após compra", value=current_texts.get("whatsapp_purchase", ""), height=120)
            # Sem mensagem de resgate (removido)
            new_wa_monthly = st.text_area("Mensagem resumo mensal", value=current_texts.get("whatsapp_monthly", ""), height=100)
            new_wa_promo = st.text_area("Mensagem promocional", value=current_texts.get("whatsapp_promo", ""), height=100)

            st.markdown("**Automação de Avisos**")
            new_auto_notify = st.checkbox(
                "Gerar aviso automático ao conceder pontos",
                value=current_texts.get("auto_notify_whatsapp", "true").lower() == "true",
            )
            new_auto_open = st.checkbox(
                "Abrir WhatsApp automaticamente após compra",
                value=current_texts.get("auto_open_whatsapp", "true").lower() == "true",
            )

            st.markdown("**Cartão Estático de Pontos (PNG)**")
            card_col1, card_col2 = st.columns(2)
            with card_col1:
                new_card_title = st.text_input("Título do cartão", value=current_texts.get("card_title", ""))
                new_card_subtitle = st.text_input("Subtítulo do cartão", value=current_texts.get("card_subtitle", ""))
                new_card_footer = st.text_input("Rodapé do cartão", value=current_texts.get("card_footer", ""))
                new_card_emoji = st.text_input("Emoji do cartão", value=current_texts.get("card_emoji", "🎉"))
            with card_col2:
                new_card_primary = st.color_picker("Cor primária", value=current_texts.get("card_primary_color", "#0D9488"))
                new_card_secondary = st.color_picker("Cor de fundo", value=current_texts.get("card_secondary_color", "#0f172a"))
                new_card_accent = st.color_picker("Cor de destaque", value=current_texts.get("card_accent_color", "#10b981"))
                new_card_show_bal = st.checkbox(
                    "Exibir saldo atual no cartão (recomendado — mostra o total cumulativo)",
                    value=current_texts.get("card_show_balance", "true").lower() == "true",
                )

            st.markdown("**Texto das Regras na barra lateral (markdown suportado)**")
            new_sidebar_rules = st.text_area("Regras (sidebar)", value=current_texts.get("sidebar_rules_text", ""), height=140)

            # ========== META 500 (simples) ==========
            st.markdown("---")
            st.markdown("**🏆 Meta 500 Pontos (Cafeteira)**")
            st.caption("Ao atingir 500 pacotes comprados o cliente ganha automaticamente a Cafeteira.")
            new_milestone_threshold = st.number_input(
                "Meta de pacotes/pontos",
                value=int(current_texts.get("milestone_packages_threshold", 500)),
                min_value=100, step=50
            )
            st.text_input("Recompensa (fixa)", value="Cafeteira", disabled=True)

            new_wa_milestone = st.text_area(
                "Mensagem WhatsApp quando bater a meta",
                value=current_texts.get("whatsapp_milestone_500", ""),
                height=90
            )

            submitted_pers = st.form_submit_button("💾 Salvar Todas as Personalizações", type="primary", width='stretch')

            if submitted_pers:
                pass  # sem redemption na versão simples
                set_setting("program_name", new_program_name)
                set_setting("program_subtitle", new_subtitle)
                set_setting("admin_welcome", new_admin_welcome)
                set_setting("client_portal_title", new_client_title)
                set_setting("client_portal_intro", new_client_intro)
                set_setting("whatsapp_purchase", new_wa_purchase)
                set_setting("whatsapp_monthly", new_wa_monthly)
                set_setting("whatsapp_promo", new_wa_promo)
                set_setting("auto_notify_whatsapp", "true" if new_auto_notify else "false")
                set_setting("auto_open_whatsapp", "true" if new_auto_open else "false")
                set_setting("card_title", new_card_title)
                set_setting("card_subtitle", new_card_subtitle)
                set_setting("card_footer", new_card_footer)
                set_setting("card_emoji", new_card_emoji)
                set_setting("card_primary_color", new_card_primary)
                set_setting("card_secondary_color", new_card_secondary)
                set_setting("card_accent_color", new_card_accent)
                set_setting("card_show_balance", "true" if new_card_show_bal else "false")
                set_setting("sidebar_rules_text", new_sidebar_rules)

                # Salva configurações do novo marco 500 pacotes
                set_setting("milestone_packages_threshold", str(int(new_milestone_threshold)))
                set_setting("milestone_reward", "Cafeteira")
                set_setting("whatsapp_milestone_500", new_wa_milestone)

                st.success("Personalizações salvas! O painel será atualizado.")
                st.cache_data.clear()
                st.rerun()

        st.divider()
        st.markdown("**Zerar dados para uso real**")
        st.warning("Isso remove TODOS os clientes, compras e resgates. As configurações personalizadas são mantidas.")
        if st.button("🗑️ ZERAR TODOS OS DADOS DE CLIENTES (irrevogável)", type="secondary", width='stretch'):
            if st.session_state.get("confirm_reset", False):
                reset_client_data(keep_settings=True)
                st.success("Dados de clientes zerados com sucesso! Sistema pronto para uso real.")
                st.session_state["confirm_reset"] = False
                st.cache_data.clear()
                st.rerun()
            else:
                st.session_state["confirm_reset"] = True
                st.warning("Clique novamente no botão para confirmar a exclusão de todos os dados de clientes.")

    # Mensagem geral
    st.divider()
    st.markdown("### 📢 Divulgação")
    if st.button("📋 Copiar texto de divulgação do programa", width='stretch'):
        promo = create_promotional_message()
        st.code(promo, language=None)

    st.divider()

    st.markdown("### ℹ️ Regras do Programa")
    rules_text = ALL_SETTINGS.get("sidebar_rules_text", "")
    st.markdown(rules_text)

    st.divider()
    st.caption("IsoSoluções • 2026\nDashboard feito para impressionar 💚")

# ================== FOOTER ==================
footer = ALL_SETTINGS.get("footer_text", "IsoSoluções")
st.markdown(f"""
<div class="footer">
    {footer.replace(chr(10), '<br>')}
</div>
""", unsafe_allow_html=True)
