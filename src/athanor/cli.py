import argparse
import contextlib
import getpass
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from . import (
    ansi,
    config,
    guide,
    hypr,
    inventory,
    palette,
    sigil,
    sky,
    stages,
    status,
    tarot,
    tomb,
    transmute,
    wall,
)
from .paths import cache_dir, runtime_dir, state_dir, write_atomic


def _now() -> datetime:
    return datetime.now().astimezone()


def _size(text: str) -> tuple[int, int]:
    w, _, h = text.lower().partition("x")
    return int(w), int(h)


def _hour_lines(now: datetime, cfg) -> dict[str, str]:
    ph = sky.planetary_hour(now, cfg.place)
    trump = tarot.trump_for(ph.planet)
    approx = "~" if ph.approximate else ""
    day, hour = sky.with_article(ph.day_ruler), sky.with_article(ph.planet)
    seed, _ = sigil.host_digest()
    card = tarot.card_of_day(now.date(), seed)
    return {
        "date": f"{now:%A}, the {sky.ordinal(now.day)} of {now:%B}",
        "ruler": f"Day of {day}, hour of {hour}{approx}",
        "trump": f"The hour's trump: {trump.title}",
        "moon": f"Moon {sky.moon_phase(now)}, {sky.moon_age(now):.0f} days old",
        "card": f"Card of the day: {card.title}",
        "bar": f"{now:%a %-d %b  %H:%M}  Hour of {hour}{approx}  Moon: {sky.moon_trend(now)}",
        "sun": f"Sunrise {ph.sunrise:%H:%M}, sunset {ph.sunset:%H:%M}"
        + ("  (no [place] set; using 6:00 and 18:00)" if ph.approximate else ""),
    }


def _lock_markup(lines: dict[str, str], colors: str) -> str:
    fg, active, dim = (f"#{c.lstrip('#')}" for c in colors.split(","))
    rows = [("date", fg), ("ruler", active), ("moon", dim), ("card", dim)]
    body = "\n".join(
        f'<span foreground="{c}">{html.escape(lines[k], quote=False)}</span>' for k, c in rows
    )
    return f'<span line_height="1.5">{body}</span>'


def cmd_hour(args) -> None:
    cfg = config.load()
    if not (args.waybar or args.follow):
        lines = _hour_lines(_now(), cfg)
        if args.lock:
            print(_lock_markup(lines, args.lock))
            return
        keys = [args.line] if args.line else ["date", "ruler", "trump", "moon", "card"]
        print("\n".join(lines[k] for k in keys))
        return
    while True:
        lines = _hour_lines(_now(), cfg)
        tip = "\n".join(lines[k] for k in ("ruler", "trump", "sun", "moon", "card"))
        print(json.dumps({"text": lines["bar"], "tooltip": tip}), flush=True)
        if not args.follow:
            return
        time.sleep(60.5 - time.time() % 60)


def cmd_inventory(args) -> None:
    if args.list:
        found = inventory.items(hypr.query("clients") or [], hypr.active_workspace())
        print("\n".join(i.text for i in found) or "You are empty handed.")
    else:
        inventory.choose()


def cmd_status(args) -> None:
    if args.waybar:
        status.waybar()
    else:
        print(status.plain(args.short))


def cmd_transmute(args) -> None:
    name = args.scheme
    if args.next or name is None:
        name = palette.following(transmute.saved_scheme())
    size = _size(args.size) if args.size else None
    scheme, walls = transmute.apply(name, reload=not args.no_reload, size=size)
    print(f"You read a scroll of transmutation. {transmute.HUES[scheme.name]}")
    if walls is None:
        print("No plates were drawn because ImageMagick is missing. pacman -S imagemagick")


def cmd_doctor(args) -> None:
    from . import doctor

    sys.exit(doctor.main(as_json=args.json))


def cmd_prerender(_args) -> None:
    transmute.prerender()


def cmd_quit(_args) -> None:
    from . import quit

    quit.ask()


def cmd_wall(args) -> None:
    print(transmute.show_level(args.dlvl))


def cmd_wake(args) -> None:
    transmute.wake(wall=not args.no_wall)


