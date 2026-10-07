import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.sh"
EVERYTHING = (
    "zsh uv imagemagick curl unzip fontconfig hyprland hyprlock hypridle waybar mako fuzzel"
    " perl foot swaybg libnotify grim slurp wl-clipboard"
)

STUBS = {
    "sudo": 'echo "sudo $*" >> "$LOG"',
    "pacman": """[[ $1 == -Q ]] && { [[ " $INSTALLED " == *" $2 "* ]]; exit; }
echo "pacman $*" >> "$LOG\"""",
    "systemctl": 'echo "systemctl $*" >> "$LOG"',
    "fc-cache": "true",
    "tar": "true",
    "perl": "true",
    "curl": 'while [[ $# -gt 0 ]]; do [[ $1 == -o ]] && { touch "$2"; shift; }; shift; done',
    "unzip": """args=("$@"); d=${args[-1]}
for a in "${args[@]}"; do [[ $a == *.ttf ]] && touch "$d/$(basename "$a")"; done""",
    "uv": """echo "uv $*" >> "$LOG"
case "$1 $2" in
  "tool install") mkdir -p "$HOME/.local/bin"
    printf '#!/bin/bash\\necho "athanor $*" >> "$LOG"\\n' > "$HOME/.local/bin/athanor"
    chmod +x "$HOME/.local/bin/athanor" ;;
  "tool list") [[ -x $HOME/.local/bin/athanor ]] && echo "athanor v0.1.0" ;;
  "tool uninstall") rm -f "$HOME/.local/bin/athanor" ;;
esac""",
    "make": """echo "make $*" >> "$LOG"
for a in "$@"; do [[ $a == OUT=* ]] && touch "${a#OUT=}"; done""",
    "chezmoi": """[[ $1 == source-path && -n $MANAGED && $2 == "$MANAGED" ]] || exit 1
echo "$HOME/.local/share/chezmoi/dot_zshrc\"""",
}


@pytest.fixture
def system(tmp_path):
    bin_dir = tmp_path / "stub"
    bin_dir.mkdir()
    for name, body in STUBS.items():
        path = bin_dir / name
        tail = "" if name == "pacman" else "exit 0\n"
        path.write_text(f"#!/usr/bin/env bash\n{body}\n{tail}")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    zsh = shutil.which("zsh")
    if zsh:
        (bin_dir / "zsh").symlink_to(zsh)
    return bin_dir


class Home:
    def __init__(self, path: Path, stubs: Path):
        self.path, self.stubs = path, stubs
        self.log = path / "log"
        path.mkdir()

    def run(self, *args: str, managed: str = "", installed: str = EVERYTHING) -> str:
        env = {
            "HOME": str(self.path),
            "PATH": f"{self.stubs}:/usr/bin:/bin",
            "LOG": str(self.log),
            "SHELL": "/usr/bin/zsh",
            "INSTALLED": installed,
            "MANAGED": managed,
        }
        done = subprocess.run(
            ["bash", str(INSTALL), *args], env=env, capture_output=True, text=True, timeout=60
        )
        assert done.returncode == 0, done.stdout + done.stderr
        return done.stdout + done.stderr

    def __truediv__(self, rel: str) -> Path:
        return self.path / rel

    def write(self, rel: str, text: str, mode: int = 0o644) -> bytes:
        path = self / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(mode)
        return path.read_bytes()

    def files(self) -> set[str]:
        return {
            p.relative_to(self.path).as_posix()
            for p in self.path.rglob("*")
            if (p.is_file() or p.is_symlink()) and p.name != "log"
        }


@pytest.fixture
def home(tmp_path, system):
    return Home(tmp_path / "home", system)


