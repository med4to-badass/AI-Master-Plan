"""
notification_card.py
Gera cartão de fidelidade (PNG) sobrepondo dados dinâmicos no card_template.png.
"""

from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from calculations import format_currency, get_milestone_progress

TEMPLATE_PATH = Path(__file__).parent / "card_template.png"

# Coordenadas fixas do template (848x1264)
RECT_TOP  = 514
RECT_BOT  = 1052
RECT_LEFT = 51
RECT_RIGHT= 797
BAR_Y     = 960
BAR_X1    = 75
BAR_X2    = 773
BAR_H     = 22
CX        = 424   # centro horizontal


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


def _glow(img: Image.Image, pos, text: str, font,
          text_color, glow_color, radius: int = 12, anchor: str = "mt") -> Image.Image:
    """Texto com efeito neon via GaussianBlur em camadas RGBA."""
    for r, alpha in [(radius, 220), (max(1, radius // 2), 160)]:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).text(pos, text, font=font,
                                   fill=(*glow_color[:3], alpha), anchor=anchor)
        layer = layer.filter(ImageFilter.GaussianBlur(radius=r))
        img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")

    ImageDraw.Draw(img).text(pos, text, font=font, fill=text_color, anchor=anchor)
    return img


def _txt(draw: ImageDraw.ImageDraw, pos, text: str, font, fill, anchor: str = "mt"):
    draw.text(pos, text, font=font, fill=fill, anchor=anchor)


def _progress_bar(draw: ImageDraw.ImageDraw, pct: float, bg_color):
    """Desenha barra de progresso dinâmica cobrindo a estática do template."""
    draw.rectangle([(BAR_X1 - 5, BAR_Y - 8), (BAR_X2 + 5, BAR_Y + BAR_H + 10)],
                   fill=bg_color)
    teal = (0, 220, 210)
    bar_w = BAR_X2 - BAR_X1
    fill_w = int(bar_w * min(1.0, pct))
    draw.rounded_rectangle([(BAR_X1, BAR_Y), (BAR_X2, BAR_Y + BAR_H)],
                            radius=10, fill=(40, 55, 70))
    if fill_w > 0:
        draw.rounded_rectangle([(BAR_X1, BAR_Y), (BAR_X1 + fill_w, BAR_Y + BAR_H)],
                                radius=10, fill=teal)
    label_font = _load_font(13, bold=True)
    draw.text(((BAR_X1 + BAR_X2) // 2, BAR_Y + BAR_H // 2),
              f"{int(pct * 100)}%", font=label_font,
              fill=(240, 245, 250), anchor="mm")


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
    """Gera PNG do cartão de fidelidade usando card_template.png como base."""
    settings = settings or {}

    img = Image.open(TEMPLATE_PATH).convert("RGB")
    bg_color = img.getpixel((10, 460))

    teal  = (0, 220, 210)
    white = (240, 245, 250)
    muted = (150, 170, 190)

    first_name = client_name.split()[0] if client_name else "Parceiro"
    content_cx = (RECT_LEFT + RECT_RIGHT) // 2
    pkg_info = get_milestone_progress(current_points)
    is_milestone = pkg_info["reached"]

    if is_milestone:
        # ── CARTÃO DE RECOMPENSA 500 PONTOS ──────────────────────────────────
        y = RECT_TOP + 40

        font_congrats = _load_font(36, bold=True)
        img = _glow(img, (content_cx, y), f"Parabéns, {first_name}!",
                    font_congrats, white, teal, radius=8)
        y += 65

        draw = ImageDraw.Draw(img)
        font_sub = _load_font(20, bold=True)
        _txt(draw, (content_cx, y), "VOCÊ ATINGIU O MARCO DE", font_sub, teal)
        y += 34

        font_big = _load_font(72, bold=True)
        img = _glow(img, (content_cx, y), "500 PACOTES",
                    font_big, teal, teal, radius=16)
        y += 84

        draw = ImageDraw.Draw(img)
        font_reward_label = _load_font(20)
        _txt(draw, (content_cx, y), "Recompensa pela sua fidelidade:", font_reward_label, white)
        y += 34

        font_reward = _load_font(44, bold=True)
        img = _glow(img, (content_cx, y), "CAFETEIRA",
                    font_reward, teal, teal, radius=12)
        y += 60

        draw = ImageDraw.Draw(img)
        _progress_bar(draw, 1.0, bg_color)

        font_footer = _load_font(15)
        _txt(draw, (content_cx, BAR_Y + BAR_H + 14),
             "Seu brinde está separado. Qualquer dúvida, é só chamar!",
             font_footer, muted)

    else:
        # ── CARTÃO DE COMPRA PADRÃO ───────────────────────────────────────────
        y = RECT_TOP + 32

        title = settings.get("card_title", "Parabéns! Você ganhou pontos!")
        font_title = _load_font(26, bold=True)
        img = _glow(img, (content_cx, y), title,
                    font_title, white, teal, radius=6)
        y += 60

        font_big = _load_font(66, bold=True)
        img = _glow(img, (content_cx, y), f"+{points_earned} PONTOS GANHOS",
                    font_big, teal, teal, radius=14)
        y += 80

        draw = ImageDraw.Draw(img)
        font_info = _load_font(20)
        _txt(draw, (content_cx, y),
             f"Compra: {format_currency(amount)}  |  Saldo atual: {current_points} pts",
             font_info, white)
        y += 34

        remaining = points_to_next_package if points_to_next_package > 0 else pkg_info["remaining"]
        font_faltam = _load_font(18)
        _txt(draw, (content_cx, y),
             f"Faltam {remaining} pontos para ganhar a cafeteira",
             font_faltam, muted)

        pct = min(1.0, current_points / 500.0)
        _progress_bar(draw, pct, bg_color)

    buffer = BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer
