import json
import signal
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

WIDTH = 18


@dataclass(frozen=True)
class Crash:
    name: str
    signal: int
    when: datetime
    stamp: int


def _center(s: str) -> str:
    s = s[:WIDTH]
    left = (WIDTH - len(s)) // 2
    return " " * left + s + " " * (WIDTH - len(s) - left)


def cause(sig: int) -> str:
    try:
        return signal.Signals(sig).name
    except ValueError:
        return f"signal {sig}"


def stone(name: str, sig: int, year: int, dlvl: int | None = None) -> str:
    lines = [
        "         __________",
        "        /          \\",
        "       /    REST    \\",
        "      /      IN      \\",
        "     /     PEACE      \\",
        "    /                  \\",
        f"    |{_center(name)}|",
        f"    |{_center('killed by a')}|",
        f"    |{_center(cause(sig))}|",
    ]
    if dlvl is not None:
        lines.append(f"    |{_center(f'on Dlvl {dlvl}')}|")
    lines += [
        f"    |{_center(str(year))}|",
        "   *|     *  *  *      | *",
        "____)/\\\\_//(\\/(/\\)/\\//\\/|_)____",
    ]
    return "\n".join(lines)


# These all die at logout (hypridle aborts every time), so their crashes from
# the previous session are ignored.
SESSION_PROGRAMS = frozenset(
    {"hypridle", "hyprlock", "hyprpaper", "waybar", "mako", "swaybg", "fuzzel", "foot"}
)


def from_last_session(crash: "Crash", session_start: float | None) -> bool:
    return (
        session_start is not None
        and crash.name in SESSION_PROGRAMS
        and crash.stamp / 1_000_000 < session_start
    )


def clean(name: str) -> str:
    # Processes name themselves. Don't let one put escape codes in a terminal.
    return "".join(c if c.isprintable() else "?" for c in name) or "something"


def parse(entries: list[dict]) -> Crash | None:
    if not entries:
        return None
    e = entries[-1]
    stamp = int(e.get("time", 0))
    exe = e.get("exe") or e.get("comm") or "something"
    return Crash(
        name=clean(Path(exe).name),
        signal=int(e.get("sig", 0)),
        when=datetime.fromtimestamp(stamp / 1_000_000, UTC),
        stamp=stamp,
    )


def latest() -> Crash | None:
    try:
        out = subprocess.run(
            # -n counts from the oldest, so --reverse is needed to get the newest.
            ["coredumpctl", "list", "--json=short", "--no-pager", "--reverse", "-n", "1"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    try:
        return parse(json.loads(out.stdout))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
