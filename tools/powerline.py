# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools"]
# ///
"""Draw the Powerline separators into a pixel font, in place, one pixel at a time.

A fallback font can't stand in for them: foot puts its glyphs on the pixel
font's baseline, and these faces put that baseline anywhere from 10 to 12 pixels
down a 16 pixel cell, so a borrowed arrow comes out clipped at one end and
short at the other. Drawn here they fill the cell exactly.

usage: uv run --script powerline.py FONT.ttf...
"""

import io
import math
import os
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

# Each shape gets the centre of a pixel: x from 0 at the left edge to 1 at the
# right, y from 0 at the bottom to 1 at the top. Lines take one pixel per row.
Fill = Callable[[float, float], bool]


def _arrow(x: float, y: float) -> bool:
    return abs(y - 0.5) * 2 <= 1 - x


def _round(x: float, y: float) -> bool:
    return x * x + (y * 2 - 1) ** 2 <= 1


def _mirror(fill: Fill) -> Fill:
    return lambda x, y: fill(1 - x, y)


FILLS: dict[int, Fill] = {
    0xE0B0: _arrow,
    0xE0B2: _mirror(_arrow),
    0xE0B4: _round,
    0xE0B6: _mirror(_round),
    0xE0B8: lambda x, y: x + y <= 1,
    0xE0BA: lambda x, y: x >= y,
    0xE0BC: lambda x, y: x <= y,
    0xE0BE: lambda x, y: x + y >= 1,
}

# For each line, where it crosses a row, as a fraction of the cell width.
LINES: dict[int, Callable[[float], float]] = {
    0xE0B1: lambda y: 1 - abs(y - 0.5) * 2,
    0xE0B3: lambda y: abs(y - 0.5) * 2,
    0xE0B5: lambda y: math.sqrt(max(0.0, 1 - (y * 2 - 1) ** 2)),
    0xE0B7: lambda y: 1 - math.sqrt(max(0.0, 1 - (y * 2 - 1) ** 2)),
    0xE0B9: lambda y: 1 - y,
    0xE0BB: lambda y: y,
    0xE0BD: lambda y: y,
    0xE0BF: lambda y: 1 - y,
}


def _runs(cols: int, rows: int, lit: Callable[[int, int], bool]):
    for row in range(rows):
        col = 0
        while col < cols:
            if not lit(col, row):
                col += 1
                continue
            start = col
            while col < cols and lit(col, row):
                col += 1
            yield row, start, col


def _glyph(cols: int, rows: int, pixel: int, bottom: int, lit: Callable[[int, int], bool]):
    pen = TTGlyphPen(None)
    for row, start, end in _runs(cols, rows, lit):
        y0, y1 = bottom + row * pixel, bottom + (row + 1) * pixel
        x0, x1 = start * pixel, end * pixel
        pen.moveTo((x0, y0))
        pen.lineTo((x0, y1))
        pen.lineTo((x1, y1))
        pen.lineTo((x1, y0))
        pen.closePath()
    return pen.glyph()


def powerline(path: str) -> None:
    font = TTFont(path, recalcTimestamp=False)
    advance = font["hmtx"]["A"][0]
    pixel = advance // 8
    bottom = font["hhea"].descent
    cols, rows = 8, (font["hhea"].ascent - bottom) // pixel

    def centre(col: int, row: int) -> tuple[float, float]:
        return (col + 0.5) / cols, (row + 0.5) / rows

    shapes = {cp: (lambda c, r, f=fill: f(*centre(c, r))) for cp, fill in FILLS.items()}
    for cp, line in LINES.items():
        shapes[cp] = lambda c, r, f=line: c == min(cols - 1, int(f(centre(c, r)[1]) * cols))

    order = font.getGlyphOrder()
    for cp, lit in shapes.items():
        name = f"uni{cp:04X}"
        if name not in order:
            order.append(name)
        glyph = _glyph(cols, rows, pixel, bottom, lit)
        glyph.recalcBounds(font["glyf"])
        font["glyf"][name] = glyph
        font["hmtx"][name] = (advance, glyph.xMin)
        for table in font["cmap"].tables:
            if table.isUnicode():
                table.cmap[cp] = name
    font.setGlyphOrder(order)
    out = io.BytesIO()
    font.save(out)
    _replace_without_touching_mapped_copies(Path(path), out.getvalue())


def _replace_without_touching_mapped_copies(target: Path, data: bytes) -> None:
    if target.read_bytes() == data:
        return
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.chmod(tmp, target.stat().st_mode & 0o777)
    os.replace(tmp, target)


if __name__ == "__main__":
    for path in sys.argv[1:]:
        powerline(path)
