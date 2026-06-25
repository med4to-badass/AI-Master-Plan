"""
notification_card.py
Gera o cartão de fidelidade (PNG) renderizando os dados dinâmicos
diretamente sobre o card_template.png (logo, moldura vermelha, cafeteira).
Os dados e a barra de progresso são personalizados a cada compra.
"""

from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from calculations import format_currency, get_milestone_progress

BASE_DIR = Path(__file__).parent
CARD_TEMPLATE = BASE_DIR / "card_template.png"

# ── Geometria do template (848 x 1264) ───────────────────────────────────────
RECT_TOP    = 516
RECT_BOTTOM = 1051
RECT_LEFT   = 51
RECT_RIGHT  = 797
CX          = (RECT_LEFT + RECT_RIGHT) // 2   # 424

# Barra de progresso (cobre a barra decorativa do template)
BAR_X1  = 90
BAR_X2  = 760
BAR_TOP = 990
BAR_BOT = 1021

# Cores
TEAL  = (0, 224, 214)
NEON_RED = (255, 45, 55)
WHITE = (240, 245, 250)
MUTED = (150, 170, 190)
BG    = (32, 40, 47)
TRACK = (44, 58, 72)

MILESTONE_TARGET = 500


# ── Fontes ────────────────────────────────────────────────────────────────────
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


# ── Efeito neon (glow) ────────────────────────────────────────────────────────
def _glow(img: Image.Image, pos, text: str, font, text_color, glow_color,
          radius: int = 12, anchor: str = "mm") -> Image.Image:
    for r, alpha in [(radius, 210), (max(1, radius // 2), 150)]:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).text(pos, text, font=font,
                                   fill=(*glow_color[:3], alpha), anchor=anchor)
        layer = layer.filter(ImageFilter.GaussianBlur(radius=r))
        img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    ImageDraw.Draw(img).text(pos, text, font=font, fill=text_color, anchor=anchor)
    return img


def _tracked_text(draw: ImageDraw.ImageDraw, cx: int, cy: int, text: str,
                  font, fill, spacing: int = 6):
    """Texto centrado (horizontal e vertical) com espaçamento entre letras."""
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        draw.text((x, cy), ch, font=font, fill=fill, anchor="lm")
        x += w + spacing


# ── Pílula de informação (rótulo + valor) ─────────────────────────────────────
def _info_pill(img: Image.Image, cx: int, top: int, w: int, h: int,
               label: str, value: str) -> Image.Image:
    draw = ImageDraw.Draw(img)
    left, right = cx - w // 2, cx + w // 2
    draw.rounded_rectangle([(left, top), (right, top + h)], radius=14,
                           fill=(38, 49, 60), outline=(70, 88, 104), width=1)
    draw.text((cx, top + 18), label, font=_load_font(15, bold=True),
              fill=TEAL, anchor="mm")
    draw.text((cx, top + h - 24), value, font=_load_font(24, bold=True),
              fill=WHITE, anchor="mm")
    return img


# ── Barra de progresso personalizada ──────────────────────────────────────────
def _progress_bar(img: Image.Image, pct: float) -> Image.Image:
    pct = max(0.0, min(1.0, pct))
    draw = ImageDraw.Draw(img)
    # Cobre a barra decorativa do template
    draw.rectangle([(RECT_LEFT + 6, BAR_TOP - 8), (RECT_RIGHT - 6, BAR_BOT + 8)], fill=BG)

    # Trilho
    radius = (BAR_BOT - BAR_TOP) // 2
    draw.rounded_rectangle([(BAR_X1, BAR_TOP), (BAR_X2, BAR_BOT)],
                           radius=radius, fill=TRACK)
    # Preenchimento com glow
    fill_w = int((BAR_X2 - BAR_X1) * pct)
    if fill_w > 6:
        glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle(
            [(BAR_X1, BAR_TOP), (BAR_X1 + fill_w, BAR_BOT)],
            radius=radius, fill=(*TEAL, 180))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=6))
        img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(BAR_X1, BAR_TOP), (BAR_X1 + fill_w, BAR_BOT)],
                               radius=radius, fill=TEAL)
    return img


