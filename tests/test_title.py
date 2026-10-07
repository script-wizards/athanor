import shutil
import subprocess
from pathlib import Path

import pytest

ZSHRC = Path(__file__).resolve().parent.parent / "config/zsh/athanor.zsh"

pytestmark = pytest.mark.skipif(not shutil.which("zsh"), reason="needs zsh")


def title(script: str, tmp_path: Path, **env: str) -> str:
    result = subprocess.run(
        ["zsh", "-f", "-c", f"source {ZSHRC}; {script}"],
        capture_output=True,
        check=True,
        cwd=tmp_path,
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin", "TERM": "foot", **env},
        text=True,
    )
    return result.stdout


def command(line: str, tmp_path: Path) -> str:
    return title(f"_athanor_title_command {line!r}", tmp_path)


def test_the_prompt_names_the_folder(tmp_path):
    (tmp_path / "almagest").mkdir()
    assert title("cd almagest; _athanor_title_folder", tmp_path) == "\x1b]2;almagest\a"


def test_home_is_a_tilde(tmp_path):
    assert title("_athanor_title_folder", tmp_path) == "\x1b]2;~\a"


@pytest.mark.parametrize(
    ("line", "shown"),
    [
        ("hx ~/projects/almagest/hours.c", "hx hours.c"),
        ("git commit -m 'bind the seventh hour'", "git commit"),
        ("ls -la", "ls"),
        ("ssh ariel", "ssh ariel"),
        ("make; ls", "make"),
        ("LANG=C sort names | uniq", "sort names"),
        ("/usr/bin/python3 -I", "python3"),
    ],
)
def test_a_running_command_names_itself(tmp_path, line, shown):
    assert command(line, tmp_path) == f"\x1b]2;{shown}\a"


def test_control_characters_are_dropped(tmp_path):
    assert command("echo $'\\e]2;pwned\\a'", tmp_path) == "\x1b]2;echo ]2;pwned\a"


@pytest.mark.parametrize(
    "env", [{"ATHANOR_TITLE": "0"}, {"TMUX": "/tmp/tmux-1000/default,1,0"}, {"TERM": "linux"}]
)
def test_titles_stand_aside(tmp_path, env):
    assert title("_athanor_title_folder; _athanor_title_command ls", tmp_path, **env) == ""


def test_a_script_that_sources_the_prompt_keeps_its_title(tmp_path):
    (tmp_path / "almagest").mkdir()
    script = tmp_path / "staged.zsh"
    script.write_text(f"source {ZSHRC}\ncd {tmp_path}/almagest\n_athanor_title_folder\ntrue\n")
    done = subprocess.run(
        ["zsh", "-f", str(script)],
        capture_output=True,
        check=True,
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin", "TERM": "foot"},
        text=True,
    )
    assert done.stdout == "\x1b]2;almagest\a"
