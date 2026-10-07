from pathlib import Path
from types import SimpleNamespace

import pytest

from athanor import palette, render, transmute


def test_variants():
    toks = {"bg": "#16120e", "w": "1920"}
    assert (
        render.render("{{ bg }} {{bg.hex}} {{ bg.rgba }} {{ w }}", toks)
        == "#16120e 16120e 16120eff 1920"
    )


def test_unknown_token_is_an_error():
    with pytest.raises(KeyError):
        render.render("{{ nope }}", {})


def test_variant_on_non_color_is_an_error():
    with pytest.raises(ValueError):
        render.render("{{ w.hex }}", {"w": "1920"})


@pytest.mark.parametrize("name", palette.SCHEMES)
def test_every_template_renders(tmp_path, name):
    scheme = palette.load(name)
    toks = transmute.tokens(scheme, (1920, 1080), None, tmp_path / "sigil.png", "SHA256:x")
    written = render.render_tree(tmp_path / "out", toks)
    assert {p.relative_to(tmp_path / "out").as_posix() for p in written} >= {
        "hypr/colors.conf",
        "hypr/hyprlock.conf",
        "waybar/style.css",
        "mako/config",
        "fuzzel/fuzzel.ini",
        "foot/colors.ini",
        "foot/foot.ini",
        "hypr/colors.lua",
    }
    for path in written:
        text = path.read_text()
        assert "{{" not in text and "}}" not in text, path
    assert f"background={scheme.roles['bg'][1:]}" in (tmp_path / "out/foot/colors.ini").read_text()


def test_terminal_font_reaches_foot(tmp_path):
    scheme = palette.load("umber")
    toks = transmute.tokens(scheme, (1920, 1080), None, tmp_path / "s.png", "x", "compaq")
    render.render_tree(tmp_path / "out", toks)
    foot = (tmp_path / "out/foot/foot.ini").read_text()
    assert "font=Px437 CompaqThin 8x16:pixelsize=16" in foot
    assert "font-bold=Px437 CompaqThin Overstrike:pixelsize=16" in foot
    assert "font-italic=Px437 CompaqThin 8x16:pixelsize=16" in foot


def test_terminus_takes_its_italic_from_ttyp0(tmp_path):
    scheme = palette.load("umber")
    toks = transmute.tokens(scheme, (1920, 1080), None, tmp_path / "s.png", "x", "terminus")
    render.render_tree(tmp_path / "out", toks)
    foot = (tmp_path / "out/foot/foot.ini").read_text()
    assert "font-italic=Ttyp0:style=Italic:pixelsize=16" in foot
    assert "font-bold-italic=Terminus (TTF):pixelsize=16:weight=bold" in foot


def test_vga_bold_is_the_overstrike(tmp_path):
    scheme = palette.load("umber")
    toks = transmute.tokens(scheme, (1920, 1080), None, tmp_path / "s.png", "x", "vga")
    render.render_tree(tmp_path / "out", toks)
    assert (
        "font-bold=PxPlus IBM VGA Overstrike:pixelsize=16"
        in (tmp_path / "out/foot/foot.ini").read_text()
    )


def test_tandy_takes_its_bold_from_another_face(tmp_path):
    scheme = palette.load("umber")
    toks = transmute.tokens(scheme, (1920, 1080), None, tmp_path / "s.png", "x", "tandy")
    render.render_tree(tmp_path / "out", toks)
    foot = (tmp_path / "out/foot/foot.ini").read_text()
    assert "font=Px437 Tandy2K:pixelsize=16" in foot
    assert "font-bold=Px437 AT&T PC6300:pixelsize=16" in foot


def test_tandy_takes_its_italic_from_ttyp0(tmp_path):
    scheme = palette.load("umber")
    toks = transmute.tokens(scheme, (1920, 1080), None, tmp_path / "s.png", "x", "tandy")
    render.render_tree(tmp_path / "out", toks)
    foot = (tmp_path / "out/foot/foot.ini").read_text()
    assert "font-italic=Ttyp0:style=Italic:pixelsize=16" in foot
    assert "font-bold-italic=Px437 AT&T PC6300:pixelsize=16" in foot


