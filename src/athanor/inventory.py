import contextlib
import functools
import os
import string
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import hypr
from .paths import current_dir
from .tomb import clean

LETTERS = string.ascii_lowercase + string.ascii_uppercase
TITLE_WIDTH = 40


@dataclass(frozen=True)
class Item:
    letter: str
    text: str
    address: str


def _app_dirs() -> list[Path]:
    data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
    data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    return [Path(d) / "applications" for d in [data_home, *data_dirs.split(":")] if d]


# Order matters: a PDF viewer is Office;Viewer and should be a book.
ITEMS = (
    ("TerminalEmulator", "terminal"),
    ("WebBrowser", "browser"),
    ("Email", "letter"),
    ("InstantMessaging", "raven"),
    ("Chat", "raven"),
    ("IDE", "quill"),
    ("TextEditor", "quill"),
    ("WordProcessor", "scroll"),
    ("Spreadsheet", "ledger"),
    ("Calculator", "abacus"),
    ("FileManager", "chest"),
    ("Maps", "map"),
    ("Game", "game"),
    ("Monitor", "monitor"),
    ("RasterGraphics", "canvas"),
    ("VectorGraphics", "canvas"),
    ("Photography", "canvas"),
    ("AudioVideo", "player"),
    ("Player", "player"),
    ("Viewer", "viewer"),
)
JOURNALS = frozenset({"obsidian", "logseq", "joplin", "zettlr", "anytype", "notesnook"})
BOOKS = ("Office", "Viewer")


@functools.cache
def _desktop_entries() -> dict[str, tuple[str, frozenset[str]]]:
    entries: dict[str, tuple[str, frozenset[str]]] = {}
    for d in reversed(_app_dirs()):
        for entry in sorted(d.glob("*.desktop")) if d.is_dir() else ():
            fields: dict[str, str] = {}
            with contextlib.suppress(OSError, UnicodeDecodeError):
                for line in entry.read_text().splitlines():
                    if line.startswith("[") and line.strip() != "[Desktop Entry]":
                        break
                    key, sep, value = line.partition("=")
                    if sep and key in ("Name", "GenericName", "StartupWMClass", "Categories"):
                        fields.setdefault(key, value.strip())
            name = fields.get("GenericName") or fields.get("Name")
            if not name:
                continue
            cats = frozenset(c for c in fields.get("Categories", "").split(";") if c)
            for key in (entry.stem, fields.get("StartupWMClass", "")):
                if key:
                    entries[key.lower()] = (name, cats)
    return entries


def item(window_class: str) -> str:
    if not window_class:
        return "thing"
    short = window_class.rsplit(".", 1)[-1].lower()  # md.obsidian.Obsidian
    if short in JOURNALS:
        return "journal"
    found = _desktop_entries().get(window_class.lower())
    if found is None:
        return clean(short)
    name, cats = found
    if all(c in cats for c in BOOKS):
        return "book"
    for category, noun in ITEMS:
        if category in cats:
            return noun
    return clean(name.lower())


def _noun(window_class: str) -> str:
    name = item(window_class)
    return f"{'an' if name[0] in 'aeiou' else 'a'} {name}"


def _title(title: str) -> str:
    title = clean(title)
    return title if len(title) <= TITLE_WIDTH else title[: TITLE_WIDTH - 1] + "…"


def items(clients: list[dict], active_workspace: int | None) -> list[Item]:
    shown = [c for c in clients if c.get("mapped", True) and not c.get("hidden", False)]
    shown.sort(key=lambda c: c.get("focusHistoryID", len(clients)))
    out = []
    for letter, c in zip(LETTERS, shown, strict=False):
        text = f"{letter} - {_noun(c.get('class', ''))}"
        if c.get("title") and c["title"] != c.get("class"):
            text += f' called "{_title(c["title"])}"'
        workspace = c.get("workspace", {}).get("id")
        if c.get("focusHistoryID") == 0:
            text += " (wielded)"
        elif workspace is not None and workspace != active_workspace:
            text += f" (on Dlvl {workspace})"
        out.append(Item(letter, text, c["address"]))
    return out


def prompt(found: list[Item]) -> str:
    span = found[0].letter if len(found) == 1 else f"{found[0].letter}-{found[-1].letter}"
    return f"What do you want to use? [{span}] "


def choose() -> None:
    found = items(hypr.query("clients") or [], hypr.active_workspace())
    if not found:
        subprocess.run(["notify-send", "-a", "athanor", "You are empty handed."], check=False)
        return
    picked = subprocess.run(
        [
            "fuzzel",
            "--config",
            str(current_dir() / "fuzzel/fuzzel.ini"),
            "--dmenu",
            "--index",
            "--only-match",
            # fuzzel's default 48 columns cut off "(on Dlvl 2)".
            "--width",
            str(max(len(i.text) for i in found) + 4),
            "--prompt",
            prompt(found),
        ],
        input="\n".join(i.text for i in found),
        capture_output=True,
        text=True,
        check=False,
    )
    if picked.returncode != 0 or not picked.stdout.strip().isdigit():
        return
    index = int(picked.stdout)
    if index < len(found):
        hypr.focus_window(found[index].address)
