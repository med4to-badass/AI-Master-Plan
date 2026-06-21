"""
notification_card.py
Gera cartão estático (PNG) para avisar clientes sobre pontos ganhos.
Cores e textos personalizáveis via app_settings.
"""

from io import BytesIO
from typing import Any, Dict, Optional

from PIL import Image, ImageDraw, ImageFont

from calculations import format_currency, get_milestone_progress

def _hex_to_rgb(hex_color: str, fallback: tuple = (16, 185, 129)) -> tuple:
    color = (hex_color or "").strip().lstrip("#")
    if len(color) != 6:
        return fallback
    try:
        return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return fallback


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list:
    words = text.split()
    if not words:
        return [""]
    lines, current = [], words[0]
    for word in words[1:]:
        test = f"{current} {word}"
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def generate_points_card(
    client_name: str,
    points_earned: int,
    current_points: int,
    amount: float,
    settings: Optional[Dict[str, Any]] = None,
    # Novos parâmetros para avisos profissionais de "quanto falta"
    available_packages: int = 0,
    points_to_next_package: int = 0,
    total_packages_bought: int = 0,
    milestone_remaining: int = 0,
) -> BytesIO:
    """
    Cartão de Fidelidade PROFISSIONAL (PNG).
    Design premium com gradiente, saldo cumulativo claro e avisos visuais
    de quanto falta para o próximo pacote e para a recompensa de 500.
    Totalmente personalizado pelas configurações do admin.
    """
    settings = settings or {}
    width, height = 860, 560   # Formato cartão de fidelidade mais largo e premium

    primary = _hex_to_rgb(settings.get("card_primary_color", "#0D9488"))
    secondary = _hex_to_rgb(settings.get("card_secondary_color", "#0f172a"))
    accent = _hex_to_rgb(settings.get("card_accent_color", "#10b981"))
    text_color = (241, 245, 249)
    muted = (148, 163, 184)
    card_bg = (30, 41, 59)  # slate-800 mais escuro para contraste premium

    img = Image.new("RGB", (width, height), secondary)
    draw = ImageDraw.Draw(img)

    # Gradiente de fundo mais sofisticado (topo mais claro)
    for y in range(height):
        ratio = y / height
        r = int(secondary[0] * (1 - ratio * 0.15) + primary[0] * ratio * 0.08)
        g = int(secondary[1] * (1 - ratio * 0.15) + primary[1] * ratio * 0.08)
        b = int(secondary[2] * (1 - ratio * 0.15) + primary[2] * ratio * 0.08)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Borda superior elegante + linha de destaque
    draw.rectangle([(0, 0), (width, 6)], fill=accent)
    draw.rectangle([(20, 6), (width-20, 7)], fill=primary)

    # Header do programa
    title = settings.get("card_title", "Parabéns! Você ganhou pontos!")
    subtitle = settings.get("card_subtitle", "Programa Parceiro Isopor")
    footer = settings.get("card_footer", "IsoSoluções • Programa de Fidelidade")
    emoji = settings.get("card_emoji", "🎉")

    font_header = _load_font(20, bold=True)
    font_title = _load_font(26, bold=True)
    font_name = _load_font(32, bold=True)
    font_big = _load_font(68, bold=True)
    font_label = _load_font(15)
    font_value = _load_font(18, bold=True)
    font_progress = _load_font(16, bold=True)
    font_small = _load_font(13)
    font_footer = _load_font(12)

    first_name = client_name.split()[0] if client_name else "Parceiro"

    # === HEADER ===
    y = 22
    draw.text((width // 2, y), f"{subtitle}  •  {emoji}", font=font_header, fill=muted, anchor="mt")
    y += 32
    draw.text((width // 2, y), title, font=font_title, fill=text_color, anchor="mt")
    y += 42

    # Nome do cliente
    draw.text((width // 2, y), f"Olá, {first_name}!", font=font_name, fill=text_color, anchor="mt")
    y += 52

    # === PONTOS GANHOS (grande e impactante) ===
    draw.text((width // 2, y), f"+{points_earned}", font=font_big, fill=accent, anchor="mt")
    y += 58
    draw.text((width // 2, y), "PONTOS CONQUISTADOS NESTA COMPRA", font=font_label, fill=muted, anchor="mt")
    y += 26
    draw.text((width // 2, y), f"Compra de {format_currency(amount)}", font=font_small, fill=muted, anchor="mt")
    y += 42

    # === SALDO CUMULATIVO (caixa elegante) ===
    show_balance = settings.get("card_show_balance", "true").lower() == "true"
    if show_balance:
        previous = max(0, current_points - points_earned)

        # Caixa de fundo do saldo
        box_y = y
        box_height = 78
        draw.rounded_rectangle(
            [(40, box_y), (width-40, box_y + box_height)],
            radius=12,
            fill=card_bg,
            outline=accent,
            width=2
        )

        # Três colunas dentro da caixa
        col_width = (width - 100) // 3
        centers = [70 + col_width//2, 50 + col_width + col_width//2, 30 + 2*col_width + col_width//2]

        # Coluna 1 - Anterior
        draw.text((centers[0], box_y + 18), "SALDO ANTERIOR", font=font_small, fill=muted, anchor="mt")
        draw.text((centers[0], box_y + 42), f"{previous}", font=font_value, fill=text_color, anchor="mt")

        # Seta
        draw.text((centers[1]-30, box_y + 38), "→", font=font_value, fill=accent, anchor="mt")

        # Coluna 2 - Ganhou
        draw.text((centers[1], box_y + 18), "+ GANHOU AGORA", font=font_small, fill=muted, anchor="mt")
        draw.text((centers[1], box_y + 42), f"+{points_earned}", font=font_value, fill=accent, anchor="mt")

        # Coluna 3 - Total
        draw.text((centers[2], box_y + 18), "TOTAL ATUAL", font=font_small, fill=muted, anchor="mt")
        draw.text((centers[2], box_y + 42), f"{current_points} pts", font=font_value, fill=accent, anchor="mt")

        y = box_y + box_height + 28

    # === PROGRESSO PARA CAFETEIRA (meta única: 500 pacotes) ===
    bar_width = width - 100
    bar_x = 50
    bar_y = y
    bar_height = 22

    mile = get_milestone_progress(total_packages_bought, 500)

    # Fundo da barra
    draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)], radius=10, fill=(51, 65, 85))

    # Preenchimento
    fill_w = int(bar_width * (mile["percent"] / 100))
    if fill_w > 0:
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + fill_w, bar_y + bar_height)], radius=10, fill=accent)

    y = bar_y + bar_height + 8
    if mile["reached"]:
        cafe_msg = "🏆 Cafeteira conquistada! Parabéns!"
        msg_fill = accent
    else:
        cafe_msg = f"Faltam {mile['remaining']} pacotes para a Cafeteira (meta 500)"
        msg_fill = text_color
    draw.text((width // 2, y), cafe_msg, font=font_progress, fill=msg_fill, anchor="mt")
    y += 24

    # Rodapé premium
    y = height - 52
    draw.rectangle([(0, y-6), (width, y-5)], fill=accent)
    footer_lines = _wrap_text(draw, footer, font_footer, width - 120)
    fy = y
    for line in footer_lines:
        draw.text((width // 2, fy), line, font=font_footer, fill=muted, anchor="mt")
        fy += 15

    buffer = BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer