"""Generate the application logo ("pixel brightening", option D).

A 4×4 grid of rounded pixels on a dark tile brightens from the bottom-left
(dark) to the top-right (white), echoing the landing-page pixel conversion.
One geometry definition produces every file so the SVG and PNGs never drift:

    frontend/public/favicon.svg           vector logo (favicon and header)
    frontend/public/apple-touch-icon.png  180 px, iOS home screen
    frontend/public/icon-192.png          192 px
    frontend/public/icon-512.png          512 px

Run from the repository root:

    python scripts/build_logo.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUTPUT = Path(__file__).resolve().parents[1] / "frontend" / "public"

VIEWBOX = 64
TILE_RADIUS = 14
TILE_COLOR = "#0f1115"
# Dark → bright ramp; the step index is the pixel's diagonal distance from the dark corner.
RAMP = ["#1b1f2a", "#23365e", "#1f4fa8", "#0b57d0", "#4f86e8", "#a6c4f6", "#ffffff"]
GRID = 4
ORIGIN = 10.0
PITCH = 11.5
PIXEL = 9.5
PIXEL_RADIUS = 2.0


def pixels() -> list[tuple[float, float, str]]:
    """(x, y, colour) of every grid pixel; row 0 is the top row."""
    cells = []
    for row in range(GRID):
        for col in range(GRID):
            step = col + (GRID - 1 - row)
            cells.append((ORIGIN + col * PITCH, ORIGIN + row * PITCH, RAMP[step]))
    return cells


def build_svg() -> str:
    rects = "".join(
        f'<rect x="{x:g}" y="{y:g}" width="{PIXEL:g}" height="{PIXEL:g}" rx="{PIXEL_RADIUS:g}" fill="{color}"/>'
        for x, y, color in pixels()
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEWBOX} {VIEWBOX}">'
        f'<rect width="{VIEWBOX}" height="{VIEWBOX}" rx="{TILE_RADIUS}" fill="{TILE_COLOR}"/>'
        f"{rects}</svg>\n"
    )


def build_png(size: int, rounded_tile: bool = True) -> Image.Image:
    """Rasterise at 4× and downsample so edges are anti-aliased."""
    scale = size * 4 / VIEWBOX
    canvas = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    box = (0, 0, size * 4 - 1, size * 4 - 1)
    if rounded_tile:
        draw.rounded_rectangle(box, radius=TILE_RADIUS * scale, fill=TILE_COLOR)
    else:
        # iOS masks the icon itself, so the touch icon is a full square.
        draw.rectangle(box, fill=TILE_COLOR)
    for x, y, color in pixels():
        draw.rounded_rectangle(
            (x * scale, y * scale, (x + PIXEL) * scale, (y + PIXEL) * scale),
            radius=PIXEL_RADIUS * scale,
            fill=color,
        )
    return canvas.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "favicon.svg").write_text(build_svg(), encoding="utf-8")
    build_png(180, rounded_tile=False).save(OUTPUT / "apple-touch-icon.png", optimize=True)
    build_png(192).save(OUTPUT / "icon-192.png", optimize=True)
    build_png(512).save(OUTPUT / "icon-512.png", optimize=True)
    for name in ("favicon.svg", "apple-touch-icon.png", "icon-192.png", "icon-512.png"):
        print(f"{name}: {(OUTPUT / name).stat().st_size} bytes")


if __name__ == "__main__":
    main()
