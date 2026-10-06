import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from . import ansi, config, hypr, palette
from .paths import cache_dir, config_dir, current_dir
from .transmute import saved_scheme

OK, WARN, FAIL = "ok", "warn", "FAIL"

FONT_FILES = (
    "PxPlus_IBM_VGA_8x16.ttf",
    "Px437_CompaqThin_8x16.ttf",
    "Px437_Tandy2K.ttf",
    "Px437_ATT_PC6300.ttf",
    "TerminusTTF-4.49.3.ttf",
    "CozetteVector.ttf",
    "t0-16i-uni.bdf",
    "Jacquard24-Regular.ttf",
    "IMFeENrm28P.ttf",
)
HYPRLAND_TARGET = (0, 56)
BEGIN_MARK = ">>> athanor >>>"
SINGLE_PROCESS_TERMINALS = ("xfce4-terminal", "gnome-terminal-server", "konsole")


@dataclass(frozen=True)
class Result:
    area: str
    status: str
    found: str
    fix: str = ""


def _run(*cmd: str, timeout: float = 5) -> subprocess.CompletedProcess | None:
    if not shutil.which(cmd[0]):
        return None
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _font_dir() -> Path:
    data = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
    return Path(data) / "fonts" / "athanor"


def check_font_files() -> list[Result]:
    missing = [f for f in FONT_FILES if not (_font_dir() / f).is_file()]
    if not missing:
        return [Result("fonts", OK, f"All {len(FONT_FILES)} fonts are in {_font_dir()}.")]
    return [
        Result(
            "fonts",
            FAIL,
            f"Missing: {', '.join(missing)}.",
            "Run ./install.sh shell.",
        )
    ]


def check_fonts_resolve(match=None) -> list[Result]:
    match = match or _fc_family
    face = config.TERMINAL_FONTS[config.load().terminal_font]
    wanted = [face.family, *[f for f in (face.bold, face.italic) if f], "PxPlus IBM VGA 8x16"]
    wanted += ["Jacquard 24"]
    out = []
    for family in dict.fromkeys(wanted):
        got = match(family)
        if got is None:
            return [Result("fonts", WARN, "Couldn't check the fonts because fc-match is missing.")]
        if got.lower() != family.lower():
            out.append(
                Result(
                    "fonts",
                    FAIL,
                    f"{family} resolves to {got}.",
                    "Run ./install.sh shell and then fc-cache -f. In foot's config, a hyphen "
                    "in a family name is written as \\-.",
                )
            )
    return out or [Result("fonts", OK, "Every font resolves.")]


def _fc_family(family: str) -> str | None:
    done = _run("fc-match", "-f", "%{family[0]}", family)
    return done.stdout.strip() if done and done.returncode == 0 else None


def check_stale_terminals(now: float | None = None, started=None) -> list[Result]:
    fonts = [p for p in _font_dir().glob("*.ttf")]
    if not fonts:
        return []
    newest = max(p.stat().st_mtime for p in fonts)
    started = started or _process_starts
    stale = [name for name, t in started(SINGLE_PROCESS_TERMINALS) if t < newest]
    if not stale:
        return []
    names = ", ".join(sorted(set(stale)))
    return [
        Result(
            "fonts",
            WARN,
            f"{names} started before the fonts were installed and can't use them.",
            f"Close every {names} window and open a new one.",
        )
    ]


def _process_starts(names) -> list[tuple[str, float]]:
    out = []
    boot = time.time() - float(Path("/proc/uptime").read_text().split()[0])
    hz = os.sysconf("SC_CLK_TCK")
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            comm = (proc / "comm").read_text().strip()
            if comm not in names:
                continue
            ticks = int((proc / "stat").read_text().rsplit(")", 1)[1].split()[19])
        except (OSError, IndexError, ValueError):
            continue
        out.append((comm, boot + ticks / hz))
    return out


def _zshrc() -> Path:
    done = _run("zsh", "-c", 'print -r -- "${ZDOTDIR:-$HOME}"')
    home = done.stdout.strip() if done and done.returncode == 0 else str(Path.home())
    return Path(home) / ".zshrc"


def _managed_by(path: Path) -> str | None:
    if path.is_symlink():
        return f"a symlink to {path.resolve()}"
    done = _run("chezmoi", "source-path", str(path))
    if done and done.returncode == 0:
        return f"managed by chezmoi ({done.stdout.strip()})"
    return None


