import contextlib
import getpass
import json
import os
import shutil
import signal
import socket
import subprocess
import time
from datetime import date, datetime
from pathlib import Path

from . import config, cursor, hypr, palette, sigil, sky, stages, tarot, wall
from .paths import cache_dir, current_dir, runtime_dir, state_dir, write_atomic
from .render import render_tree

DEFAULT_SIZE = (1920, 1080)

HUES = {
    "umber": "The room takes on an umber hue.",
    "vellum": "The walls pale to the color of old vellum.",
    "orpiment": "The light yellows to orpiment.",
    "cinnabar": "The room reddens to cinnabar.",
}


def saved_scheme() -> str:
    try:
        name = (state_dir() / "scheme").read_text().strip()
    except OSError:
        return "umber"
    name = palette.RETIRED.get(name, name)
    return name if name in palette.SCHEMES else "umber"


def osc(scheme: palette.Scheme) -> str:
    seq = "".join(f"\033]4;{i};{c}\007" for i, c in enumerate(scheme.ansi))
    r = scheme.roles
    return seq + f"\033]10;{r['fg']}\007\033]11;{r['bg']}\007\033]12;{r['fg']}\007"


def recolor_terminals(scheme: palette.Scheme) -> int:
    seq, count, uid = osc(scheme), 0, os.getuid()
    pts = Path("/dev/pts")
    for tty in pts.iterdir() if pts.is_dir() else ():
        if not tty.name.isdigit():
            continue
        try:
            if tty.stat().st_uid != uid:
                continue
            with open(tty, "w") as f:
                f.write(seq)
            count += 1
        except OSError:
            continue
    return count


def run(*cmd: str) -> None:
    if shutil.which(cmd[0]):
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def _swaybg_pids() -> list[int]:
    out = subprocess.run(["pgrep", "-x", "swaybg"], capture_output=True, text=True)
    return [int(p) for p in out.stdout.split()]


def _hyprpaper(path: Path) -> bool:
    out = subprocess.run(["pgrep", "-x", "hyprpaper"], capture_output=True)
    if out.returncode != 0 or not shutil.which("hyprctl"):
        return False
    done = subprocess.run(
        ["hyprctl", "hyprpaper", "wallpaper", f",{path}"], capture_output=True, text=True
    )
    return done.returncode == 0


