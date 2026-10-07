import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SLOTS = {"default", "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"}
SLOTS |= {f"bright{c}" for c in SLOTS - {"default"}}
STYLES = {"bold", "italic", "underline", "reverse"}


def test_micro_uses_only_terminal_slots():
    for line in (ROOT / "config/micro/colorschemes/athanor.micro").read_text().splitlines():
        if not line.startswith("color-link"):
            continue
        _, group, value = line.split(maxsplit=2)
        for word in re.split(r"[ ,]", value.strip('"')):
            assert word in SLOTS | STYLES or word == "comment", (group, word)


NVIM = ROOT / "config/nvim"
NVIM_SLOTS = {"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", "gray"}
NVIM_SLOTS |= {f"bright_{c}" for c in ("red", "green", "yellow")}


def test_nvim_uses_only_terminal_slots():
    for path in (NVIM / "colors/athanor.lua", NVIM / "lua/lualine/themes/athanor.lua"):
        text = path.read_text()
        assert not re.search(r"#[0-9a-fA-F]{6}", text), path
        assert not re.search(r"\b(guifg|guibg|sp)\s*=", text), path
        for key, value in re.findall(r"\b(ctermfg|ctermbg|fg|bg)\s*=\s*([\w\"]+)", text):
            value = value.strip('"')
            named = value in NVIM_SLOTS | {"NONE", "color"}
            assert named or 0 <= int(value) <= 15, (path.name, key, value)


@pytest.mark.skipif(not shutil.which("nvim"), reason="needs nvim")
def test_nvim_loads_the_colorscheme_without_true_color():
    probe = (
        "lua print(vim.g.colors_name, vim.o.termguicolors,"
        " vim.api.nvim_get_hl(0, {name = '@keyword', link = false}).ctermfg)"
    )
    done = subprocess.run(
        [
            "nvim",
            "--headless",
            "--clean",
            "--cmd",
            f"set rtp^={NVIM}",
            "-c",
            "colorscheme athanor",
            "-c",
            probe,
            "-c",
            "qa!",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert done.stderr.strip().splitlines()[-1] == "athanor false 1", done.stderr