def test_icons_fall_back_to_a_smaller_unsmoothed_face(tmp_path):
    scheme = palette.load("umber")
    toks = transmute.tokens(scheme, (1920, 1080), None, tmp_path / "s.png", "x", "tandy")
    render.render_tree(tmp_path / "out", toks)
    foot = (tmp_path / "out/foot/foot.ini").read_text()
    icons = ",Symbols Nerd Font Mono:pixelsize=12:antialias=false:rgba=none\n"
    assert foot.count(icons) == 4


def test_foot_colors_use_sections_foot_accepts(tmp_path):
    scheme = palette.load("vellum")
    toks = transmute.tokens(scheme, (1920, 1080), None, tmp_path / "s.png", "x")
    render.render_tree(tmp_path / "out", toks)
    text = (tmp_path / "out/foot/colors.ini").read_text()
    sections = [line for line in text.splitlines() if line.startswith("[")]
    assert sections == ["[colors-dark]", "[colors-light]"]


def test_lock_card_fits_beside_the_text_on_a_small_screen():
    # A 1366x768 screen: the plate panel ends at 620.
    layout = transmute.lock_layout((1366, 768), 620, 2)
    card_left = 1366 - transmute.MARGIN - layout["card_w"]
    assert layout["lock_x"] + transmute.TEXT_COLUMN + transmute.GAP <= card_left
    assert 0 < layout["card_w"] <= 320 and layout["card_w"] % 2 == 0


def test_lock_card_is_capped_on_a_big_screen():
    assert transmute.lock_layout((3840, 2160), 1900, 3)["card_w"] == 318


def test_jacquard_name_is_not_read_as_a_size(tmp_path):
    scheme = palette.load("umber")
    toks = transmute.tokens(scheme, (1366, 768), None, tmp_path / "s.png", "x")
    render.render_tree(tmp_path / "out", toks)
    assert "font_family = Jacquard 24,\n" in (tmp_path / "out/hypr/hyprlock.conf").read_text()


def test_inset_box_crops_inside_the_frame():
    from athanor import wall

    assert wall.inset_box((1000, 2000), (0.1, 0.05, 0.1, 0.05)) == (800, 1800, 100, 100)
    assert wall.inset_box((1000, 2000), None) == (1000, 2000, 0, 0)


def test_plate_settings_change_the_cache_key():
    from athanor import wall

    a = wall._key({"file": "x", "inset": [0, 0, 0, 0]}, {})
    assert a != wall._key({"file": "x", "inset": [0.03, 0, 0.03, 0]}, {})
    assert a == wall._key({"inset": [0, 0, 0, 0], "file": "x"}, {})


def test_every_level_has_a_plate_on_disk():
    import tomllib
    from importlib.resources import files

    plates = files("athanor") / "plates"
    manifest = tomllib.loads((plates / "plates.toml").read_text())
    assert len(manifest["level"]) == 7, "one plate per dungeon level, one per planet"
    for entry in [*manifest["level"], manifest["lock"]]:
        assert (plates / entry["file"]).is_file(), entry["file"]


def test_workspaces_map_to_levels_and_come_round_again(tmp_path):
    from athanor import wall

    walls = wall.Walls(tuple(tmp_path / f"{n}.png" for n in range(1, 8)), tmp_path / "l", 0, 2)
    assert walls.level(1).name == "1.png" and walls.level(7).name == "7.png"
    assert walls.level(8).name == "1.png" and walls.level(10).name == "3.png"
    assert walls.level(None).name == "1.png" and walls.level(-98).name == "1.png"
    assert walls.desk == walls.level(1)


