import os
import shutil
import struct
import subprocess
import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from pathlib import Path

from . import palette
from .paths import write_atomic

THEME = "athanor"

SIZES = ((24, 1), (48, 2))

CHUNK_IMAGE = 0xFFFD0002


@dataclass(frozen=True)
class Cursor:
    name: str
    rows: tuple[str, ...]
    hot: tuple[int, int]
    names: tuple[str, ...]


@cache
def cursors() -> dict[str, Cursor]:
    data = tomllib.loads((files("athanor") / "cursors.toml").read_text())
    out = {}
    for name, c in data.items():
        rows = c["art"].strip("\n").split("\n")
        width = max(map(len, rows))
        out[name] = Cursor(
            name, tuple(r.ljust(width) for r in rows), tuple(c["hot"]), tuple(c["names"])
        )
    return out


def theme_dir() -> Path:
    data = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"
    return Path(data) / "icons" / THEME


def _argb(hexcolor: str) -> int:
    return 0xFF000000 | int(hexcolor.lstrip("#"), 16)


def image(rows, ink: str, paper: str, size: int, scale: int) -> list[list[int]]:
    colors = {"#": _argb(ink), ".": _argb(paper)}
    out = [[0] * size for _ in range(size)]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in colors:
                for dy in range(scale):
                    out[y * scale + dy][x * scale : (x + 1) * scale] = [colors[ch]] * scale
    return out


def xcursor(images: list[tuple[int, list[list[int]]]], hot: tuple[int, int] = (0, 0)) -> bytes:
    header = struct.pack("<4sIII", b"Xcur", 16, 0x10000, len(images))
    toc, chunks, pos = b"", b"", 16 + 12 * len(images)
    for nominal, px in images:
        size = len(px)
        scale = size // SIZES[0][0]
        x, y = hot[0] * scale, hot[1] * scale
        toc += struct.pack("<III", CHUNK_IMAGE, nominal, pos)
        chunk = struct.pack("<9I", 36, CHUNK_IMAGE, nominal, 1, size, size, x, y, 0)
        chunk += struct.pack(f"<{size * size}I", *(p for row in px for p in row))
        chunks += chunk
        pos += len(chunk)
    return header + toc + chunks


def render(scheme: palette.Scheme, root: Path | None = None) -> Path:
    root = root or theme_dir()
    ink, paper = scheme.roles["bg"], scheme.roles["fg"]
    out = root / "cursors"
    for c in cursors().values():
        images = [(size, image(c.rows, ink, paper, size, scale)) for size, scale in SIZES]
        write_atomic(out / c.name, xcursor(images, c.hot))
        for alias in c.names:
            link = out / alias
            if not link.is_symlink():
                link.unlink(missing_ok=True)
                link.symlink_to(c.name)
    write_atomic(
        root / "index.theme",
        f"[Icon Theme]\nName={THEME}\nComment=Athanor's cursors, drawn by transmute\n"
        "Inherits=Adwaita\n",
    )
    return root


def show() -> None:
    if os.environ.get("XCURSOR_THEME") != THEME or not shutil.which("hyprctl"):
        return
    size = os.environ.get("XCURSOR_SIZE") or "24"
    # Hyprland caches the theme, so switch away and back to reload it.
    for name in ("Adwaita", THEME):
        subprocess.run(["hyprctl", "setcursor", name, size], capture_output=True, check=False)
