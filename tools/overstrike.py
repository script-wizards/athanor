# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools"]
# ///
"""Make a bold from a pixel font by drawing each glyph twice, one pixel apart.

usage: uv run --script overstrike.py FONT.ttf OUT.ttf "Family Name"
"""

import sys

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


def overstrike(src: str, out: str, family: str) -> None:
    font = TTFont(src)
    glyf, glyphs = font["glyf"], font.getGlyphSet()
    pixel = font["hmtx"]["A"][0] / 8
    for name in font.getGlyphOrder():
        strokes = DecomposingRecordingPen(glyphs)
        glyphs[name].draw(strokes)
        if not strokes.value:
            continue
        pen = TTGlyphPen(None)
        strokes.replay(pen)
        strokes.replay(TransformPen(pen, (1, 0, 0, 1, pixel, 0)))
        glyf[name] = pen.glyph()

    font["OS/2"].usWeightClass = 700
    font["OS/2"].fsSelection = (font["OS/2"].fsSelection | 0x20) & ~0x40
    font["head"].macStyle |= 1
    names = {1: family, 2: "Bold", 4: f"{family} Bold", 6: family.replace(" ", "") + "-Bold"}
    names |= {16: family, 17: "Bold"}
    for record in font["name"].names:
        if record.nameID in names:
            record.string = names[record.nameID]
    font.save(out)


if __name__ == "__main__":
    overstrike(*sys.argv[1:4])
