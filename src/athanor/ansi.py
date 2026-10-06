import os
import sys


def enabled(stream=sys.stdout) -> bool:
    return "NO_COLOR" not in os.environ and stream.isatty()


def paint(text: str, slot: int, on: bool = True) -> str:
    if not on:
        return text
    code = 30 + slot if slot < 8 else 90 + slot - 8
    return f"\033[{code}m{text}\033[0m"