def start_wallpaper(path: Path) -> None:
    if _hyprpaper(path):
        return
    if not shutil.which("swaybg"):
        return
    shown = runtime_dir() / "athanor-wall"
    old = _swaybg_pids()
    try:
        if old and shown.read_text() == str(path):
            return
    except OSError:
        pass
    subprocess.Popen(
        ["swaybg", "-m", "fill", "-i", str(path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    write_atomic(shown, str(path))
    # Kill the old swaybg only after the new one is up, or the screen flashes.
    if old:
        time.sleep(0.3)
        for pid in old:
            with contextlib.suppress(OSError):
                os.kill(pid, signal.SIGTERM)


def screen_or_default(log=print) -> tuple[int, int]:
    size = hypr.screen_size()
    if size:
        return size
    w, h = DEFAULT_SIZE
    log(
        f"No running Hyprland answered, so this is drawn for {w}x{h}. "
        "Run athanor transmute again inside the session to fit the screen."
    )
    return DEFAULT_SIZE


def current_walls(size: tuple[int, int] | None = None):
    cfg = config.load()
    size = size or hypr.screen_size() or DEFAULT_SIZE
    return wall.render(
        palette.load(saved_scheme()), size, cache_dir() / "wall", cfg.pixel_scale, cfg.levels
    )


def show_level(workspace: int | None = None) -> Path:
    walls = current_walls()
    path = walls.level(workspace if workspace is not None else hypr.active_workspace())
    start_wallpaper(path)
    return path


CARD_ASPECT = 0.58
MARGIN = 72
TEXT_COLUMN = 300
GAP = 40


def lock_layout(size: tuple[int, int], panel_x: int, scale: int) -> dict[str, int]:
    w, h = size
    lock_x = panel_x + MARGIN
    room = w - MARGIN - (lock_x + TEXT_COLUMN + GAP)
    tall = int((h - 2 * MARGIN) * CARD_ASPECT)
    card_w = max(0, min(320, room, tall))
    card_w -= card_w % scale
    return {"lock_x": lock_x, "card_w": card_w}


def _layout_state() -> Path:
    return state_dir() / "lock.json"


def card_of_day_png(scheme: palette.Scheme, layout: dict[str, int] | None = None) -> Path | None:
    # hyprlock's reload_cmd calls this without a layout.
    if layout is None:
        try:
            layout = json.loads(_layout_state().read_text())
        except (OSError, json.JSONDecodeError):
            layout = {"card_w": 320, "scale": 2}
    width, scale = layout["card_w"], layout.get("scale", 2)
    if width <= 0:
        return None
    seed, _ = sigil.host_digest()
    today = date.today()
    draw = tarot.card_of_day(today, seed)
    src = tarot.art_path(draw.card, cache_dir() / "tarot")
    if not src.exists():
        return None
    out, stamp = cache_dir() / "tarot-day.png", cache_dir() / "tarot-day.stamp"
    key = f"{today} {scheme.name} {draw.title} {width}@{scale}"
    try:
        current = stamp.read_text()
    except OSError:
        current = ""
    if current != key or not out.exists():
        wall.card_image(src, scheme, draw.reversed, "png", out, width=width, scale=scale)
        write_atomic(stamp, key)
    return out


def tokens(
    scheme,
    size,
    walls,
    sigil_png: Path,
    fingerprint: str,
    font: str = config.Config.terminal_font,
    name: str = "",
) -> dict[str, str]:
    w, h = size
    face = config.TERMINAL_FONTS[font]
    layout = lock_layout(size, walls.lock_panel_x if walls else 0, walls.scale if walls else 2)
    return {
        **scheme.colors(),
        "scheme": scheme.name,
        "label": scheme.label,
        "screen_w": str(w),
        "screen_h": str(h),
        "lock_x": str(layout["lock_x"]),
        "card_w": str(layout["card_w"]),
        "text_w": str(TEXT_COLUMN),
        "wall_desk": str(walls.desk) if walls else "",
        **{f"wall_{n}": str(walls.level(n)) if walls else "" for n in range(1, 8)},
        "wall_lock": str(walls.lock) if walls else "",
        "sigil": str(sigil_png),
        "host": socket.gethostname(),
        "name": name or getpass.getuser(),
        "fingerprint": fingerprint,
        "fingerprint_short": fingerprint if len(fingerprint) <= 24 else fingerprint[:23] + "…",
        "beside_x": str(layout["lock_x"] + 88 + 16),
        "bin": str(Path.home() / ".local/bin/athanor"),
        "card_png": str(cache_dir() / "tarot-day.png"),
        "term_font": face.family,
        "term_px": str(face.px),
        "term_icon_px": str(round(face.px * 3 / 4)),
        "term_font_bold": f"{face.bold}:pixelsize={face.px}"
        if face.bold
        else f"{face.family}:pixelsize={face.px}:weight=bold",
        "term_font_italic": f"{face.italic}:style=Italic:pixelsize={face.px}"
        if face.italic
        else f"{face.family}:pixelsize={face.px}",
    }


def apply(
    name: str,
    reload: bool = True,
    size: tuple[int, int] | None = None,
    log=print,
    message: str | None = None,
):
    scheme = palette.load(name)
    cfg = config.load()
    size = size or screen_or_default(log)

    try:
        walls = wall.render(scheme, size, cache_dir() / "wall", cfg.pixel_scale, cfg.levels)
    except wall.MissingTool as e:
        log(f"no plates this time: {e}")
        walls = None

    digest, fingerprint = sigil.host_digest()
    sigil_png = cache_dir() / f"sigil-{scheme.name}.png"
    write_atomic(sigil_png, sigil.png(sigil.grid(digest), scheme.roles["sigil"]))

    if walls:
        layout = {**lock_layout(size, walls.lock_panel_x, walls.scale), "scale": walls.scale}
        write_atomic(_layout_state(), json.dumps(layout))
        card_of_day_png(scheme, layout)
    toks = tokens(scheme, size, walls, sigil_png, fingerprint, cfg.terminal_font, cfg.name)
    render_tree(current_dir(), toks)
    write_atomic(state_dir() / "scheme", scheme.name + "\n")
    cursor.render(scheme)

    if reload:
        hypr.request("reload")
        run("pkill", "-SIGUSR2", "-x", "waybar")
        run("makoctl", "reload")
        if walls:
            start_wallpaper(walls.level(hypr.active_workspace()))
        recolor_terminals(scheme)
        cursor.show()
        run(
            "notify-send",
            "-a",
            "athanor",
            message or f"You read a scroll of transmutation. {HUES[scheme.name]}",
        )
    return scheme, walls


def prerender(size: tuple[int, int] | None = None) -> None:
    cfg = config.load()
    size = size or hypr.screen_size() or DEFAULT_SIZE
    for name in palette.SCHEMES:
        with contextlib.suppress(wall.MissingTool, subprocess.CalledProcessError):
            wall.render(palette.load(name), size, cache_dir() / "wall", cfg.pixel_scale, cfg.levels)


def wake(wall: bool = True) -> None:
    cfg = config.load()
    name = saved_scheme()
    if cfg.stages:
        name = stages.scheme_at(sky.planetary_hour(datetime.now().astimezone(), cfg.place))
    _, walls = apply(name, reload=False)
    cursor.show()
    if walls and wall:
        start_wallpaper(walls.level(hypr.active_workspace()))
    subprocess.Popen(
        [str(Path.home() / ".local/bin/athanor"), "prerender"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
