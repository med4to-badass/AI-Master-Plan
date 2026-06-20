# app_simplificado.py
# Versão simplificada do Dashboard - Programa Parceiro Isopor
# Removido o sistema de resgate de pacotes (10 pontos = 1 pacote grátis)
# Mantido apenas: 1 pacote = 1 ponto + meta de 500 pontos = Cafeteira

"""
Dashboard Principal - Programa Parceiro Isopor (Versão Simplificada)
Aura Project

Principais mudanças:
- Removido resgate de pacotes (10 pontos = 1 pacote)
- Sistema 100% cumulativo: 1 pacote = 1 ponto
- Apenas meta de 500 pontos = Cafeteira
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
from calculations import calcular_pontos_e_gerar_mensagem
from database import (
    get_client_by_id,
    register_purchase,
    get_client_history,
    get_dashboard_kpis,
)
from notifications import build_whatsapp_url

# ================== CONFIGURAÇÃO DA PÁGINA ==================
st.set_page_config(
    page_title="IsoSoluções | Programa Parceiro Isopor (Simplificado)",
    page_icon="♻️",
    layout="wide",
)

# ================== ESTILO BÁSICO ==================
st.markdown("""
<style>
.stApp {
    background: #0b1120;
    color: #f1f5f9;
}
</style>
""", unsafe_allow_html=True)

# ================== INICIALIZAÇÃO ==================
st.title("IsoSoluções - Programa Parceiro Isopor (Versão Simples)")

st.info("**Versão Simplificada**: 1 pacote = 1 ponto | Meta: 500 pontos = Cafeteira")

# ================== SELEÇÃO DE CLIENTE ==================
st.subheader("Selecione o Cliente")

# Aqui você pode colocar seu seletor de cliente normal
# Por enquanto, um exemplo simples:

client_id = st.number_input("ID do Cliente (exemplo)", min_value=1, value=1)

if st.button("Carregar Cliente"):
    client = get_client_by_id(client_id)
    
    if client:
        st.success(f"Cliente carregado: **{client['name']}**")
        st.write(f"**Pontos atuais:** {client['current_points']}")
        st.write(f"**Pacotes comprados:** {client.get('total_packages_bought', 0)}")

        # ================== REGISTRAR COMPRA SIMPLIFICADA ==================
        st.markdown("---")
        st.subheader("Registrar Compra")

        with st.form("form_compra"):
            valor = st.number_input("Valor da compra (R$)", min_value=38.0, step=38.0)
            pacotes = st.number_input("Quantidade de pacotes", min_value=1, value=5)
            submitted = st.form_submit_button("Registrar Compra")

            if submitted:
                # Chama a função simplificada
                mensagem, novo_saldo, pontos_ganhos = calcular_pontos_e_gerar_mensagem(
                    cliente_nome=client['name'],
                    valor_compra=valor,
                    saldo_atual=client['current_points']
                )

                st.success("Compra registrada!")
                st.code(mensagem)

                # Link para WhatsApp
                wa_url = build_whatsapp_url(client['phone'], mensagem)
                st.link_button("📱 Enviar no WhatsApp", wa_url)

    else:
        st.error("Cliente não encontrado.")

# ================== INSTRUÇÕES ==================
st.markdown("---")
st.caption("Esta é uma versão simplificada. O sistema agora tem apenas 1 pacote = 1 ponto e meta de 500 pontos = Cafeteira.")