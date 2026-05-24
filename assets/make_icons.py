"""Generate PNG icons for the PWA.

Run once (or whenever the icon design changes) to produce assets/icon-192.png
and assets/icon-512.png. build.py copies them into docs/ on each build.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent

BG = (15, 20, 25)        # --bg
ACCENT = (96, 165, 250)  # --accent
POS = (16, 185, 129)     # --pos
TEXT = (226, 232, 240)   # --text


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)

    # Rounded outer border so the icon reads as a tile on any background.
    pad = size // 14
    radius = size // 6
    d.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=radius,
        outline=(45, 55, 72),
        width=max(2, size // 96),
    )

    # Stylised candlestick / line chart inside.
    # Three candles + a trend arrow.
    cx = size // 2
    cy = size // 2
    inner = size - 4 * pad
    step = inner // 5
    bar_w = max(2, size // 16)

    bars = [
        # (x_offset_from_center, top_y_offset, bottom_y_offset, color)
        (-2 * step, -inner // 6, inner // 5, POS),
        (-step // 2, -inner // 3, inner // 10, POS),
        (step, -inner // 2.2, -inner // 12, POS),
    ]
    # Wicks
    for dx, top, bot, color in bars:
        x = cx + dx
        d.line([(x, cy + top - size // 24), (x, cy + bot + size // 24)],
               fill=color, width=max(1, size // 96))
        d.rectangle(
            [x - bar_w, cy + top, x + bar_w, cy + bot],
            fill=color,
        )

    # Trend arrow rising to top-right
    arr_start = (cx - 2 * step - bar_w, cy + inner // 6)
    arr_end = (cx + 2 * step, cy - inner // 2.5)
    d.line([arr_start, arr_end], fill=ACCENT, width=max(2, size // 48))
    # Arrowhead
    head = size // 12
    ex, ey = arr_end
    d.polygon(
        [(ex, ey), (ex - head, ey + head // 2), (ex - head // 2, ey + head)],
        fill=ACCENT,
    )

    return img


def main() -> None:
    for s in (192, 512):
        img = draw_icon(s)
        out = ASSETS / f"icon-{s}.png"
        img.save(out, "PNG", optimize=True)
        print(f"Wrote {out} ({s}x{s})")


if __name__ == "__main__":
    main()