def _block_check(area: str, path: Path, line: str) -> Result:
    if not path.exists():
        return Result(area, WARN, f"No {path}.", "Run ./install.sh to add it.")
    try:
        text = path.read_text()
    except OSError as e:
        return Result(area, WARN, f"Can't read {path}: {e.strerror}.")
    if BEGIN_MARK in text:
        return Result(area, OK, f"The block is in {path}.")
    managed = _managed_by(path)
    if managed:
        return Result(
            area,
            WARN,
            f"{path} is {managed}. Athanor's block isn't in it.",
            f"Add this to the source: {line}",
        )
    return Result(area, WARN, f"Athanor's block isn't in {path}.", "Run ./install.sh to add it.")


def check_zsh() -> list[Result]:
    line = "[[ -r ~/.config/athanor/athanor.zsh ]] && source ~/.config/athanor/athanor.zsh"
    return [_block_check("shell", _zshrc(), line)]


def _hypr_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "hypr"


def check_hypr_config() -> list[Result]:
    lua, conf = _hypr_dir() / "hyprland.lua", _hypr_dir() / "hyprland.conf"
    if not lua.exists() and not conf.exists():
        return [Result("hyprland", WARN, "No Hyprland config.", "Run ./install.sh.")]
    if lua.exists():
        out = [
            _block_check(
                "hyprland",
                lua,
                'require((os.getenv("HOME") .. "/.config/athanor/hypr/") .. "athanor")',
            )
        ]
        if conf.exists():
            out.append(
                Result(
                    "hyprland",
                    OK,
                    "hyprland.conf remains. Hyprland ignores it.",
                )
            )
        return out
    return [
        _block_check("hyprland", conf, "source = ~/.config/athanor/hypr/athanor.conf"),
        Result(
            "hyprland",
            WARN,
            "hyprland.conf uses hyprlang. Per-workspace wallpapers need hyprland.lua.",
            "Move hyprland.conf aside and run ./install.sh desktop.",
        ),
    ]


def check_hypr_session() -> list[Result]:
    if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return check_x_session()
    out = []
    version = _hypr_version()
    if version and version[:2] < HYPRLAND_TARGET:
        want = ".".join(map(str, HYPRLAND_TARGET))
        out.append(
            Result(
                "hyprland",
                WARN,
                f"Hyprland {'.'.join(map(str, version))}. Athanor wants {want}.",
                "pacman -Syu",
            )
        )
    errors = (hypr.request("configerrors") or "").strip()
    if errors:
        first = errors.splitlines()[0]
        out.append(
            Result(
                "hyprland",
                FAIL,
                f"Config errors: {first}",
                "hyprctl configerrors lists them all.",
            )
        )
    else:
        out.append(Result("hyprland", OK, "No config errors."))
    if (_hypr_dir() / "hyprland.lua").exists() and not _running("hyprpaper"):
        out.append(
            Result(
                "hyprland",
                WARN,
                "hyprpaper isn't running. Wallpapers won't change with the workspace.",
                "Log in again or run hyprpaper --config "
                "~/.config/athanor/current/hypr/hyprpaper.conf",
            )
        )
    return out


def _hypr_version() -> tuple[int, ...] | None:
    reply = hypr.request("j/version")
    try:
        tag = json.loads(reply or "{}").get("tag", "")
    except json.JSONDecodeError:
        return None
    parts = tag.lstrip("v").split(".")
    return tuple(int(p) for p in parts if p.isdigit()) or None


def check_x_session() -> list[Result]:
    done = _run("loginctl", "list-sessions", "--no-legend")
    if not done or done.returncode != 0:
        return []
    for line in done.stdout.splitlines():
        sid = line.split()[0] if line.split() else ""
        show = _run("loginctl", "show-session", sid, "-p", "Type", "-p", "Active", "-p", "Seat")
        props = dict(p.split("=", 1) for p in (show.stdout.split() if show else []) if "=" in p)
        if props.get("Type") == "x11" and props.get("Active") == "yes" and props.get("Seat"):
            return [
                Result(
                    "session",
                    WARN,
                    "An X session holds this seat. Hyprland from a tty will fail: "
                    "'Found no gpus to use'.",
                    "Log out of it first or pick Hyprland at the login screen.",
                )
            ]
    return []


