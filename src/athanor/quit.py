import subprocess

from . import hypr
from .paths import current_dir

PROMPT = "Let the athanor go cold? [yn] (n) "
CHOICES = ("n - no, tend the fire", "y - yes, let it go out (quit Hyprland)")


def confirmed(answer: str) -> bool:
    return answer.strip() == "1"


def ask() -> None:
    picked = subprocess.run(
        [
            "fuzzel",
            "--config",
            str(current_dir() / "fuzzel/fuzzel.ini"),
            "--dmenu",
            "--index",
            "--only-match",
            "--lines",
            str(len(CHOICES)),
            "--width",
            str(max(len(c) for c in CHOICES) + len(PROMPT) + 4),
            "--prompt",
            PROMPT,
        ],
        input="\n".join(CHOICES),
        capture_output=True,
        text=True,
        check=False,
    )
    if picked.returncode == 0 and confirmed(picked.stdout):
        hypr.exit_session()