def _draw_brand_title(img: Image.Image) -> Image.Image:
    """Desenha 'Cartão' (vermelho neon) + 'Fidelidade' (teal neon) abaixo do logo."""
    font = _load_font(46, bold=True)
    draw = ImageDraw.Draw(img)
    gap = draw.textlength(" ", font=font)
    w1 = draw.textlength("Cartão", font=font)
    w2 = draw.textlength("Fidelidade", font=font)
    total = w1 + gap + w2
    x0 = CX - total / 2
    y = 462
    img = _glow(img, (x0, y), "Cartão", font, NEON_RED, NEON_RED, radius=10, anchor="lm")
    img = _glow(img, (x0 + w1 + gap, y), "Fidelidade", font, TEAL, TEAL, radius=10, anchor="lm")
    return img


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
    settings = settings or {}
    first_name = client_name.split()[0] if client_name else "Parceiro"
    pkg_info = get_milestone_progress(current_points)
    is_milestone = pkg_info["reached"]

    img = Image.open(CARD_TEMPLATE).convert("RGB")
    img = _draw_brand_title(img)

    if is_milestone:
        # ── CARTÃO MILESTONE (500 pontos atingidos) ──────────────────────────
        img = _glow(img, (CX, 580), f"Parabéns, {first_name}!",
                    _load_font(36, bold=True), WHITE, TEAL, radius=8)
        draw = ImageDraw.Draw(img)
        _tracked_text(draw, CX, 638, "VOCÊ ATINGIU O MARCO DE",
                      _load_font(20, bold=True), TEAL, spacing=4)

        img = _glow(img, (CX, 730), f"{MILESTONE_TARGET} PONTOS",
                    _load_font(82, bold=True), TEAL, TEAL, radius=16)
        draw = ImageDraw.Draw(img)
        draw.text((CX, 818), "Sua recompensa pela fidelidade:",
                  font=_load_font(20), fill=MUTED, anchor="mm")

        img = _glow(img, (CX, 884), "CAFETEIRA",
                    _load_font(54, bold=True), WHITE, TEAL, radius=12)
        draw = ImageDraw.Draw(img)
        draw.text((CX, 952), "Seu brinde já está separado. É só retirar!",
                  font=_load_font(18), fill=MUTED, anchor="mm")

        img = _progress_bar(img, 1.0)

    else:
        # ── CARTÃO DE COMPRA ─────────────────────────────────────────────────
        draw = ImageDraw.Draw(img)
        draw.text((CX, 562), first_name, font=_load_font(30, bold=True),
                  fill=WHITE, anchor="mm")
        _tracked_text(draw, CX, 602, "VOCÊ GANHOU",
                      _load_font(20, bold=True), TEAL, spacing=5)

        img = _glow(img, (CX, 700), f"+{points_earned}",
                    _load_font(128, bold=True), TEAL, TEAL, radius=18)
        draw = ImageDraw.Draw(img)
        pts_word = "PONTO" if points_earned == 1 else "PONTOS"
        _tracked_text(draw, CX, 782, pts_word,
                      _load_font(26, bold=True), WHITE, spacing=8)

        # Pílulas: Compra | Saldo atual
        img = _info_pill(img, CX - 160, 838, 290, 76, "COMPRA",
                         format_currency(amount))
        img = _info_pill(img, CX + 160, 838, 290, 76, "SALDO ATUAL",
                         f"{current_points} pts")
        draw = ImageDraw.Draw(img)

        # Faltam X para a cafeteira
        remaining = points_to_next_package if points_to_next_package > 0 else pkg_info["remaining"]
        draw.text((CX, 952), f"Faltam {remaining} pontos para a Cafeteira",
                  font=_load_font(19), fill=MUTED, anchor="mm")

        # Barra de progresso real
        pct = current_points / float(MILESTONE_TARGET)
        img = _progress_bar(img, pct)

    buffer = BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer
