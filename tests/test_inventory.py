import pytest

from athanor import inventory


@pytest.fixture(autouse=True)
def desktop_entries(tmp_path, monkeypatch):
    apps = tmp_path / "share" / "applications"
    apps.mkdir(parents=True)
    (apps / "foot.desktop").write_text(
        "[Desktop Entry]\nName=Foot\nGenericName=Terminal\nCategories=System;TerminalEmulator;\n"
    )
    (apps / "zathura.desktop").write_text(
        "[Desktop Entry]\nName=Zathura\nCategories=Office;Viewer;\n"
    )
    (apps / "feh.desktop").write_text(
        "[Desktop Entry]\nName=Feh\nGenericName=Image viewer\n"
        "Categories=Graphics;2DGraphics;Viewer;\n"
    )
    (apps / "helix.desktop").write_text(
        "[Desktop Entry]\nName=Helix\nCategories=Utility;TextEditor;\n"
    )
    (apps / "galculator.desktop").write_text(
        "[Desktop Entry]\nName=Galculator\nCategories=Utility;\n"
    )
    (apps / "firefox.desktop").write_text(
        "[Desktop Entry]\nName=Firefox\nGenericName=Web Browser\nStartupWMClass=firefox\n"
        "Categories=Network;WebBrowser;\n"
    )
    (apps / "obsidian.desktop").write_text(
        "[Desktop Entry]\nName=Obsidian\nStartupWMClass=md.obsidian.Obsidian\n"
        "[Desktop Action new]\nName=New vault\n"
    )
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "share"))
    inventory._desktop_entries.cache_clear()
    yield
    inventory._desktop_entries.cache_clear()


def client(address, cls, title, workspace, history, **extra):
    return {
        "address": address,
        "class": cls,
        "title": title,
        "workspace": {"id": workspace},
        "focusHistoryID": history,
        **extra,
    }


CLIENTS = [
    client("0x2", "md.obsidian.Obsidian", "dungeonbooks - Obsidian", 2, 1),
    client("0x1", "foot", "zsh", 1, 0),
    client("0x3", "foot", "foot", 1, 2),
    client("0x4", "firefox", "x" * 60, 3, 3),
]


def test_items_in_focus_order_with_letters():
    found = inventory.items(CLIENTS, 1)
    assert [i.text for i in found] == [
        'a - a terminal called "zsh" (wielded)',
        'b - a journal called "dungeonbooks - Obsidian" (on Dlvl 2)',
        "c - a terminal",
        'd - a browser called "' + "x" * 39 + '…" (on Dlvl 3)',
    ]
    assert [i.address for i in found] == ["0x1", "0x2", "0x3", "0x4"]


def test_titles_lose_control_characters():
    found = inventory.items([client("0x1", "foot", "evil\x1b]0;x\x07", 1, 0)], 1)
    assert "\x1b" not in found[0].text and "\x07" not in found[0].text


def test_hidden_windows_are_not_carried():
    found = inventory.items([client("0x1", "foot", "zsh", 1, 0, hidden=True)], 1)
    assert found == []


def test_prompt_names_the_letters():
    found = inventory.items(CLIENTS, 1)
    assert inventory.prompt(found) == "What do you want to use? [a-d] "
    assert inventory.prompt(found[:1]) == "What do you want to use? [a] "


def test_focus_window_tries_lua_then_hyprlang(monkeypatch):
    from athanor import hypr

    sent = []

    def request(command):
        sent.append(command)
        return "ok" if "focuswindow" in command else "error: parse"

    monkeypatch.setattr(hypr, "request", request)
    assert hypr.focus_window("0x555bf0ae8b70")
    assert sent[0] == "dispatch hl.dsp.focus({ window = 'address:0x555bf0ae8b70' })"
    assert sent[1] == "dispatch focuswindow address:0x555bf0ae8b70"


def test_focus_window_refuses_anything_but_a_hex_address(monkeypatch):
    from athanor import hypr

    monkeypatch.setattr(hypr, "request", lambda c: (_ for _ in ()).throw(AssertionError(c)))
    assert not hypr.focus_window("0x1' }) hl.dsp.exit() --")


def test_quit_only_on_a_yes(monkeypatch):
    from athanor import quit

    assert quit.CHOICES[0].startswith("n - ")
    assert quit.confirmed("1\n") and not quit.confirmed("0\n") and not quit.confirmed("")


def test_exit_tries_lua_then_hyprlang(monkeypatch):
    from athanor import hypr

    sent = []
    monkeypatch.setattr(
        hypr, "request", lambda c: sent.append(c) or ("ok" if c == "dispatch exit" else "error")
    )
    assert hypr.exit_session()
    assert sent == ["dispatch hl.dsp.exit()", "dispatch exit"]


def test_tools_are_named_as_a_wizard_would():
    assert inventory.item("foot") == "terminal"
    assert inventory.item("firefox") == "browser"
    assert inventory.item("md.obsidian.Obsidian") == "journal"
    assert inventory.item("zathura") == "book"
    assert inventory.item("feh") == "viewer"
    assert inventory.item("helix") == "quill"
    assert inventory.item("galculator") == "galculator"
    assert inventory.item("org.example.Thing") == "thing"
    assert inventory.item("") == "thing"
    assert inventory._noun("foot") == "a terminal" and inventory._noun("abacus") == "an abacus"
