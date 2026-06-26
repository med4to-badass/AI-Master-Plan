"""
bulletin_board.py
Mural de atualizações — exibição e gestão para admin e portal do cliente.
"""

from datetime import datetime
from html import escape
from typing import List, Dict, Any

import streamlit as st

from database import (
    get_bulletin_updates,
    add_bulletin_update,
    update_bulletin_update,
    delete_bulletin_update,
)


def _format_date(iso_str: str) -> str:
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00")[:19])
        return dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return iso_str[:10] if len(iso_str) >= 10 else iso_str


def _render_item_html(item: Dict[str, Any], compact: bool = False) -> str:
    title = escape(item.get("title", ""))
    content = escape(item.get("content", ""))
    date_label = _format_date(item.get("updated_at") or item.get("created_at", ""))

    if compact:
        return f"""
        <div class="bulletin-item">
            <div class="bulletin-item-title">{title}</div>
            <div class="bulletin-item-content">{content}</div>
            <div class="bulletin-item-date">{date_label}</div>
        </div>
        """

    return f"""
    <div class="bulletin-item">
        <div class="bulletin-item-header">
            <span class="bulletin-item-title">{title}</span>
            <span class="bulletin-item-date">{date_label}</span>
        </div>
        <div class="bulletin-item-content">{content}</div>
    </div>
    """


def render_bulletin_board(client_view: bool = False, max_items: int = 4) -> None:
    """Exibe o mural de atualizações de forma discreta mas visível."""
    updates = get_bulletin_updates(active_only=True, client_view=client_view, limit=max_items)

    if not updates:
        return

    label = "Atualizações" if client_view else "Mural de Atualizações"
    items_html = "".join(_render_item_html(u, compact=client_view) for u in updates)

    st.markdown(
        f"""
        <div class="bulletin-board {'bulletin-board-client' if client_view else ''}">
            <div class="bulletin-board-header">
                <span class="bulletin-board-icon">📌</span>
                <span class="bulletin-board-label">{label}</span>
            </div>
            <div class="bulletin-board-items">
                {items_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_bulletin_admin_panel() -> None:
    """Painel de gestão do mural na sidebar do admin."""
    with st.expander("📌 Mural de Atualizações", expanded=False):
        st.caption("Publique avisos visíveis no painel admin e no portal do cliente.")

        with st.form("new_bulletin_form", clear_on_submit=True):
            new_title = st.text_input("Título do aviso", placeholder="Ex: Novo horário de atendimento")
            new_content = st.text_area(
                "Mensagem",
                placeholder="Descreva a atualização para os parceiros...",
                height=80,
            )
            new_show_clients = st.checkbox("Exibir no portal do cliente", value=True)
            if st.form_submit_button("Publicar aviso", type="primary", width='stretch'):
                if new_title.strip() and new_content.strip():
                    add_bulletin_update(new_title, new_content, show_to_clients=new_show_clients)
                    st.success("Aviso publicado!")
                    st.rerun()
                else:
                    st.warning("Preencha título e mensagem.")

        st.divider()
        st.markdown("**Avisos publicados**")

        all_updates = get_bulletin_updates(active_only=False, client_view=False, limit=20)
        if not all_updates:
            st.caption("Nenhum aviso ainda. Publique o primeiro acima.")
            return

        for item in all_updates:
            status = "🟢" if item.get("is_active") else "⚪"
            client_flag = "👤" if item.get("show_to_clients") else "🔒"
            date_label = _format_date(item.get("updated_at") or item.get("created_at", ""))

            with st.container(border=True):
                st.markdown(f"{status} {client_flag} **{item['title']}** — _{date_label}_")
                st.caption(item["content"][:120] + ("..." if len(item["content"]) > 120 else ""))

                edit_key = f"edit_bulletin_{item['id']}"
                if st.session_state.get(edit_key):
                    with st.form(f"edit_form_{item['id']}"):
                        edit_title = st.text_input("Título", value=item["title"], key=f"et_{item['id']}")
                        edit_content = st.text_area(
                            "Mensagem",
                            value=item["content"],
                            height=70,
                            key=f"ec_{item['id']}",
                        )
                        edit_show = st.checkbox(
                            "Exibir no portal do cliente",
                            value=bool(item.get("show_to_clients")),
                            key=f"es_{item['id']}",
                        )
                        edit_active = st.checkbox(
                            "Ativo (visível)",
                            value=bool(item.get("is_active")),
                            key=f"ea_{item['id']}",
                        )
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.form_submit_button("Salvar", type="primary", width='stretch'):
                                update_bulletin_update(
                                    item["id"],
                                    edit_title,
                                    edit_content,
                                    show_to_clients=edit_show,
                                    is_active=edit_active,
                                )
                                st.session_state[edit_key] = False
                                st.rerun()
                        with col_cancel:
                            if st.form_submit_button("Cancelar", width='stretch'):
                                st.session_state[edit_key] = False
                                st.rerun()
                else:
                    col_edit, col_toggle, col_del = st.columns(3)
                    with col_edit:
                        if st.button("Editar", key=f"btn_edit_{item['id']}", width='stretch'):
                            st.session_state[edit_key] = True
                            st.rerun()
                    with col_toggle:
                        new_active = not bool(item.get("is_active"))
                        toggle_label = "Ativar" if new_active else "Ocultar"
                        if st.button(toggle_label, key=f"btn_toggle_{item['id']}", width='stretch'):
                            update_bulletin_update(
                                item["id"],
                                item["title"],
                                item["content"],
                                show_to_clients=bool(item.get("show_to_clients")),
                                is_active=new_active,
                            )
                            st.rerun()
                    with col_del:
                        if st.button("Excluir", key=f"btn_del_{item['id']}", width='stretch'):
                            delete_bulletin_update(item["id"])
                            st.rerun()