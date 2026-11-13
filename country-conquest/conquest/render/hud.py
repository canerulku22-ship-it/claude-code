"""Top-of-screen counters: champion flag + territory count, and the win streak."""
from __future__ import annotations

from PIL import Image

from .camera import ease_out_back
from .flags import flag_card
from .fx import panel, paste
from .text import TextStyle, render_text


def draw_hud(canvas: Image.Image, k: float, x0: float, y0: float, iso2: str, territory_text: str,
             streak_text: str | None, style: TextStyle, panel_rgb: tuple, bump: float = 0.0,
             alpha: float = 1.0, champion_swap: float = 1.0) -> None:
    """Draw the HUD with its top-left corner at reference (x0, y0).

    ``bump`` (0..1, decaying) pops the territory line when the count changes;
    ``champion_swap`` (0..1) animates the flag when a new champion takes over."""
    if alpha <= 0.01:
        return
    h = round(98 * k)
    flag = flag_card(iso2, round(92 * k), shadow=False)
    text = render_text(territory_text, round(50 * k), style)
    w = round(flag.width + text.width + 44 * k)
    bg = panel(w, h, h // 2, panel_rgb + (196,))
    px, py = round(x0 * k), round(y0 * k)
    paste(canvas, bg, px + w / 2, py + h / 2, alpha=alpha)
    s = 1.0 + 0.14 * bump
    fs = ease_out_back(champion_swap) if champion_swap < 1 else 1.0
    paste(canvas, flag, px + 20 * k + flag.width / 2, py + h / 2, scale=max(0.05, fs), alpha=alpha)
    # Grow from the left edge so the bump never covers the flag.
    paste(canvas, text, px + 28 * k + flag.width + text.width * s / 2, py + h / 2 + 2 * k, scale=s, alpha=alpha)

    if streak_text:
        st = render_text(streak_text, round(40 * k), style)
        sh = round(66 * k)
        sw = round(st.width + 22 * k)
        sbg = panel(sw, sh, sh // 2, panel_rgb + (176,))
        sy = py + h + 12 * k
        paste(canvas, sbg, px + sw / 2, sy + sh / 2, alpha=alpha)
        paste(canvas, st, px + sw / 2, sy + sh / 2 + 2 * k, alpha=alpha)