def test_shell_layer_in_a_fresh_home(home):
    home.run("shell")
    assert (home / ".zshrc").read_text().startswith("# >>> athanor >>>\n")
    for rel in (
        ".config/athanor/athanor.zsh",
        ".config/helix/themes/athanor.toml",
        ".config/micro/colorschemes/athanor.micro",
        ".config/nvim/colors/athanor.lua",
        ".config/nvim/lua/lualine/themes/athanor.lua",
        ".config/fontconfig/conf.d/60-athanor.conf",
    ):
        link = home / rel
        assert link.is_symlink() and Path(os.readlink(link)).is_relative_to(ROOT), rel
    assert (home / ".config/athanor/athanor.toml").is_file()
    assert (home / ".local/share/fonts/athanor/Px437_Tandy2K.ttf").exists()
    assert (home / ".local/share/fonts/athanor/t0-16i-uni.bdf").exists()
    assert not (home / ".config/hypr").exists()
    assert "pacman -S --needed" not in home.log.read_text()


def test_only_missing_packages_are_installed_and_nothing_is_upgraded(home):
    home.run("shell", installed="zsh uv curl unzip fontconfig perl")
    log = home.log.read_text()
    assert "sudo pacman -S --needed imagemagick\n" in log
    assert "-Syu" not in log and "-Sy " not in log


def test_running_twice_changes_nothing(home):
    home.run()
    first = {rel: (home / rel).read_bytes() for rel in (".zshrc", ".config/hypr/hyprland.lua")}
    home.run()
    for rel, data in first.items():
        assert (home / rel).read_bytes() == data, rel


@pytest.mark.skipif(not shutil.which("zsh"), reason="ZDOTDIR is found by asking zsh")
def test_zdotdir_and_own_lua_config_are_restored_byte_for_byte(home):
    home.write(".zshenv", "export ZDOTDIR=$HOME/.config/zsh\n")
    zshrc = home.write(".config/zsh/.zshrc", 'eval "$(starship init zsh)"\n', 0o600)
    lua = home.write(
        ".config/hypr/hyprland.lua",
        'hl.on("hyprland.start", function() hl.exec_cmd("waybar") end)\n',
    )
    out = home.run()
    assert (home / ".config/zsh/.zshrc").read_text().startswith("# >>> athanor >>>\n")
    assert not (home / ".zshrc").exists()
    assert 'require(athanor .. "athanor")' in (home / ".config/hypr/hyprland.lua").read_text()
    assert 'require(athanor .. "binds")' not in (home / ".config/hypr/hyprland.lua").read_text()
    assert "you'll get two" in out
    home.run("--uninstall")
    assert (home / ".config/zsh/.zshrc").read_bytes() == zshrc
    assert stat.S_IMODE((home / ".config/zsh/.zshrc").stat().st_mode) == 0o600
    assert (home / ".config/hypr/hyprland.lua").read_bytes() == lua


def test_a_fresh_desktop_gets_a_lua_config_with_bindings(home):
    home.run("desktop")
    lua = (home / ".config/hypr/hyprland.lua").read_text()
    assert lua.startswith("-- >>> athanor >>>\n") and lua.rstrip().endswith("-- <<< athanor <<<")
    assert 'require(athanor .. "binds")' in lua
    assert not (home / ".config/hypr/hyprland.conf").exists()
    assert "systemctl --user enable --now athanor-tomb.path" in home.log.read_text()


def test_athanors_own_hyprland_conf_moves_to_lua_and_stays(home):
    home.write(
        ".config/hypr/hyprland.conf",
        "# >>> athanor >>>\nsource = ~/.config/athanor/hypr/athanor.conf\n"
        "source = ~/.config/athanor/hypr/binds.conf\n# <<< athanor <<<\n",
    )
    home.run("desktop")
    assert 'require(athanor .. "binds")' in (home / ".config/hypr/hyprland.lua").read_text()
    assert (home / ".config/hypr/hyprland.conf").exists()
    home.run("--uninstall")
    assert not (home / ".config/hypr").exists() or not any((home / ".config/hypr").iterdir())


def test_a_users_hyprland_conf_still_works_with_a_warning(home):
    conf = home.write(".config/hypr/hyprland.conf", "$mod = SUPER\nexec-once = waybar\n")
    out = home.run("desktop")
    assert "retiring" in out
    text = (home / ".config/hypr/hyprland.conf").read_text()
    assert text.startswith("# >>> athanor >>>\nsource = ~/.config/athanor/hypr/athanor.conf\n")
    assert "binds.conf" not in text
    home.run("--uninstall")
    assert (home / ".config/hypr/hyprland.conf").read_bytes() == conf