def cmd_stages(args) -> None:
    cfg = config.load()
    if not args.follow:
        scheme = stages.scheme_at(sky.planetary_hour(_now(), cfg.place))
        print(f"The work is in {stages.STAGES[scheme]}: {palette.load(scheme).label}.")
        if not cfg.stages:
            print("Set stages = true under [transmute] to follow it.")
        return
    if not cfg.stages:
        return
    current = stages.scheme_at(sky.planetary_hour(_now(), cfg.place))
    while True:
        time.sleep(60.5 - time.time() % 60)
        scheme = stages.scheme_at(sky.planetary_hour(_now(), cfg.place))
        if scheme != current:
            current = scheme
            transmute.apply(scheme, message=stages.announcement(scheme))


def _sixel_ok() -> bool:
    if os.environ.get("ATHANOR_SIXEL") in ("0", "1"):
        return os.environ["ATHANOR_SIXEL"] == "1"
    return sys.stdout.isatty() and os.environ.get("TERM", "").startswith("foot")


def _art_dir() -> Path:
    return cache_dir() / "tarot"


CARD_HEIGHT = 360


def _caption(draw: tarot.Draw, position: str, color: bool) -> None:
    head = f"{position}: " if position else ""
    print(ansi.paint(head, 8, color) + ansi.paint(draw.title, 15, color))
    print("  " + draw.meaning)


def _show_art(draws: list[tarot.Draw]) -> None:
    cards = [(tarot.art_path(d.card, _art_dir()), d.reversed) for d in draws]
    cards = [(src, rev) for src, rev in cards if src.exists()]
    if not cards:
        return
    scheme = palette.load(transmute.saved_scheme())
    fit = max(1, shutil.get_terminal_size().columns * 8 // (CARD_HEIGHT * 58 // 100 + 16))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            pngs = [
                str(
                    wall.card_image(
                        src, scheme, rev, "png", Path(tmp) / f"{i}.png", height=CARD_HEIGHT
                    )
                )
                for i, (src, rev) in enumerate(cards)
            ]
            sixel = wall.spread_image(pngs, scheme, min(fit, len(pngs)))
        sys.stdout.flush()
        sys.stdout.buffer.write(sixel)
        sys.stdout.write("\n")
    except (wall.MissingTool, OSError, subprocess.CalledProcessError):
        pass


def _show(draw: tarot.Draw, position: str, art: bool, color: bool) -> None:
    _caption(draw, position, color)
    if art:
        _show_art([draw])


def cmd_draw(args) -> None:
    color = ansi.enabled()
    art = not args.no_art and _sixel_ok()
    if args.day or args.png:
        seed, _ = sigil.host_digest()
        today = _now().date()
        draw = tarot.card_of_day(today, seed)
        if args.png:
            out = transmute.card_of_day_png(palette.load(transmute.saved_scheme()))
            if out:
                print(out)
            return
        _show(draw, "", art, color)
        return
    if args.card:
        draws = [tarot.draw_by_name(name) for name in args.card]
        for name, draw in zip(args.card, draws, strict=True):
            if draw is None:
                sys.exit(f"There is no card called {name!r}.")
        n = len(draws)
    else:
        n = args.n
        draws = tarot.spread(n)
    positions = tarot.SPREAD_POSITIONS.get(n) or tuple(str(i + 1) for i in range(n))
    for position, draw in zip(positions, draws, strict=True):
        _caption(draw, position, color)
    if art:
        _show_art(draws)


def cmd_cards(args) -> None:
    if args.action == "fetch":
        fetched = tarot.fetch_art(_art_dir())
        have = sum(tarot.art_path(c, _art_dir()).exists() for c in tarot.DECK)
        head = f"Fetched {fetched}. " if fetched else ""
        print(f"{head}{have} cards in {_art_dir()}.")
    else:
        for card in tarot.DECK:
            print(f"{card.title:<26} {card.upright}")


def cmd_sigil(args) -> None:
    digest, fingerprint = sigil.host_digest()
    cells = sigil.grid(digest)
    if args.png:
        color = palette.load(transmute.saved_scheme()).roles["sigil"]
        write_atomic(Path(args.png), sigil.png(cells, color, args.scale))
        return
    if args.fingerprint:
        print(fingerprint)
        return
    print(sigil.text(cells))
    print(fingerprint)


