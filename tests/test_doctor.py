import re
from pathlib import Path

import pytest

from athanor import doctor

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def xdg(tmp_path, monkeypatch):
    for var in ("XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(var, str(tmp_path / var.lower()))
    return tmp_path


def test_font_list_matches_what_the_installer_fetches():
    installed = set(re.findall(r"(\w[\w.-]*\.(?:ttf|bdf))", (ROOT / "install.sh").read_text()))
    installed -= {"TerminusTTF-Bold-4.49.3.ttf", "t0-16i.bdf"}
    assert set(doctor.FONT_FILES) == installed


def test_missing_fonts_fail_with_the_fix(xdg):
    (r,) = doctor.check_font_files()
    assert r.status == doctor.FAIL and "install.sh shell" in r.fix
    fonts = xdg / "xdg_data_home" / "fonts" / "athanor"
    fonts.mkdir(parents=True)
    for f in doctor.FONT_FILES:
        (fonts / f).touch()
    assert doctor.check_font_files()[0].status == doctor.OK


def test_a_face_that_falls_back_fails(xdg):
    results = doctor.check_fonts_resolve(match=lambda fam: "Noto Sans" if "AT&T" in fam else fam)
    assert [r.status for r in results] == [doctor.FAIL]
    assert "AT&T PC6300" in results[0].found and "Noto Sans" in results[0].found


def test_a_terminal_older_than_the_fonts_is_named(xdg):
    fonts = xdg / "xdg_data_home" / "fonts" / "athanor"
    fonts.mkdir(parents=True)
    (fonts / "Px437_Tandy2K.ttf").touch()
    old = lambda names: [("xfce4-terminal", 0.0)]  # noqa: E731
    (r,) = doctor.check_stale_terminals(started=old)
    assert r.status == doctor.WARN and "Close every xfce4-terminal window" in r.fix
    assert doctor.check_stale_terminals(started=lambda names: [("xfce4-terminal", 4e9)]) == []


@pytest.mark.parametrize(
    "conf, status",
    [
        ("[Seat:*]\ngreeter-session=lightdm-mini-greeter\nuser-session=xfce\n", doctor.WARN),
        ("[Seat:*]\ngreeter-session=lightdm-mini-greeter\nuser-session=hyprland\n", doctor.OK),
        ("[Seat:*]\ngreeter-session=lightdm-gtk-greeter\nuser-session=xfce\n", None),
    ],
)
def test_lightdm_mini_greeters_default_session(tmp_path, conf, status):
    path = tmp_path / "lightdm.conf"
    path.write_text(conf)
    results = doctor.check_display_manager(path)
    assert [r.status for r in results] == ([status] if status else [])


def test_hyprland_config_forms(xdg):
    hypr = xdg / "xdg_config_home" / "hypr"
    hypr.mkdir(parents=True)
    (hypr / "hyprland.conf").write_text("# >>> athanor >>>\nsource = x\n# <<< athanor <<<\n")
    statuses = [r.status for r in doctor.check_hypr_config()]
    assert statuses == [doctor.OK, doctor.WARN]
    (hypr / "hyprland.lua").write_text("hl.config({})\n")
    results = doctor.check_hypr_config()
    assert results[0].status == doctor.WARN and "isn't in" in results[0].found
    assert "ignores it" in results[1].found


def test_a_symlinked_zshrc_gets_the_line_to_add_to_its_source(tmp_path, monkeypatch):
    target = tmp_path / "dotfiles-zshrc"
    target.write_text("x=1\n")
    link = tmp_path / ".zshrc"
    link.symlink_to(target)
    monkeypatch.setattr(doctor, "_zshrc", lambda: link)
    (r,) = doctor.check_zsh()
    assert r.status == doctor.WARN and "a symlink to" in r.found and "athanor.zsh" in r.fix


def test_exit_code_is_one_only_on_a_failure(monkeypatch, capsys):
    monkeypatch.setattr(doctor, "run_all", lambda: [doctor.Result("a", doctor.WARN, "w", "f")])
    assert doctor.main() == 0
    monkeypatch.setattr(doctor, "run_all", lambda: [doctor.Result("a", doctor.FAIL, "x", "f")])
    assert doctor.main() == 1
    assert "wound to tend" in capsys.readouterr().out


def test_a_broken_check_does_not_hide_the_rest(monkeypatch):
    def boom():
        raise RuntimeError("bad")

    monkeypatch.setattr(doctor, "CHECKS", (boom, lambda: [doctor.Result("x", doctor.OK, "y")]))
    results = doctor.run_all()
    assert results[0].status == doctor.WARN and "boom" in results[0].found
    assert results[1].found == "y"


def test_no_notch_built_means_nothing_to_say(xdg, monkeypatch):
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "x")
    assert doctor.check_notch() == []


def built_notch(xdg, monkeypatch, plugins: str):
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "x")
    monkeypatch.setattr(doctor.hypr, "request", lambda cmd: plugins)
    notch = xdg / "xdg_data_home" / "athanor" / "athanor-notch.so"
    notch.parent.mkdir(parents=True)
    notch.touch()
    return notch


def test_a_loaded_notch_is_ok(xdg, monkeypatch):
    built_notch(xdg, monkeypatch, '[{"name": "athanor", "version": "0.1.0"}]')
    (r,) = doctor.check_notch()
    assert r.status == doctor.OK


def test_a_notch_hyprland_refused_says_to_rebuild(xdg, monkeypatch):
    notch = built_notch(xdg, monkeypatch, "no plugins loaded")
    (r,) = doctor.check_notch()
    assert r.status == doctor.WARN
    assert "install.sh notch" in r.fix and str(notch) in r.fix
