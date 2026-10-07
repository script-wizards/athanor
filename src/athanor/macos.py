"""Small macOS adapters; Linux keeps its existing backends."""

import ctypes
import plistlib
import re
import subprocess
import sys
import time
from functools import cache
from pathlib import Path

from . import palette
from .paths import write_atomic


def available() -> bool:
    return sys.platform == "darwin"


def command(*args: str) -> str:
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout if done.returncode == 0 else ""


@cache
def _system():
    lib = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
    lib.mach_host_self.restype = ctypes.c_uint
    lib.host_statistics.argtypes = (
        ctypes.c_uint,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint),
    )
    lib.host_statistics.restype = ctypes.c_int
    return lib


@cache
def _host() -> int:
    return _system().mach_host_self()


def cpu_sample() -> tuple[int, int] | None:
    # HOST_CPU_LOAD_INFO: user, system, idle, nice ticks across all CPUs.
    try:
        lib = _system()
        ticks = (ctypes.c_uint * 4)()
        count = ctypes.c_uint(4)
        if lib.host_statistics(_host(), 3, ticks, ctypes.byref(count)) != 0:
            return None
        return ticks[2], sum(ticks)
    except (OSError, AttributeError):
        return None


def battery_info() -> tuple[int, int, bool] | None:
    text = command("/usr/bin/pmset", "-g", "batt")
    found = re.search(r"(\d+)%;\s*([^;]+)", text)
    if not found:
        return None
    health = 100
    try:
        supplies = plistlib.loads(
            command("/usr/sbin/ioreg", "-r", "-c", "AppleSmartBattery", "-a").encode()
        )
        info = supplies[0]
        full, design = info.get("MaxCapacity", 0), info.get("DesignCapacity", 0)
        if 0 < full <= 100 and design > 100:
            health = full  # Apple Silicon reports MaxCapacity as a percentage.
        elif full > 0 and design > 0:
            health = min(100, round(full * 100 / design))
    except (ValueError, TypeError, IndexError, KeyError, plistlib.InvalidFileException):
        pass
    return int(found[1]), health, found[2].strip() in ("charging", "charged", "finishing charge")


def mem_used() -> int:
    text = command("/usr/bin/vm_stat")
    page = re.search(r"page size of (\d+) bytes", text)
    if not page:
        return 0
    counts = dict(re.findall(r"^([^:\n]+):\s*(\d+)\.", text, re.MULTILINE))
    # Physical pages in use, including compressed memory (not its uncompressed size).
    used = sum(
        int(counts.get(key, 0))
        for key in ("Pages active", "Pages wired down", "Pages occupied by compressor")
    )
    return used * int(page[1])


def uptime_minutes() -> int:
    text = command("/usr/sbin/sysctl", "-n", "kern.boottime")
    boot = re.search(r"\bsec\s*=\s*(\d+)", text)
    return max(0, int((time.time() - int(boot[1])) // 60)) if boot else 0


def machine_id() -> str:
    text = command("/usr/sbin/ioreg", "-rd1", "-c", "IOPlatformExpertDevice")
    found = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', text)
    return found[1] if found else ""


def screen_size() -> tuple[int, int] | None:
    try:
        lib = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        lib.CGMainDisplayID.restype = ctypes.c_uint
        sizes = []
        for name in ("CGDisplayPixelsWide", "CGDisplayPixelsHigh"):
            fn = getattr(lib, name)
            fn.argtypes = (ctypes.c_uint,)
            fn.restype = ctypes.c_size_t
            sizes.append(fn(lib.CGMainDisplayID()))
        return tuple(sizes) if all(sizes) else None
    except (OSError, AttributeError):
        return None


def notify(message: str) -> None:
    command(
        "/usr/bin/osascript",
        "-e",
        'on run argv\ndisplay notification (item 1 of argv) with title "Athanor"\nend run',
        message,
    )


def set_wallpaper(path: Path) -> bool:
    # Pass the path as data, so quotes and backslashes cannot become AppleScript.
    script = (
        'on run argv\ntell application "System Events"\n'
        "repeat with d in every desktop\nset picture of d to (item 1 of argv)\n"
        'end repeat\nend tell\nreturn "ok"\nend run'
    )
    return command("/usr/bin/osascript", "-e", script, str(path)).strip() == "ok"


def _color(hexcolor: str) -> bytes:
    rgb = " ".join(f"{v / 255:.8f}" for v in palette.rgb(hexcolor))
    return plistlib.dumps(
        {
            "$archiver": "NSKeyedArchiver",
            "$version": 100000,
            "$top": {"root": plistlib.UID(1)},
            "$objects": [
                "$null",
                {"$class": plistlib.UID(2), "NSColorSpace": 1, "NSRGB": (rgb + "\0").encode()},
                {"$classes": ["NSColor", "NSObject"], "$classname": "NSColor"},
            ],
        },
        fmt=plistlib.FMT_BINARY,
    )


def render_profiles(dest: Path) -> None:
    colors = ("Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White")
    for name in palette.SCHEMES:
        scheme = palette.load(name)
        profile = {
            "name": f"Athanor {scheme.label}",
            "type": "Window Settings",
            "ProfileCurrentVersion": 2.07,
            "BackgroundColor": _color(scheme.roles["bg"]),
            "TextColor": _color(scheme.roles["fg"]),
            "TextBoldColor": _color(scheme.roles["fg"]),
            "CursorColor": _color(scheme.roles["fg"]),
            "SelectionColor": _color(scheme.roles["dim"]),
            "UseBoldFonts": True,
            "UseBrightBold": False,
            "columnCount": 100,
            "rowCount": 30,
        }
        for i, color in enumerate(scheme.ansi):
            key = f"ANSI{'Bright' if i >= 8 else ''}{colors[i % 8]}Color"
            profile[key] = _color(color)
        write_atomic(dest / f"athanor-{name}.terminal", plistlib.dumps(profile))