def test_levels_and_hyprpaper_get_every_plate(tmp_path):
    from athanor import wall

    scheme = palette.load("umber")
    walls = wall.Walls(tuple(tmp_path / f"desk-{n}.png" for n in range(1, 8)), tmp_path / "l", 0, 2)
    toks = transmute.tokens(scheme, (1366, 768), walls, tmp_path / "s.png", "x")
    render.render_tree(tmp_path / "out", toks)
    levels = (tmp_path / "out/hypr/levels.lua").read_text()
    assert all(f'"{tmp_path}/desk-{n}.png"' in levels for n in range(1, 8))
    assert f"path = {tmp_path}/desk-1.png" in (tmp_path / "out/hypr/hyprpaper.conf").read_text()


def test_lock_lines_are_one_block_of_escaped_markup():
    from athanor import cli

    lines = {"date": "a & b", "ruler": "<i>", "moon": "m", "card": "c"}
    out = cli._lock_markup(lines, "e3d6b8,d49a3a,#8a7a62")
    assert out.startswith('<span line_height="1.5">') and out.count("\n") == 3
    assert "a &amp; b" in out and "&lt;i&gt;" in out
    assert '<span foreground="#8a7a62">c</span>' in out


def test_the_lockscreen_greets_the_character(tmp_path, monkeypatch):
    scheme = palette.load("umber")
    toks = transmute.tokens(scheme, (1366, 768), None, tmp_path / "s.png", "x", name="Prospero")
    assert toks["name"] == "Prospero"
    monkeypatch.setattr(transmute.getpass, "getuser", lambda: "nachi")
    assert transmute.tokens(scheme, (1366, 768), None, tmp_path / "s.png", "x")["name"] == "nachi"


@pytest.mark.parametrize("name", palette.SCHEMES)
def test_the_notch_takes_the_schemes_colors_only_when_loaded(tmp_path, name):
    scheme = palette.load(name)
    toks = transmute.tokens(scheme, (1920, 1080), None, tmp_path / "s.png", "x")
    render.render_tree(tmp_path / "out", toks)
    lua = (tmp_path / "out/hypr/colors.lua").read_text()
    plugin = lua[lua.index("hl.get_loaded_plugins()") :]
    assert 'plugin.name == "athanor"' in plugin and "border_size = 0" in plugin
    for role in ("active", "dim", "bg"):
        assert f"rgb({scheme.roles[role][1:]})" in plugin


@pytest.mark.parametrize(("levels", "drawn"), [(True, 7), (False, 1)])
def test_one_plate_for_every_workspace_when_levels_are_off(tmp_path, monkeypatch, levels, drawn):
    from athanor import wall

    def magick(cmd, check):
        Path(cmd[-1]).touch()

    monkeypatch.setattr(wall, "_magick", lambda: "magick")
    monkeypatch.setattr(wall, "_size", lambda path: (1000, 800))
    monkeypatch.setattr(wall.subprocess, "run", magick)
    walls = wall.render(palette.load("umber"), (1366, 768), tmp_path, levels=levels)
    assert len(list(tmp_path.glob("desk-*.png"))) == drawn
    assert walls.level(5) == (walls.levels[4] if levels else walls.levels[0])
    assert walls.level(1).name.startswith("desk-1-")


def test_the_spread_names_a_font_so_a_bitmap_face_cant_be_picked(tmp_path, monkeypatch):
    from athanor import wall

    ran = []
    monkeypatch.setattr(wall, "_magick", lambda: "magick")
    monkeypatch.setattr(wall, "font_dir", lambda: tmp_path)
    monkeypatch.setattr(
        wall.subprocess, "run", lambda args, **kw: ran.append(args) or SimpleNamespace(stdout=b"")
    )
    (tmp_path / "PxPlus_IBM_VGA_8x16.ttf").touch()
    wall.spread_image(["a.png"], palette.load("umber"), 1)
    assert ran[0][2:4] == ["-font", str(tmp_path / "PxPlus_IBM_VGA_8x16.ttf")]