def _tomb_state() -> Path:
    return state_dir() / "tomb.json"


def cmd_tomb(args) -> None:
    if args.demo:
        print(tomb.stone("firefox", 11, _now().year, dlvl=2))
        return
    crash = tomb.latest()
    try:
        seen = json.loads(_tomb_state().read_text())
    except (OSError, json.JSONDecodeError):
        seen = {}
    if args.notify:
        if crash is None or crash.stamp <= seen.get("stamp", 0):
            return
        dlvl = hypr.active_workspace()
        write_atomic(_tomb_state(), json.dumps({"stamp": crash.stamp, "dlvl": dlvl}))
        if tomb.from_last_session(crash, hypr.session_start()):
            return
        where = f" on Dlvl {dlvl}" if dlvl is not None else ""
        # The process picked its own name and mako parses Pango markup.
        transmute.run(
            "notify-send",
            "-a",
            "athanor",
            "--",
            f"{html.escape(crash.name)} was killed by a {tomb.cause(crash.signal)}{where}.",
        )
        return
    if crash is None:
        print("No one has died here.")
        return
    dlvl = seen.get("dlvl") if seen.get("stamp") == crash.stamp else None
    print(tomb.stone(crash.name, crash.signal, crash.when.year, dlvl))


def cmd_room(args) -> None:
    from . import room

    cfg = config.load()
    if args.once:
        marker = runtime_dir() / "athanor-room"
        if marker.exists():
            return
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    color = ansi.enabled()
    greeted = state_dir() / "greeted"
    if args.once and not greeted.exists():
        print(guide.greeting(cfg.name or getpass.getuser(), cfg.title) + "\n")
        write_atomic(greeted, "")
    card = None
    if cfg.tarot_on_login:
        seed, _ = sigil.host_digest()
        card = tarot.card_of_day(_now().date(), seed).title
    print(room.room(cfg, card, color))
    note = guide.moon_note(sky.moon_phase(_now()))
    if note:
        print(ansi.paint(note, 3, color))


def cmd_guide(_args) -> None:
    text = guide.text(ansi.enabled())
    if sys.stdout.isatty() and len(text.splitlines()) >= shutil.get_terminal_size().lines:
        pager = os.environ.get("PAGER") or "less"
        if shutil.which(pager.split()[0]):
            subprocess.run(
                [*pager.split(), "-R"] if pager == "less" else pager.split(),
                input=text,
                text=True,
                check=False,
            )
            return
    print(text)


def cmd_sheet(_args) -> None:
    from . import room

    print(room.sheet(config.load(), ansi.enabled()))


def cmd_font(_args) -> None:
    face = config.TERMINAL_FONTS[config.load().terminal_font]
    bold = f", with {face.bold} for bold" if face.bold else ""
    print(f"{face.family} at {face.px}px ({face.px * 72 / 96:g}pt at 96 dpi){bold}")


