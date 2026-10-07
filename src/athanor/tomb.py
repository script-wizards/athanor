import json
import signal
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from . import macos

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
    if macos.available():
        return latest_macos()
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


def parse_macos(text: str) -> Crash | None:
    # .ips reports contain a metadata JSON object followed by a report object.
    try:
        header, end = json.JSONDecoder().raw_decode(text.lstrip())
        rest = text.lstrip()[end:].strip()
        report = json.loads(rest) if rest else header
        name = report.get("procName") or header.get("app_name")
        sig = report.get("exception", {}).get("signal", "")
        number = getattr(signal, sig, None) if isinstance(sig, str) else None
        stamp = report.get("captureTime") or header.get("timestamp")
        if not name or number is None or not stamp:
            return None
        when = datetime.fromisoformat(stamp).astimezone(UTC)
        return Crash(clean(name), int(number), when, int(when.timestamp() * 1_000_000))
    except (ValueError, TypeError, AttributeError):
        return None


def latest_macos(roots: tuple[Path, ...] | None = None) -> Crash | None:
    roots = (
        roots
        if roots is not None
        else (
            Path.home() / "Library/Logs/DiagnosticReports",
            Path("/Library/Logs/DiagnosticReports"),
        )
    )
    reports = []
    for root in roots:
        try:
            reports += [(p.stat().st_mtime, p) for p in root.glob("*.ips")]
        except OSError:
            continue
    for _, path in sorted(reports, reverse=True):
        try:
            crash = parse_macos(path.read_text())
        except (OSError, UnicodeError):
            continue
        if crash:
            return crash
    return None
