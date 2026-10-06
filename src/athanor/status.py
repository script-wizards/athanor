import dataclasses
import json
import os
import select
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from . import hypr

POWER = Path("/sys/class/power_supply")


@dataclass(frozen=True)
class Battery:
    percent: int
    health: int
    charging: bool


@dataclass(frozen=True)
class Reading:
    workspace: int | None
    disk_free: int
    battery: Battery | None
    cpu: int | None
    mem_used: int
    minutes: int


def _read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def battery(root: Path = POWER) -> Battery | None:
    if not root.exists():
        return None
    for supply in sorted(root.iterdir()):
        if _read(supply / "type") != "Battery" or _read(supply / "present") == "0":
            continue
        capacity = _read(supply / "capacity")
        if capacity is None:
            continue
        health = 100
        for kind in ("energy", "charge"):
            full, design = _read(supply / f"{kind}_full"), _read(supply / f"{kind}_full_design")
            if full and design and int(design) > 0:
                health = min(100, round(100 * int(full) / int(design)))
                break
        charging = _read(supply / "status") in ("Charging", "Full")
        return Battery(int(capacity), health, charging)
    return None


class Cpu:
    def __init__(self, stat: Path = Path("/proc/stat")):
        self.stat = stat
        self.prev: tuple[int, int] | None = None

    def _sample(self) -> tuple[int, int] | None:
        line = _read(self.stat)
        if not line:
            return None
        fields = [int(v) for v in line.splitlines()[0].split()[1:]]
        idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
        return idle, sum(fields)

    def percent(self) -> int | None:
        now = self._sample()
        prev, self.prev = self.prev, now
        if now is None or prev is None or now[1] == prev[1]:
            return None
        busy = 1 - (now[0] - prev[0]) / (now[1] - prev[1])
        return max(0, min(100, round(busy * 100)))


def mem_used(meminfo: Path = Path("/proc/meminfo")) -> int:
    values = {}
    for line in (_read(meminfo) or "").splitlines():
        key, _, rest = line.partition(":")
        values[key] = int(rest.split()[0]) * 1024
    return values.get("MemTotal", 0) - values.get("MemAvailable", 0)


def uptime_minutes(uptime: Path = Path("/proc/uptime")) -> int:
    text = _read(uptime)
    return int(float(text.split()[0]) // 60) if text else 0


def disk_free(path: str = "/") -> int:
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize


def size(n: int, decimals: int = 0) -> str:
    gib = n / 2**30
    if gib >= 1000:
        return f"{gib / 1024:.1f}T"
    return f"{gib:.{decimals}f}G"


def read(cpu: Cpu) -> Reading:
    return Reading(
        workspace=hypr.active_workspace(),
        disk_free=disk_free(),
        battery=battery(),
        cpu=cpu.percent(),
        mem_used=mem_used(),
        minutes=uptime_minutes(),
    )


def hp(b: Battery | None) -> str:
    if b is None:
        return "Hp:AC"
    return f"Hp:{b.percent}({b.health}){'+' if b.charging else ''}"


def line(r: Reading) -> str:
    return "  ".join(
        (
            f"Dlvl:{r.workspace if r.workspace is not None else '?'}",
            f"$:{size(r.disk_free)}",
            hp(r.battery),
            f"Str:{r.cpu if r.cpu is not None else '--'}%",
            f"Mem:{size(r.mem_used, 1)}",
            f"T:{r.minutes}",
        )
    )


def short(r: Reading) -> str:
    return f"{hp(r.battery)}  T:{r.minutes}"


def classes(r: Reading) -> list[str]:
    b = r.battery
    if b is None or b.charging:
        return []
    if b.percent <= 10:
        return ["hurt", "dying"]
    if b.percent <= 20:
        return ["hurt"]
    return []


TOOLTIP = (
    "Dlvl workspace. $ disk. Hp battery. Str CPU. T minutes awake. The rest is in `athanor guide`."
)


PROMPT_EVENTS = (b"workspace>>", b"workspacev2>>", b"focusedmon>>", b"focusedmonv2>>")


def wants_redraw(chunk: bytes) -> bool:
    return any(line.startswith(PROMPT_EVENTS) for line in chunk.splitlines())


def waybar(interval: float = 2.0) -> None:
    cpu = Cpu()
    cpu.percent()
    sock = hypr.events()
    last = None

    def emit(r: Reading) -> None:
        out = {"text": line(r), "class": classes(r), "tooltip": TOOLTIP}
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()

    deadline = time.monotonic() + interval
    while True:
        wait = max(0.0, deadline - time.monotonic())
        ready = select.select([sock], [], [], wait)[0] if sock else time.sleep(wait) or []
        if ready:
            chunk = sock.recv(65536)
            if not chunk:
                sock.close()
                sock = None
            elif wants_redraw(chunk) and last is not None:
                last = dataclasses.replace(last, workspace=hypr.active_workspace())
                emit(last)
            continue
        last = read(cpu)
        emit(last)
        deadline = time.monotonic() + interval


def plain(brief: bool = False) -> str:
    cpu = Cpu()
    cpu.percent()
    time.sleep(0.25)
    r = read(cpu)
    return short(r) if brief else line(r)
