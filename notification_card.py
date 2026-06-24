"""
notification_card.py
Gera cartão de fidelidade (PNG) sobrepondo dados dinâmicos no card_template.png.
Design baseado no template com estilo neon vermelho/teal.
"""

from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from calculations import format_currency, get_milestone_progress

TEMPLATE_PATH = Path(__file__).parent / "card_template.png"

# Coordenadas do template (848x1264)
RECT_TOP = 514       # topo da borda vermelha
RECT_BOT = 1052      # fundo da borda vermelha
RECT_LEFT = 51       # borda esquerda
RECT_RIGHT = 797     # borda direita
LOGO_TOP = 40        # início do logo
LOGO_BOT = 430       # fim do logo (IsoSoluções text)
BAR_Y = 960          # posição da barra de progresso
BAR_X1 = 75
BAR_X2 = 773
BAR_H = 22
CX = 424             # centro horizontal


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _glow_text(img: Image.Image, pos, text: str, font,
               text_color, glow_color, radius: int = 12, anchor: str = "mt") -> Image.Image:
    """Renderiza texto com efeito neon (glow via blur + texto nítido por cima)."""
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.text(pos, text, font=font, fill=(*glow_color[:3], 230), anchor=anchor)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=radius))

    glow2 = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd2 = ImageDraw.Draw(glow2)
    gd2.text(pos, text, font=font, fill=(*glow_color[:3], 180), anchor=anchor)
    glow2 = glow2.filter(ImageFilter.GaussianBlur(radius=max(1, radius // 2)))

    base = img.convert("RGBA")
    base = Image.alpha_composite(base, glow)
    base = Image.alpha_composite(base, glow2)

    sharp = ImageDraw.Draw(base)
    sharp.text(pos, text, font=font, fill=text_color, anchor=anchor)

    return base.convert("RGB")


def _plain_text(draw: ImageDraw.ImageDraw, pos, text: str, font, fill, anchor: str = "mt"):
    draw.text(pos, text, font=font, fill=fill, anchor=anchor)


def generate_points_card(
    client_name: str,
    points_earned: int,
    current_points: int,
    amount: float,
    settings: Optional[Dict[str, Any]] = None,
    available_packages: int = 0,
    points_to_next_package: int = 0,
    total_packages_bought: int = 0,
    milestone_remaining: int = 0,
) -> BytesIO:
    """Gera PNG do cartão de fidelidade usando o template visual da IsoSoluções."""
    settings = settings or {}

    img = Image.open(TEMPLATE_PATH).convert("RGB")
    w, h = img.size  # 848 x 1264

    # ── ENCOLHE O LOGO ───────────────────────────────────────────────────────
    logo_h = LOGO_BOT - LOGO_TOP  # 390 px
    logo_region = img.crop((0, LOGO_TOP, w, LOGO_BOT))
    new_logo_h = int(logo_h * 0.75)   # ~292 px
    logo_small = logo_region.resize((w, new_logo_h), Image.LANCZOS)

    bg_color = img.getpixel((10, 460))  # cor de fundo no gap entre logo e retângulo

    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, LOGO_TOP), (w, LOGO_BOT)], fill=bg_color)
    img.paste(logo_small, (0, LOGO_TOP))

    logo_end = LOGO_TOP + new_logo_h   # ~332

    # ── TITULO "CARTÃO FIDELIDADE" ────────────────────────────────────────────
    font_titulo = _load_font(50, bold=True)
    title_y = logo_end + 14
    img = _glow_text(img, (CX, title_y), "CARTÃO FIDELIDADE",
                     font_titulo, text_color=(255, 255, 255),
                     glow_color=(0, 210, 200), radius=14)

    # ── CONTEÚDO DENTRO DO RETÂNGULO VERMELHO ────────────────────────────────
    draw = ImageDraw.Draw(img)

    teal  = (0, 220, 210)
    red   = (255, 50, 50)
    white = (240, 245, 250)
    muted = (150, 170, 190)

    first_name = client_name.split()[0] if client_name else "Parceiro"
    content_cx = (RECT_LEFT + RECT_RIGHT) // 2   # 424
    y = RECT_TOP + 35

    # Nome do cliente
    font_name = _load_font(36, bold=True)
    img = _glow_text(img, (content_cx, y), f"Olá, {first_name}!",
                     font_name, white, teal, radius=8)
    y += 52

    # +X PONTOS (neon vermelho, estilo "COMPROU = GANHOU")
    draw = ImageDraw.Draw(img)
    font_big = _load_font(74, bold=True)
    img = _glow_text(img, (content_cx, y), f"+{points_earned} PONTOS",
                     font_big, red, red, radius=16)
    y += 86

    draw = ImageDraw.Draw(img)
    font_sub = _load_font(17)
    _plain_text(draw, (content_cx, y), f"Compra: {format_currency(amount)}", font_sub, muted)
    y += 34

    # Separador
    draw.line([(RECT_LEFT + 30, y), (RECT_RIGHT - 30, y)], fill=(70, 90, 110), width=1)
    y += 18

    # Saldo: anterior → ganhou → total
    previous = max(0, current_points - points_earned)
    col_w = (RECT_RIGHT - RECT_LEFT - 60) // 3
    col1 = RECT_LEFT + 30 + col_w // 2
    col2 = content_cx
    col3 = RECT_RIGHT - 30 - col_w // 2

    font_lbl = _load_font(14)
    font_val = _load_font(20, bold=True)

    _plain_text(draw, (col1, y), "ANTERIOR", font_lbl, muted)
    _plain_text(draw, (col2, y), "+ GANHOU", font_lbl, muted)
    _plain_text(draw, (col3, y), "TOTAL", font_lbl, muted)
    y += 22
    _plain_text(draw, (col1, y), str(previous), font_val, white)
    _plain_text(draw, (col2, y), f"+{points_earned}", font_val, teal)
    _plain_text(draw, (col3, y), f"{current_points} pts", font_val, teal)
    y += 42

    # Separador
    draw.line([(RECT_LEFT + 30, y), (RECT_RIGHT - 30, y)], fill=(70, 90, 110), width=1)
    y += 18

    # Status de progresso (estilo "QUASE LA" do Design.png)
    pkg_info = get_milestone_progress(current_points)
    remaining = points_to_next_package if points_to_next_package > 0 else pkg_info["remaining"]

    if pkg_info["reached"]:
        status_txt = "META ATINGIDA!"
        status_color = red
    elif remaining <= 50:
        status_txt = "QUASE LÁ!"
        status_color = teal
    else:
        status_txt = f"FALTAM {remaining} PONTOS"
        status_color = white

    font_status = _load_font(34, bold=True)
    img = _glow_text(img, (content_cx, y), status_txt,
                     font_status, status_color, status_color, radius=12)
    y += 48

    draw = ImageDraw.Draw(img)
    font_prog = _load_font(16)
    _plain_text(draw, (content_cx, y),
                f"para a Cafeteira  •  {current_points} / 500 pontos",
                font_prog, muted)

    # ── BARRA DE PROGRESSO DINÂMICA ──────────────────────────────────────────
    draw.rectangle([(BAR_X1 - 5, BAR_Y - 8), (BAR_X2 + 5, BAR_Y + BAR_H + 10)],
                   fill=bg_color)

    bar_w = BAR_X2 - BAR_X1
    pct = min(1.0, current_points / 500.0)
    fill_w = int(bar_w * pct)

    draw.rounded_rectangle([(BAR_X1, BAR_Y), (BAR_X2, BAR_Y + BAR_H)],
                            radius=10, fill=(40, 55, 70))
    if fill_w > 0:
        draw.rounded_rectangle([(BAR_X1, BAR_Y), (BAR_X1 + fill_w, BAR_Y + BAR_H)],
                                radius=10, fill=teal)

    font_bar = _load_font(13, bold=True)
    bar_cx = (BAR_X1 + BAR_X2) // 2
    bar_cy = BAR_Y + BAR_H // 2
    draw.text((bar_cx, bar_cy), f"{int(pct*100)}%", font=font_bar, fill=white, anchor="mm")

    buffer = BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer
