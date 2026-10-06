import tomllib
from dataclasses import dataclass
from importlib.resources import files

SCHEMES = ("umber", "vellum", "orpiment", "cinnabar")
RETIRED = {"dore": "cinnabar"}
ANSI_NAMES = ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")
PIGMENTS = ("ink", "vermilion", "olive", "ochre", "slate", "madder", "verdigris", "paper")
ROLES = ("bg", "fg", "dim", "border", "active", "bar", "barfg", "bar_warn", "sigil")


@dataclass(frozen=True)
class Scheme:
    name: str
    label: str
    roles: dict[str, str]
    ansi: tuple[str, ...]
    wall_desk: tuple[str, str]
    wall_lock: tuple[str, str]

    def colors(self) -> dict[str, str]:
        return {**self.roles, **{f"a{i}": c for i, c in enumerate(self.ansi)}}


def _table() -> dict:
    return tomllib.loads((files("athanor") / "palette.toml").read_text())


def load(name: str) -> Scheme:
    raw = _table().get(name)
    if raw is None:
        raise KeyError(f"no scheme {name!r}; the schemes are {' '.join(SCHEMES)}")
    return Scheme(
        name=name,
        label=raw["label"],
        roles={role: raw[role] for role in ROLES},
        ansi=tuple(raw["ansi"]),
        wall_desk=tuple(raw["wall_desk"]),
        wall_lock=tuple(raw["wall_lock"]),
    )


def following(name: str) -> str:
    return SCHEMES[(SCHEMES.index(name) + 1) % len(SCHEMES)]


def rgb(hex_color: str) -> tuple[int, int, int]:
    n = int(hex_color.lstrip("#"), 16)
    return n >> 16, (n >> 8) & 255, n & 255


def luminance(hex_color: str) -> float:
    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)
