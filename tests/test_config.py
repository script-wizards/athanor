from athanor import config


def _load(tmp_path, monkeypatch, text):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    (tmp_path / "athanor").mkdir()
    (tmp_path / "athanor" / "athanor.toml").write_text(text)
    return config.load()


def test_terminal_font_defaults_to_tandy(tmp_path, monkeypatch):
    assert _load(tmp_path, monkeypatch, "").terminal_font == "tandy"


def test_terminal_font_is_read(tmp_path, monkeypatch):
    cfg = _load(tmp_path, monkeypatch, '[display]\nterminal_font = "Compaq"\n')
    assert cfg.terminal_font == "compaq"


def test_unknown_terminal_font_falls_back(tmp_path, monkeypatch):
    cfg = _load(tmp_path, monkeypatch, '[display]\nterminal_font = "comic sans"\n')
    assert cfg.terminal_font == "tandy"


def test_the_character_defaults_to_who_and_where_you_are(tmp_path, monkeypatch):
    cfg = _load(tmp_path, monkeypatch, "")
    assert (cfg.name, cfg.title, cfg.race) == ("", "the Wizard", "")


def test_the_character_can_be_named(tmp_path, monkeypatch):
    text = '[character]\nname = "Prospero"\ntitle = "the Magus"\nrace = "Arch Linux"\n'
    cfg = _load(tmp_path, monkeypatch, text)
    assert (cfg.name, cfg.title, cfg.race) == ("Prospero", "the Magus", "Arch Linux")


def test_levels_default_on_and_can_be_turned_off(tmp_path, monkeypatch):
    assert _load(tmp_path, monkeypatch, "").levels is True
    (tmp_path / "athanor" / "athanor.toml").write_text("[display]\nlevels = false\n")
    assert config.load().levels is False
