import hashlib
import json
import math
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path


class MissingTool(RuntimeError):
    pass


@dataclass(frozen=True)
class Walls:
    levels: tuple[Path, ...]
    lock: Path
    lock_panel_x: int
    scale: int

    @property
    def desk(self) -> Path:
        return self.levels[0]

    def level(self, workspace: int | None) -> Path:
        if not workspace or workspace < 1:
            return self.levels[0]
        return self.levels[(workspace - 1) % len(self.levels)]


def _magick() -> str:
    exe = shutil.which("magick")
    if exe is None:
        raise MissingTool("the plates need ImageMagick 7. pacman -S imagemagick")
    return exe


def _manifest() -> dict:
    return tomllib.loads((files("athanor") / "plates" / "plates.toml").read_text())


def pixel_scale(height: int, configured: int = 0) -> int:
    if configured > 0:
        return configured
    return 3 if height >= 2000 else 2


def _size(path: Path) -> tuple[int, int]:
    out = subprocess.run(
        [_magick(), "identify", "-format", "%w %h", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    w, h = out.stdout.split()
    return int(w), int(h)


def desk_crop(
    plate: tuple[int, int], low: tuple[int, int], focus, anchor
) -> tuple[int, int, int, int]:
    pw, ph = plate
    lw, lh = low
    k = max(lw / pw, lh / ph)
    sw, sh = math.ceil(pw * k), math.ceil(ph * k)
    ox = round(min(max(focus[0] * sw - anchor[0] * lw, 0), sw - lw))
    oy = round(min(max(focus[1] * sh - anchor[1] * lh, 0), sh - lh))
    return sw, sh, ox, oy


def inset_box(size: tuple[int, int], inset) -> tuple[int, int, int, int]:
    pw, ph = size
    left, top, right, bottom = inset or (0, 0, 0, 0)
    w, h = round(pw * (1 - left - right)), round(ph * (1 - top - bottom))
    return w, h, round(pw * left), round(ph * top)


def _inside(box: tuple[int, int, int, int]) -> list[str]:
    w, h, x, y = box
    return ["-crop", f"{w}x{h}+{x}+{y}", "+repage"]


def _key(*entries: dict) -> str:
    blob = json.dumps(entries, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:8]


def _dither(contrast: str, ink: str, paper: str) -> list[str]:
    return [
        "-sigmoidal-contrast",
        contrast,
        "-dither",
        "FloydSteinberg",
        "-monochrome",
        "+level-colors",
        f"{ink},{paper}",
    ]


def render(scheme, size: tuple[int, int], out_dir: Path, configured_scale: int = 0) -> Walls:
    magick = _magick()
    w, h = size
    s = pixel_scale(h, configured_scale)
    lw, lh = math.ceil(w / s), math.ceil(h / s)
    manifest = _manifest()
    out_dir.mkdir(parents=True, exist_ok=True)
    levels, lock = manifest["level"], manifest["lock"]
    tag = f"{scheme.name}-{w}x{h}@{s}-{_key(levels, lock)}"
    lock_out = out_dir / f"lock-{tag}.png"

    level_outs = []
    for n, level in enumerate(levels, start=1):
        out = out_dir / f"desk-{n}-{tag}.png"
        level_outs.append(out)
        if out.exists():
            continue
        with as_file(files("athanor") / "plates" / level["file"]) as plate:
            box = inset_box(_size(plate), level.get("inset"))
            sw, sh, ox, oy = desk_crop(box[:2], (lw, lh), level["focus"], level["anchor"])
            subprocess.run(
                [
                    magick,
                    str(plate),
                    "-colorspace",
                    "gray",
                    *_inside(box),
                    "-gamma",
                    str(level.get("gamma", 1.0)),
                    "-resize",
                    f"{sw}x{sh}!",
                    "-crop",
                    f"{lw}x{lh}+{ox}+{oy}",
                    "+repage",
                    *_dither(level["contrast"], *scheme.wall_desk),
                    "-filter",
                    "point",
                    "-resize",
                    f"{lw * s}x{lh * s}!",
                    "-crop",
                    f"{w}x{h}+0+0",
                    "+repage",
                    str(out),
                ],
                check=True,
            )

    with as_file(files("athanor") / "plates" / lock["file"]) as plate:
        box = inset_box(_size(plate), lock.get("inset"))
        pw, ph = box[:2]
        plate_w = min(round(pw * lh / ph), round(lw * 0.6))
        if not lock_out.exists():
            ink, paper = scheme.wall_lock
            subprocess.run(
                [
                    magick,
                    "-size",
                    f"{lw}x{lh}",
                    f"xc:{scheme.roles['bg']}",
                    "(",
                    str(plate),
                    "-colorspace",
                    "gray",
                    *_inside(box),
                    "-resize",
                    f"{plate_w}x{lh}^",
                    "-gravity",
                    "center",
                    "-extent",
                    f"{plate_w}x{lh}",
                    *_dither(lock["contrast"], ink, paper),
                    ")",
                    "-gravity",
                    "west",
                    "-composite",
                    "-filter",
                    "point",
                    "-resize",
                    f"{lw * s}x{lh * s}!",
                    str(lock_out),
                ],
                check=True,
            )

    return Walls(levels=tuple(level_outs), lock=lock_out, lock_panel_x=plate_w * s, scale=s)


def card_image(
    src: Path,
    scheme,
    reversed_: bool,
    fmt: str,
    out: Path | None = None,
    *,
    height: int | None = None,
    width: int | None = None,
    scale: int = 2,
):
    if (height is None) == (width is None):
        raise ValueError("give a height or a width")
    geometry = f"{width // scale}x" if width else f"x{height // scale}"
    magick = _magick()
    ink, paper = scheme.wall_lock
    # HSL lightness rather than grayscale, which turns the cards' flat reds and
    # blues solid black.
    args = [
        magick, str(src),
        "-colorspace", "HSL", "-channel", "B", "-separate", "+channel",
        "-resize", geometry, "-gamma", "1.4",
        "-dither", "FloydSteinberg", "-monochrome",
        "+level-colors", f"{ink},{paper}",
    ]  # fmt: skip
    if reversed_:
        args += ["-rotate", "180"]
    args += ["-filter", "point", "-resize", f"{scale * 100}%"]
    if fmt == "sixel":
        return subprocess.run([*args, "sixel:-"], capture_output=True, check=True).stdout
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([*args, str(out)], check=True)
    return out


def spread_image(pngs: list[str], scheme, per_row: int, gap: int = 8) -> bytes:
    args = [_magick(), "montage", *pngs, "-tile", f"{per_row}x", "-geometry", f"+{gap}+{gap}"]
    args += ["-background", scheme.roles["bg"], "sixel:-"]
    return subprocess.run(args, capture_output=True, check=True).stdout
