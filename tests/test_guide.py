import re
from pathlib import Path

from athanor import cli, guide

BINDS = (Path(__file__).parent.parent / "config/hypr/binds.lua").read_text()


def test_every_key_in_the_guide_is_bound():
    for key, _ in guide.KEYS:
        if "1 - 7" in key:
            assert "for level = 1, 7 do" in BINDS
            if key.startswith("SHIFT"):
                assert 'SHIFT + " .. level' in BINDS
            continue
        for k in re.sub(r"^SHIFT \+ ", "", key).split():
            shifted = key.startswith("SHIFT")
            if len(k) == 1 and k in "HJKL":
                assert f"{k} = " in BINDS
                if shifted:
                    assert 'SHIFT + " .. key' in BINDS
            else:
                assert f'"{"SHIFT + " if shifted else ""}{k}"' in BINDS or (
                    f'mod .. " + {"SHIFT + " if shifted else ""}{k}"' in BINDS
                ), key


def test_every_command_in_the_guide_exists():
    sub = next(a for a in cli.parser()._actions if a.dest == "command")
    for name, _ in guide.COMMANDS:
        assert name in sub.choices, name


def test_moon_notes_are_netHacks():
    assert guide.moon_note("full") == "You are lucky! Full moon tonight."
    assert guide.moon_note("new") == "Be careful! New moon tonight."
    assert guide.moon_note("waxing crescent") is None


def test_guide_renders_without_color():
    text = guide.text(False)
    assert text.splitlines()[0].strip() == guide.TITLE
    assert "\033" not in text
