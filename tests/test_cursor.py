import struct

import pytest

from athanor import cursor, palette

ALL = list(cursor.cursors())


def parse(data: bytes) -> list[dict]:
    magic, header, version, n = struct.unpack_from("<4sIII", data, 0)
    assert (magic, header, version) == (b"Xcur", 16, 0x10000)
    images = []
    for i in range(n):
        kind, nominal, pos = struct.unpack_from("<III", data, 16 + 12 * i)
        size, ckind, cnominal, _, w, h, xhot, yhot, _ = struct.unpack_from("<9I", data, pos)
        assert (size, ckind, cnominal) == (36, kind, nominal)
        px = struct.unpack_from(f"<{w * h}I", data, pos + 36)
        images.append({"nominal": nominal, "w": w, "h": h, "hot": (xhot, yhot), "px": px})
    return images


@pytest.mark.parametrize("name", ALL)
def test_the_art_fits_and_clicks_on_itself(name):
    c = cursor.cursors()[name]
    assert set("".join(c.rows)) <= {"#", ".", " "}
    for size, scale in cursor.SIZES:
        assert len(c.rows) * scale <= size and len(c.rows[0]) * scale <= size
    x, y = c.hot
    assert c.rows[y][x] != " ", "the hotspot is on the drawing"


def test_the_set_covers_what_programs_ask_for():
    names = {n for c in cursor.cursors().values() for n in (c.name, *c.names)}
    wanted = {
        "default", "pointer", "text", "wait", "progress", "not-allowed", "crosshair", "move",
        "ew-resize", "ns-resize", "nwse-resize", "nesw-resize", "col-resize", "row-resize",
        "n-resize", "s-resize", "e-resize", "w-resize",
        "ne-resize", "nw-resize", "se-resize", "sw-resize", "left_ptr",
    }  # fmt: skip
    assert wanted <= names
    every = [n for c in cursor.cursors().values() for n in (c.name, *c.names)]
    assert len(every) == len(set(every)), "no name is claimed twice"


def test_every_size_is_the_same_drawing_scaled():
    c = cursor.cursors()["text"]
    images = [(n, cursor.image(c.rows, "#000000", "#ffffff", n, s)) for n, s in cursor.SIZES]
    small, big = parse(cursor.xcursor(images, c.hot))
    assert (small["w"], big["w"]) == (24, 48)
    assert big["hot"] == (2 * small["hot"][0], 2 * small["hot"][1]) == (2 * c.hot[0], 2 * c.hot[1])
    for y in range(24):
        for x in range(24):
            assert big["px"][(2 * y) * 48 + 2 * x] == small["px"][y * 24 + x]


@pytest.mark.parametrize("name", palette.SCHEMES)
def test_each_scheme_draws_them_in_its_own_colors(tmp_path, name):
    scheme = palette.load(name)
    root = cursor.render(scheme, tmp_path / "athanor")
    bg, fg = (int(scheme.roles[k].lstrip("#"), 16) | 0xFF000000 for k in ("bg", "fg"))
    for c in ALL:
        small = parse((root / "cursors" / c).read_bytes())[0]
        assert {p for p in small["px"] if p} == {bg, fg}


def test_the_theme_links_every_name_and_inherits_the_rest(tmp_path):
    root = cursor.render(palette.load("umber"), tmp_path / "athanor")
    assert "Inherits=Adwaita" in (root / "index.theme").read_text()
    for c in cursor.cursors().values():
        for alias in c.names:
            assert (root / "cursors" / alias).resolve() == (root / "cursors" / c.name).resolve()
    cursor.render(palette.load("vellum"), root)


def test_hyprland_is_left_alone_when_another_theme_is_in_use(monkeypatch):
    calls = []
    monkeypatch.setattr(cursor.subprocess, "run", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(cursor.shutil, "which", lambda _: "/usr/bin/hyprctl")
    monkeypatch.setenv("XCURSOR_THEME", "Bibata")
    cursor.show()
    assert calls == []
    monkeypatch.setenv("XCURSOR_THEME", "athanor")
    cursor.show()
    assert [c[0][2] for c in calls] == ["Adwaita", "athanor"]
