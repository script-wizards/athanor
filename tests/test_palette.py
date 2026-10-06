import re

import pytest

from athanor import palette

HEX = re.compile(r"#[0-9a-f]{6}")


@pytest.mark.parametrize("name", palette.SCHEMES)
def test_scheme_shape(name):
    s = palette.load(name)
    assert len(s.ansi) == 16
    for color in [*s.roles.values(), *s.ansi, *s.wall_desk, *s.wall_lock]:
        assert HEX.fullmatch(color), color


@pytest.mark.parametrize("name", palette.SCHEMES)
def test_text_contrast(name):
    s = palette.load(name)
    bg = s.roles["bg"]
    assert palette.contrast(s.roles["fg"], bg) >= 7
    assert palette.contrast(s.roles["dim"], bg) >= 4.5
    for slot in (1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14):
        assert palette.contrast(s.ansi[slot], bg) >= 4.5, (name, slot, s.ansi[slot])


@pytest.mark.parametrize("name", palette.SCHEMES)
def test_bar_contrast(name):
    r = palette.load(name).roles
    assert palette.contrast(r["barfg"], r["bar"]) >= 7
    assert palette.contrast(r["bar_warn"], r["bar"]) >= 4.5


def test_cycle_visits_every_scheme():
    seen, name = [], "umber"
    for _ in palette.SCHEMES:
        seen.append(name)
        name = palette.following(name)
    assert sorted(seen) == sorted(palette.SCHEMES)
    assert name == "umber"


def test_unknown_scheme():
    with pytest.raises(KeyError):
        palette.load("rubedo")


def test_every_slot_has_a_pigment():
    assert len(palette.PIGMENTS) == len(palette.ANSI_NAMES)


def test_a_retired_scheme_moves_to_its_successor(tmp_path, monkeypatch):
    from athanor import transmute

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    (tmp_path / "athanor").mkdir()
    (tmp_path / "athanor" / "scheme").write_text("dore\n")
    assert transmute.saved_scheme() == "cinnabar"
