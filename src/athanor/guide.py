from . import macos
from .ansi import paint

TITLE = "The Athanor Guidebook"

STATUS = (
    ("Dlvl:3", "Dungeon level: which of the seven workspaces you're on."),
    ("$:212G", "Gold: free disk space."),
    ("Hp:87(96)", "Hit points: battery charge. The max is the battery's health."),
    ("", "A + means it is charging. Hp:AC means there is no battery."),
    ("Str:14%", "Strength spent: how hard the CPU is working."),
    ("Mem:6.1G", "Memory in use."),
    ("T:48213", "Turns: minutes since boot."),
    ("Sick", "A new kernel waits. Reboot to load its modules."),
    ("Hour of Venus", "The planetary hour for your sunrise and sunset."),
    ("Moon: waning", "The moon's phase."),
)

SYMBOLS = (
    ("@", "You, at the prompt. It goes red when the last command failed."),
    ("--More--", "More messages are waiting."),
    ("~", "The reading is a guess. Set [place] in athanor.toml."),
    ("(wielded)", "In the window list, the window you are using."),
)

KEYS = (
    ("Return", "open a terminal"),
    ("Space", "open the launcher"),
    ("Tab", "pick from your open windows"),
    ("1 - 7", "go to that dungeon level"),
    ("SHIFT + 1 - 7", "carry the window there"),
    ("H J K L", "look that way (the arrows work too)"),
    ("SHIFT + H J K L", "move the window that way"),
    ("Q", "close the window"),
    ("F", "toggle fullscreen"),
    ("V", "float the window"),
    ("T", "read a scroll of transmutation"),
    ("Escape", "lock the screen"),
    ("SHIFT + E", "let the athanor go cold (asks first)"),
)

COMMANDS = (
    ("guide", "this Guidebook"),
    ("doctor", "check the install"),
    ("room", "look around"),
    ("sheet", "your character sheet"),
    ("hour", "the planetary hour, the moon and the card of the day"),
    ("draw", "draw tarot cards (draw 3 lays a spread)"),
    ("cards", "list the deck, or fetch the card images"),
    ("status", "the status line"),
    ("windows", "pick an open window"),
    ("transmute", "change the scheme"),
    ("palette", "the scheme's colors and their pigments"),
    ("stages", "the stage for this hour"),
    ("tomb", "the last crash"),
    ("sigil", "this machine's sigil"),
    ("font", "the terminal font and size"),
)


def _rows(rows, width: int, color: bool) -> list[str]:
    return [f"  {paint(left.ljust(width), 15, color)}  {right}" for left, right in rows]


def text(color: bool) -> str:
    out = [paint(TITLE.center(72).rstrip(), 3, color), ""]
    out += [paint("The status line (athanor status):", 8, color)]
    rows = STATUS
    if macos.available():
        rows = (
            ("Dlvl:?", "macOS Spaces are not mapped to dungeon levels."),
            *STATUS[1:7],
            *STATUS[8:],
        )
    out += _rows(rows, 13, color)
    out += ["", paint("Symbols:", 8, color)]
    out += _rows(SYMBOLS, 13, color)
    if macos.available():
        out += [
            "",
            "Terminal.app: import a profile from ~/.config/athanor/current/terminal.",
            "Kitty: include ~/.config/athanor/current/kitty/colors.conf in kitty.conf.",
            "transmute updates compatible terminals; Terminal.app uses its imported profile.",
            "wall N sets a dungeon plate as the wallpaper on your desktops.",
        ]
    else:
        out += ["", paint("Hold Super (the Windows key) and press:", 8, color)]
        out += _rows(KEYS, 15, color)
    out += ["", paint("At the prompt, type athanor and one of:", 8, color)]
    commands = COMMANDS
    if macos.available():
        commands = tuple(row for row in COMMANDS if row[0] != "windows")
    out += _rows(commands, 13, color)
    out += ["", "Nothing is renamed. ls is still ls."]
    return "\n".join(out)


def greeting(user: str, title: str) -> str:
    return (
        f"Hello {user}, welcome to Athanor! You are {title}.\nFor instructions type: athanor guide"
    )


def moon_note(phase: str) -> str | None:
    if phase == "full":
        return "You are lucky! Full moon tonight."
    if phase == "new":
        return "Be careful! New moon tonight."
    return None