def test_a_chezmoi_managed_zshrc_is_left_alone(home):
    zshrc = home.write(".zshrc", "x=1\n")
    out = home.run("shell", managed=str(home / ".zshrc"))
    assert (home / ".zshrc").read_bytes() == zshrc
    assert "chezmoi manages it" in out and "source ~/.config/athanor/athanor.zsh" in out


def test_a_symlinked_zshrc_is_left_alone(home, tmp_path):
    target = tmp_path / "dotfiles-zshrc"
    target.write_text("x=1\n")
    (home / ".zshrc").symlink_to(target)
    out = home.run("shell")
    assert target.read_text() == "x=1\n"
    assert "it is a symlink" in out


def test_files_that_arent_athanors_are_never_replaced(home):
    theme = home.write(".config/helix/themes/athanor.toml", "# mine\n")
    out = home.run("shell")
    assert (home / ".config/helix/themes/athanor.toml").read_bytes() == theme
    assert "isn't Athanor's. Leaving it alone." in out


def test_uninstall_leaves_nothing_but_settings_and_purge_takes_those(home):
    home.run()
    home.write(".local/share/icons/athanor/cursors/default", "drawn by transmute")
    home.run("--uninstall")
    fonts = home / ".local/share/fonts/athanor"
    kept = {".config/athanor/athanor.toml"}
    kept |= {f".local/share/fonts/athanor/{name}" for name in os.listdir(fonts)}
    assert home.files() == kept
    home.run("--uninstall", "--purge")
    assert home.files() == set()


def test_uninstall_cleans_up_after_the_first_installer(home):
    (home / ".config/hypr").mkdir(parents=True)
    (home / ".config/hypr/hyprland.conf").symlink_to(ROOT / "config/hypr/athanor.conf")
    home.write(".config/hypr/hyprland.conf.athanor-bak.20261004-120000", "mine\n")
    (home / ".config/mako").mkdir()
    (home / ".config/mako/config").symlink_to("/elsewhere")
    out = home.run("--uninstall")
    assert not (home / ".config/hypr/hyprland.conf").exists()
    assert "hyprland.conf.athanor-bak.20261004-120000" in out
    assert os.readlink(home / ".config/mako/config") == "/elsewhere"


def test_dry_run_touches_nothing(home):
    home.write(".zshrc", "x=1\n")
    out = home.run("--dry-run")
    assert home.files() == {".zshrc"}
    assert "sudo" not in (home.log.read_text() if home.log.exists() else "")
    assert "adding the Athanor block" in out


def test_the_notch_is_built_only_when_asked_for(home):
    home.run()
    notch = home / ".local/share/athanor/athanor-notch.so"
    assert not notch.exists()
    out = home.run("notch", installed=EVERYTHING + " gcc make pkgconf")
    assert notch.is_file() and not notch.with_name("athanor-notch.so.new").exists()
    assert f"make -s -C {ROOT}/plugin" in home.log.read_text()
    assert f"hyprctl plugin load {notch}" in out


def test_the_notch_brings_the_desktop_and_its_compiler(home):
    home.run("notch")
    assert (home / ".config/hypr/hyprland.lua").exists()
    assert "gcc make pkgconf" in home.log.read_text()


def test_uninstall_takes_the_notch(home):
    home.run("notch")
    home.run("--uninstall")
    assert not (home / ".local/share/athanor").exists()


def test_vga_and_compaq_get_an_overstrike_bold_once(home):
    home.run("shell")
    log = home.log.read_text()
    assert log.count("tools/overstrike.py") == 2
    assert "PxPlus IBM VGA Overstrike" in log and "Px437 CompaqThin Overstrike" in log
    for name in ("PxPlus_IBM_VGA_8x16-Overstrike.ttf", "Px437_CompaqThin_8x16-Overstrike.ttf"):
        (home / f".local/share/fonts/athanor/{name}").touch()
    home.run("shell")
    assert home.log.read_text().count("tools/overstrike.py") == 2
