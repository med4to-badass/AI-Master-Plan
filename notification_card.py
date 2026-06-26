"""
notification_card.py
Gera o cartão de fidelidade (PNG) no estilo "Corporate" (linhas estruturadas):
mantém o cabeçalho/logo do card_template.png intacto e redesenha a área de
conteúdo abaixo com painel organizado, dados em linhas e barra de progresso real.
"""

from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from calculations import format_currency, get_milestone_progress

BASE_DIR = Path(__file__).parent
CARD_TEMPLATE = BASE_DIR / "card_template.png"

# ── Geometria (848 x 1264) ────────────────────────────────────────────────────
W, H = 848, 1264
HEADER_H = 455          # tudo acima fica = template (logo intacta)
CX = W // 2             # 424

# Painel de conteúdo
PANEL_X1, PANEL_X2 = 55, W - 55
PANEL_TOP, PANEL_BOT = 510, 1180
HEADER_BAR_BOT = 575

# Barra de progresso
BAR_X1, BAR_X2 = 95, W - 95
BAR_TOP, BAR_BOT = 1058, 1086

# Cores
TEAL  = (0, 224, 214)
TEAL_DARK = (0, 120, 116)
NEON_RED = (255, 45, 55)
WHITE = (240, 245, 250)
MUTED = (150, 168, 188)
PANEL_FILL = (26, 34, 43)
PANEL_LINE = (52, 68, 82)
ROW_LINE = (44, 58, 70)
TRACK = (40, 52, 64)

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


# ── Base: header do template + gradiente contínuo abaixo ──────────────────────
def _base_canvas(top=(44, 54, 63), bottom=(20, 26, 33)) -> Image.Image:
    tpl = Image.open(CARD_TEMPLATE).convert("RGB")
    grad = Image.new("RGB", (1, H))
    for y in range(H):
        if y < HEADER_H:
            grad.putpixel((0, y), top)
        else:
            t = ((y - HEADER_H) / (H - HEADER_H)) ** 0.9
            grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    img = grad.resize((W, H)).convert("RGB")
    img.paste(tpl.crop((0, 0, W, HEADER_H)), (0, 0))   # logo intacta
    return img


# ── Painel corporate com cabeçalho teal ───────────────────────────────────────
def _draw_panel(img: Image.Image, first_name: str) -> Image.Image:
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([PANEL_X1, PANEL_TOP, PANEL_X2, PANEL_BOT],
                           radius=18, fill=PANEL_FILL, outline=PANEL_LINE, width=1)
    # cabeçalho teal (cantos superiores arredondados)
    draw.rounded_rectangle([PANEL_X1, PANEL_TOP, PANEL_X2, HEADER_BAR_BOT],
                           radius=18, fill=TEAL_DARK)
    draw.rectangle([PANEL_X1, HEADER_BAR_BOT - 18, PANEL_X2, HEADER_BAR_BOT], fill=TEAL_DARK)
    draw.text((PANEL_X1 + 30, (PANEL_TOP + HEADER_BAR_BOT) // 2),
              "CARTÃO FIDELIDADE", font=_load_font(18, bold=True), fill=WHITE, anchor="lm")
    draw.text((PANEL_X2 - 30, (PANEL_TOP + HEADER_BAR_BOT) // 2),
              first_name, font=_load_font(18, bold=True), fill=WHITE, anchor="rm")
    return img


def _seg_bar(img: Image.Image, pct: float, color=TEAL) -> Image.Image:
    pct = max(0.0, min(1.0, pct))
    draw = ImageDraw.Draw(img)
    r = (BAR_BOT - BAR_TOP) // 2
    draw.rounded_rectangle([BAR_X1, BAR_TOP, BAR_X2, BAR_BOT], radius=r, fill=TRACK)
    fill_w = int((BAR_X2 - BAR_X1) * pct)
    if fill_w > 6:
        glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle(
            [BAR_X1, BAR_TOP, BAR_X1 + fill_w, BAR_BOT], radius=r, fill=(*color, 150))
        glow = glow.filter(ImageFilter.GaussianBlur(7))
        img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
        ImageDraw.Draw(img).rounded_rectangle(
            [BAR_X1, BAR_TOP, BAR_X1 + fill_w, BAR_BOT], radius=r, fill=color)
    return img


def _rows(img: Image.Image, rows, y0=830, step=52) -> Image.Image:
    draw = ImageDraw.Draw(img)
    y = y0
    for label, value in rows:
        draw.text((PANEL_X1 + 40, y), label, font=_load_font(18), fill=MUTED, anchor="lm")
        draw.text((PANEL_X2 - 40, y), value, font=_load_font(19, bold=True), fill=WHITE, anchor="rm")
        draw.line([PANEL_X1 + 40, y + 22, PANEL_X2 - 40, y + 22], fill=ROW_LINE, width=1)
        y += step
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

    img = _base_canvas()
    img = _draw_panel(img, first_name)

    if is_milestone:
        # ── CARTÃO MARCO (500 pontos) ────────────────────────────────────────
        img = _glow(img, (CX, 690), f"{MILESTONE_TARGET}",
                    _load_font(112, bold=True), TEAL, TEAL, radius=14)
        draw = ImageDraw.Draw(img)
        _tracked_text(draw, CX, 770, "PONTOS — MARCO ATINGIDO",
                      _load_font(18, bold=True), WHITE, spacing=3)

        img = _rows(img, [
            ("Parabéns", first_name),
            ("Saldo atual", f"{current_points} pts"),
            ("Recompensa conquistada", "Cafeteira"),
            ("Status", "Brinde separado ✓"),
        ])
        img = _seg_bar(img, 1.0)
        draw = ImageDraw.Draw(img)
        draw.text((CX, 1140), "☕  Sua recompensa pela fidelidade já está pronta!",
                  font=_load_font(15, bold=True), fill=TEAL, anchor="mm")

    else:
        # ── CARTÃO DE COMPRA ─────────────────────────────────────────────────
        img = _glow(img, (CX, 690), f"+{points_earned}",
                    _load_font(112, bold=True), TEAL, TEAL, radius=14)
        draw = ImageDraw.Draw(img)
        pts_word = "PONTO GANHO" if points_earned == 1 else "PONTOS GANHOS"
        _tracked_text(draw, CX, 768, pts_word, _load_font(20, bold=True), WHITE, spacing=5)

        remaining = points_to_next_package if points_to_next_package > 0 else pkg_info["remaining"]
        img = _rows(img, [
            ("Compra registrada", format_currency(amount)),
            ("Saldo atual", f"{current_points} pts"),
            ("Meta do prêmio", f"{MILESTONE_TARGET} pts"),
            ("Faltam", f"{remaining} pts"),
        ])
        img = _seg_bar(img, current_points / float(MILESTONE_TARGET))
        draw = ImageDraw.Draw(img)
        draw.text((CX, 1140), "☕  Recompensa ao atingir a meta: Cafeteira",
                  font=_load_font(15, bold=True), fill=TEAL, anchor="mm")

    buffer = BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer
