import re
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

from .paths import write_atomic

TOKEN = re.compile(r"\{\{\s*([a-z][a-z0-9_]*)(?:\.(hex|rgba))?\s*\}\}")
HEX = re.compile(r"#[0-9a-fA-F]{6}")


def render(text: str, tokens: dict[str, str]) -> str:
    def sub(m: re.Match) -> str:
        name, variant = m.group(1), m.group(2)
        if name not in tokens:
            raise KeyError(f"template token {name!r} has no value")
        value = str(tokens[name])
        if variant is None:
            return value
        if not HEX.fullmatch(value):
            raise ValueError(f"token {name!r} is not a color and has no .{variant}")
        return value[1:] if variant == "hex" else value[1:] + "ff"

    return TOKEN.sub(sub, text)


def templates() -> Traversable:
    return files("athanor") / "templates"


def _walk(node: Traversable, prefix: Path = Path()):
    for child in node.iterdir():
        if child.is_dir():
            yield from _walk(child, prefix / child.name)
        else:
            yield prefix / child.name, child


def render_tree(dest: Path, tokens: dict[str, str]) -> list[Path]:
    written = []
    for rel, src in _walk(templates()):
        out = dest / rel
        write_atomic(out, render(src.read_text(), tokens))
        written.append(out)
    return written
