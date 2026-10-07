import tomllib
from dataclasses import dataclass, field
from typing import NamedTuple

from .paths import config_dir

DEFAULT_ROOM = "Dust hangs in the lamplight. A terminal hums on the desk."


class TerminalFont(NamedTuple):
    family: str
    px: int
    # foot puts bold on the regular face's baseline, so a taller bold face gets
    # its tops clipped.
    bold: str | None = None
    italic: str | None = None


TERMINAL_FONTS = {
    "tandy": TerminalFont("Px437 Tandy2K", 16, bold="Px437 AT&T PC6300", italic="Ttyp0"),
    "terminus": TerminalFont("Terminus (TTF)", 16, italic="Ttyp0"),
    "cozette": TerminalFont("CozetteVector", 13),
    "compaq": TerminalFont("Px437 CompaqThin 8x16", 16, bold="Px437 CompaqThin Overstrike"),
    "vga": TerminalFont("PxPlus IBM VGA 8x16", 16, bold="PxPlus IBM VGA Overstrike"),
}


@dataclass(frozen=True)
class Config:
    place: tuple[float, float] | None = None
    name: str = ""
    title: str = "the Wizard"
    race: str = ""
    room_name: str = "A Dim Chamber"
    room_description: str = DEFAULT_ROOM
    exits: dict[str, str] = field(default_factory=dict)
    pixel_scale: int = 0
    levels: bool = True
    terminal_font: str = "tandy"
    tarot_on_login: bool = True
    stages: bool = False


def load() -> Config:
    path = config_dir() / "athanor.toml"
    try:
        raw = tomllib.loads(path.read_text())
    except FileNotFoundError:
        return Config()
    place = raw.get("place", {})
    room = raw.get("room", {})
    character = raw.get("character", {})
    lat, lon = place.get("latitude"), place.get("longitude")
    display = raw.get("display", {})
    font = str(display.get("terminal_font", Config.terminal_font)).lower()
    if font not in TERMINAL_FONTS:
        font = Config.terminal_font
    return Config(
        place=(float(lat), float(lon)) if lat is not None and lon is not None else None,
        name=str(character.get("name", "")),
        title=character.get("title", Config.title),
        race=str(character.get("race", "")),
        room_name=room.get("name", Config.room_name),
        room_description=room.get("description", DEFAULT_ROOM),
        exits=dict(room.get("exits", {})),
        pixel_scale=int(display.get("pixel_scale", 0)),
        levels=bool(display.get("levels", True)),
        terminal_font=font,
        tarot_on_login=bool(raw.get("tarot", {}).get("on_login", True)),
        stages=bool(raw.get("transmute", {}).get("stages", False)),
    )