def check_display_manager(conf: Path = Path("/etc/lightdm/lightdm.conf")) -> list[Result]:
    try:
        text = conf.read_text()
    except OSError:
        return []
    values = {}
    for line in text.splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            values[key.strip()] = value.strip()
    if "mini-greeter" not in values.get("greeter-session", ""):
        return []
    session = values.get("user-session", "")
    if session.startswith("hyprland"):
        return [Result("session", OK, "LightDM starts Hyprland.")]
    return [
        Result(
            "session",
            WARN,
            f"The greeter has no session menu. It starts '{session or 'its default'}'. "
            "~/.dmrc is ignored.",
            f"Set user-session=hyprland in {conf}. Needs sudo.",
        )
    ]


def _running(name: str) -> bool:
    done = _run("pgrep", "-x", name)
    return bool(done and done.returncode == 0)


def check_place() -> list[Result]:
    if config.load().place:
        return [Result("athanor", OK, "[place] is set.")]
    return [
        Result(
            "athanor",
            WARN,
            "No [place] set. The planetary hours assume sunrise at 6:00 and sunset at 18:00.",
            f"Set latitude and longitude under [place] in {config_dir() / 'athanor.toml'}.",
        )
    ]


def check_rendered() -> list[Result]:
    scheme = saved_scheme()
    needed = ["foot/foot.ini", "hypr/hyprlock.conf", "hypr/levels.lua", "mako/config"]
    missing = [n for n in needed if not (current_dir() / n).exists()]
    if missing:
        return [
            Result(
                "athanor",
                FAIL,
                f"{scheme} is half rendered. Missing: {', '.join(missing)}.",
                f"Run athanor transmute {scheme}.",
            )
        ]
    plates = list((cache_dir() / "wall").glob(f"desk-*-{scheme}-*.png"))
    label = palette.load(scheme).label
    if not plates:
        return [
            Result(
                "athanor",
                WARN,
                f"{label} has no wallpapers.",
                f"Run athanor transmute {scheme}.",
            )
        ]
    return [Result("athanor", OK, f"{label} is rendered.")]


def check_tomb_watcher() -> list[Result]:
    done = _run("systemctl", "--user", "is-active", "athanor-tomb.path")
    if done is None:
        return []
    if done.stdout.strip() == "active":
        return [Result("athanor", OK, "athanor-tomb.path is active.")]
    return [
        Result(
            "athanor",
            WARN,
            "athanor-tomb.path is inactive. Crashes won't be announced.",
            "systemctl --user enable --now athanor-tomb.path",
        )
    ]


CHECKS = (
    check_font_files,
    check_fonts_resolve,
    check_stale_terminals,
    check_zsh,
    check_hypr_config,
    check_hypr_session,
    check_display_manager,
    check_place,
    check_rendered,
    check_tomb_watcher,
)


def run_all() -> list[Result]:
    results = []
    for check in CHECKS:
        try:
            results += check()
        except Exception as e:
            results.append(Result("doctor", WARN, f"{check.__name__} could not run: {e}"))
    return results


def render(results: list[Result], color: bool) -> str:
    slot = {OK: 2, WARN: 3, FAIL: 1}
    lines = []
    for r in results:
        mark = ansi.paint(f"{r.status:>4}", slot[r.status], color)
        lines.append(f"{mark}  {ansi.paint(f'{r.area:<9}', 8, color)} {r.found}")
        if r.fix:
            lines.append(f"{'':15} {ansi.paint('fix:', 8, color)} {r.fix}")
    fails = sum(r.status == FAIL for r in results)
    warns = sum(r.status == WARN for r in results)
    if fails:
        lines.append(f"\nYou have {fails} wound{'s' * (fails != 1)} to tend.")
    elif warns:
        lines.append(f"\nYou feel mostly well. {warns} thing{'s' * (warns != 1)} to mend.")
    else:
        lines.append("\nYou feel in good health.")
    return "\n".join(lines)


def main(as_json: bool = False) -> int:
    results = run_all()
    if as_json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        print(render(results, ansi.enabled()))
    return 1 if any(r.status == FAIL for r in results) else 0