def cmd_palette(args) -> None:
    scheme = palette.load(args.scheme or transmute.saved_scheme())
    print(scheme.label)
    for i, c in enumerate(scheme.ansi):
        r, g, b = palette.rgb(c)
        name = ("br " if i > 7 else "") + palette.ANSI_NAMES[i % 8]
        pigment = palette.PIGMENTS[i % 8]
        print(f"\033[48;2;{r};{g};{b}m      \033[0m {i:>2} {pigment:<10} {name:<11} {c}")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="athanor", description="An alchemical layer for Arch and Hyprland."
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("transmute", help="switch color scheme")
    s.add_argument("scheme", nargs="?", choices=palette.SCHEMES)
    s.add_argument("--next", action="store_true", help="switch to the next scheme")
    s.add_argument("--no-reload", action="store_true", help="render without reloading anything")
    s.add_argument("--size", metavar="WxH", help="screen size")
    s.set_defaults(fn=cmd_transmute)

    s = sub.add_parser("doctor", help="check the install")
    s.add_argument("--json", action="store_true", help="print JSON")
    s.set_defaults(fn=cmd_doctor)

    s = sub.add_parser("prerender", help="render the wallpapers for every scheme")
    s.set_defaults(fn=cmd_prerender)

    s = sub.add_parser("quit", help="ask, then quit Hyprland")
    s.set_defaults(fn=cmd_quit)

    s = sub.add_parser("wall", help="set the wallpaper for a workspace")
    s.add_argument("dlvl", nargs="?", type=int, help="workspace number (default: current)")
    s.set_defaults(fn=cmd_wall)

    s = sub.add_parser("wake", help="render and set the wallpaper at login")
    s.add_argument("--no-wall", action="store_true", help="skip the wallpaper")
    s.set_defaults(fn=cmd_wake)

    s = sub.add_parser("stages", help="show the stage for this hour")
    s.add_argument("--follow", action="store_true", help="keep switching schemes with the stages")
    s.set_defaults(fn=cmd_stages)

    s = sub.add_parser("windows", help="pick an open window")
    s.add_argument("--list", action="store_true", help="print the list instead")
    s.set_defaults(fn=cmd_inventory)

    s = sub.add_parser("status", help="print the status line")
    s.add_argument("--waybar", action="store_true", help="JSON for Waybar")
    s.add_argument("--short", action="store_true", help="only Hp and T")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("hour", help="show the planetary hour, the moon and the card of the day")
    s.add_argument("--line", choices=("date", "ruler", "trump", "moon", "card", "bar", "sun"))
    s.add_argument("--lock", metavar="FG,ACTIVE,DIM", help="Pango markup for hyprlock")
    s.add_argument("--waybar", action="store_true", help="JSON for Waybar")
    s.add_argument("--follow", action="store_true", help="print again every minute")
    s.set_defaults(fn=cmd_hour)

    s = sub.add_parser("draw", help="draw tarot cards")
    s.add_argument(
        "n",
        nargs="?",
        type=int,
        default=1,
        choices=range(1, 11),
        metavar="N",
        help="how many, 1 to 10",
    )
    s.add_argument("--day", action="store_true", help="show the card of the day")
    s.add_argument(
        "--card",
        action="append",
        help='pick a card by name, like "the magician, reversed" (repeatable)',
    )
    s.add_argument("--png", action="store_true", help="render today's card and print its path")
    s.add_argument("--no-art", action="store_true", help="text only")
    s.set_defaults(fn=cmd_draw)

    s = sub.add_parser("cards", help="list the deck, or fetch the card images")
    s.add_argument("action", nargs="?", choices=("list", "fetch"), default="list")
    s.set_defaults(fn=cmd_cards)

    s = sub.add_parser("sigil", help="show this machine's sigil")
    s.add_argument("--png", metavar="PATH", help="write it as a PNG")
    s.add_argument("--scale", type=int, default=8, help="pixels per cell")
    s.add_argument("--fingerprint", action="store_true", help="print only the host key fingerprint")
    s.set_defaults(fn=cmd_sigil)

    s = sub.add_parser("tomb", help="show the last crash")
    s.add_argument(
        "--notify", action="store_true", help="send a notification if there is a new crash"
    )
    s.add_argument("--demo", action="store_true", help="show a sample tombstone")
    s.set_defaults(fn=cmd_tomb)

    s = sub.add_parser("guide", help="explain the screen, keys and commands")
    s.set_defaults(fn=cmd_guide)

    s = sub.add_parser("room", help="describe the room")
    s.add_argument("--once", action="store_true", help="only once per boot")
    s.set_defaults(fn=cmd_room)

    s = sub.add_parser("sheet", help="show the character sheet")
    s.set_defaults(fn=cmd_sheet)

    s = sub.add_parser("font", help="print the terminal font and size")
    s.set_defaults(fn=cmd_font)

    s = sub.add_parser("palette", help="print a scheme's colors")
    s.add_argument("scheme", nargs="?", choices=palette.SCHEMES)
    s.set_defaults(fn=cmd_palette)
    return p


def main(argv: list[str] | None = None) -> None:
    args = parser().parse_args(argv)
    with contextlib.suppress(BrokenPipeError, KeyboardInterrupt):
        args.fn(args)
