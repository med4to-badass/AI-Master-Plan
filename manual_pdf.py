"""
manual_pdf.py
Gera manual de uso em PDF para o Programa Parceiro Isopor.
"""

from datetime import datetime, timezone, timedelta

_BRT = timezone(timedelta(hours=-3))
from io import BytesIO
from pathlib import Path
from typing import Any, Dict

MANUAL_PDF_PATH = Path(__file__).parent / "MANUAL_DE_USO.pdf"

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ManualTitle",
            parent=base["Title"],
            fontSize=22,
            textColor=colors.HexColor("#0D9488"),
            spaceAfter=12,
            alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "ManualSubtitle",
            parent=base["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#64748b"),
            alignment=TA_CENTER,
            spaceAfter=20,
        ),
        "h1": ParagraphStyle(
            "ManualH1",
            parent=base["Heading1"],
            fontSize=16,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=16,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "ManualH2",
            parent=base["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#0D9488"),
            spaceBefore=12,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "ManualBody",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "bullet": ParagraphStyle(
            "ManualBullet",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            leftIndent=18,
            bulletIndent=6,
            spaceAfter=4,
        ),
        "footer": ParagraphStyle(
            "ManualFooter",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#94a3b8"),
            alignment=TA_CENTER,
        ),
    }


def generate_user_manual(settings: Dict[str, Any] = None) -> BytesIO:
    """Gera manual de uso completo em PDF. Retorna BytesIO."""
    settings = settings or {}
    program_name = settings.get("program_name", "Programa Parceiro Isopor")
    threshold = settings.get("redemption_threshold", "10")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Manual de Uso - {program_name}",
    )

    s = _styles()
    story = []
    now = datetime.now(tz=_BRT).strftime("%d/%m/%Y às %H:%M")

    story.append(Paragraph(f"Manual de Uso", s["title"]))
    story.append(Paragraph(f"{program_name} — Dashboard IsoSoluções", s["subtitle"]))
    story.append(Paragraph(f"Gerado em {now}", s["footer"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0D9488")))
    story.append(Spacer(1, 0.5 * cm))

    sections = [
        (
            "1. Introdução",
            [
                "Este manual descreve como usar o dashboard do programa de fidelidade IsoSoluções. "
                "O sistema permite cadastrar clientes, registrar compras (com quantidade de pacotes), conceder pontos automaticamente, "
                "conceder recompensas especiais de marco (500 pacotes), avisar clientes via WhatsApp e personalizar todas as mensagens e o cartão de pontos.",
            ],
            [],
        ),
        (
            "2. Instalação e Primeiro Acesso",
            [
                "Entre na pasta aura_isopor_dashboard e instale as dependências com: pip install -r requirements.txt",
                "Inicie o dashboard com: streamlit run app.py ou ./INICIAR.sh",
                "O navegador abrirá em http://localhost:8501. O banco SQLite é criado automaticamente.",
            ],
            [],
        ),
        (
            "3. Regras do Programa (padrão — atualizado)",
            [],
            [
                "1 pacote comprado = 1 ponto",
                f"A cada {threshold} pontos = 1 pacote grátis (qualquer espessura)",
                "• Seus pontos são **cumulativos**: cada ponto soma ao saldo anterior (sem bônus por faixa mensal).",
                "• Na compra/acúmulo de 500 pacotes: cliente escolhe entre 5 opções (Desconto R$ 200 / Pix R$ 200 / Liquidificador / Cafeteira / Torradeira)",
            ],
        ),
        (
            "4. Cadastro de Clientes",
            [
                "No menu lateral, abra 'Cadastrar Novo Cliente'. Informe nome completo e telefone com DDD.",
                "O telefone é usado para gerar o link automático do WhatsApp ao conceder pontos.",
            ],
            [],
        ),
        (
            "5. Registrar Compra e Conceder Pontos",
            [
                "Selecione o cliente. Informe a quantidade de pacotes comprados.",
                "Cada pacote = 1 ponto automaticamente. O sistema atualiza o saldo.",
                "Após o registro, o aviso automático é preparado: mensagem WhatsApp + cartão estático PNG (com o total cumulativo).",
            ],
            [],
        ),
        (
            "6. Aviso Automático de Pontos (WhatsApp)",
            [
                "Ao registrar uma compra, o sistema gera automaticamente a mensagem personalizada e o cartão de pontos.",
                "Use o botão 'Enviar no WhatsApp' para abrir o aplicativo com a mensagem já preenchida para o cliente.",
                "Se 'Abrir WhatsApp automaticamente' estiver ativo nas configurações, o link abre sozinho após cada compra.",
                "O histórico de avisos fica registrado no painel de notificações.",
            ],
            [
                "Placeholders da mensagem de compra: {first_name}, {program_name}, {amount}, {final_points}, {current_points}, {package_message}.",
            ],
        ),
        (
            "7. Cartão Estático de Pontos",
            [
                "O cartão PNG é gerado automaticamente após cada compra. Baixe-o e envie junto com a mensagem no WhatsApp.",
                "Personalize título, subtítulo, rodapé, emoji e cores na seção 'Cartão de Pontos' do menu lateral.",
                "Você pode exibir ou ocultar o saldo atual no cartão (o sistema não usa mais bônus/multiplicadores).",
            ],
            [],
        ),
        (
            "8. Resgate de Pacotes",
            [
                "Na seção 'Resgatar Pacote(s) Grátis', informe quantos pacotes o cliente deseja resgatar.",
                "O sistema valida o saldo e gera mensagem de confirmação para WhatsApp.",
            ],
            [],
        ),
        (
            "9. Portal do Cliente",
            [
                "Cada cliente possui um link exclusivo para acompanhar pontos, pacotes e histórico.",
                "Use 'Enviar Portal do Cliente' para copiar o link ou gerar mensagem WhatsApp com o link.",
                "Configure a URL pública em Personalizar Programa para links funcionarem fora da rede local.",
                "Use ./INICIAR.sh ou ngrok/Cloudflare tunnel para expor o portal online.",
            ],
            [],
        ),
        (
            "10. Personalização no Dashboard",
            [
                "Abra 'Personalizar Programa' no menu lateral para editar regras, textos, templates WhatsApp e cartão.",
                "Todas as alterações são salvas no banco SQLite e aplicadas imediatamente.",
                "Use 'Zerar dados para uso real' para remover clientes de demonstração mantendo suas configurações.",
            ],
            [],
        ),
        (
            "11. Exportação de Relatórios",
            [
                "O botão 'Gerar Excel Completo' cria relatório com 5 abas: Resumo, Clientes, Histórico, Top Fiéis e Atividade.",
                "Este manual em PDF pode ser baixado a qualquer momento pelo menu lateral.",
            ],
            [],
        ),
        (
            "12. Dicas Rápidas",
            [],
            [
                "Os pontos são sempre somados ao saldo anterior do cliente (acumulação crescente).",
                "Envie o cartão PNG + mensagem WhatsApp para reforçar o engajamento do cliente.",
                "Revise os templates de mensagem periodicamente para manter o tom da sua marca.",
                "Faça backup do arquivo isopor_parceiro.db para preservar todos os dados.",
            ],
        ),
    ]

    for title, paragraphs, bullets in sections:
        story.append(Paragraph(title, s["h1"]))
        for p in paragraphs:
            story.append(Paragraph(p, s["body"]))
        for b in bullets:
            story.append(Paragraph(f"• {b}", s["bullet"]))
        story.append(Spacer(1, 0.2 * cm))

    story.append(PageBreak())
    story.append(Paragraph("Referência Rápida — Atalhos", s["h1"]))

    table_data = [
        ["Ação", "Onde encontrar"],
        ["Cadastrar cliente", "Sidebar → Cadastrar Novo Cliente"],
        ["Registrar compra", "Selecionar cliente → Registrar Nova Compra"],
        ["Enviar aviso WhatsApp", "Após compra → Enviar no WhatsApp"],
        ["Baixar cartão PNG", "Após compra → Baixar Cartão de Pontos"],
        ["Personalizar mensagens", "Sidebar → Personalizar Programa → WhatsApp"],
        ["Personalizar cartão", "Sidebar → Personalizar Programa → Cartão de Pontos"],
        ["Exportar Excel", "Sidebar → Gerar Excel Completo"],
        ["Baixar este manual", "Sidebar → Baixar Manual de Uso (PDF)"],
        ["Portal do cliente", "Selecionar cliente → Enviar Portal do Cliente"],
    ]

    t = Table(table_data, colWidths=[7 * cm, 9 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D9488")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0fdfa")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1")))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            f"IsoSoluções • {program_name} • Aura Project<br/>"
            "Dashboard de Fidelidade — Manual gerado automaticamente",
            s["footer"],
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer


def save_user_manual(settings: Dict[str, Any] = None, path: Path = None) -> Path:
    """Gera e salva o manual em PDF no disco. Retorna o caminho do arquivo."""
    target = path or MANUAL_PDF_PATH
    pdf_buffer = generate_user_manual(settings)
    target.write_bytes(pdf_buffer.getvalue())
    return target