import getpass
import os
import platform
import textwrap
from pathlib import Path

from . import macos, status
from .ansi import paint

COMPASS = ("north", "south", "east", "west", "up", "down", "in", "out")


def _exit_order(item: tuple[str, str]) -> tuple[int, str]:
    direction = item[0]
    return (COMPASS.index(direction) if direction in COMPASS else len(COMPASS), direction)


def room(cfg, card_title: str | None, color: bool) -> str:
    out = [paint(f"~ {cfg.room_name} ~", 3, color)]
    out += textwrap.wrap(cfg.room_description, 60)
    exits = sorted(cfg.exits.items(), key=_exit_order)
    if exits:
        width = max(len(d) for d, _ in exits)
        label = "Obvious exits: "
        for i, (direction, target) in enumerate(exits):
            name = Path(os.path.expanduser(target)).name or target
            lead = paint(label, 8, color) if i == 0 else " " * len(label)
            out.append(f"{lead}{direction.ljust(width)} ({paint(name, 15, color)})")
    if card_title:
        out.append(
            paint("On the desk lies a card: ", 8, color) + paint(card_title, 15, color) + "."
        )
    return "\n".join(out)


def _os_release() -> dict[str, str]:
    values = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            key, _, value = line.partition("=")
            values[key] = value.strip('"')
    except OSError:
        pass
    return values


def _packages() -> str:
    local = Path("/var/lib/pacman/local")
    if not local.is_dir():
        return "?"
    return f"{sum(1 for p in local.iterdir() if p.is_dir())} items"


def sheet(cfg, color: bool) -> str:
    osr = _os_release()
    battery = status.battery()
    rows = [
        (
            "Race",
            cfg.race or ("macOS" if macos.available() else osr.get("NAME", platform.system())),
            "Kernel",
            platform.release().split("-")[0],
        ),
        (
            "Class",
            "Aqua" if macos.available() else os.environ.get("XDG_CURRENT_DESKTOP", "tty"),
            "Shell",
            Path(os.environ.get("SHELL", "sh")).name,
        ),
        ("Hp", status.hp(battery).removeprefix("Hp:"), "Mem", status.size(status.mem_used(), 1)),
        ("Pack", _packages(), "", ""),
    ]
    name = f"{cfg.name or getpass.getuser()} {cfg.title}"
    out = [paint(name, 15, color)]
    for k1, v1, k2, v2 in rows:
        line = f"{paint(f' {k1:<6}', 8, color)} {v1:<16}"
        if k2:
            line += f"{paint(f'{k2:<7}', 8, color)} {v2}"
        out.append(line.rstrip())
    return "\n".join(out)
