import json
import plistlib
from types import SimpleNamespace

import pytest

from athanor import cli, doctor, guide, macos, palette, paths, sigil, status, tomb, transmute


@pytest.fixture
def mac(monkeypatch):
    monkeypatch.setattr(macos, "available", lambda: True)


@pytest.mark.parametrize(
    "state, charging", [("discharging", False), ("charging", True), ("charged", True)]
)
def test_native_battery_and_apple_silicon_health(mac, monkeypatch, state, charging):
    info = plistlib.dumps([{"MaxCapacity": 94, "DesignCapacity": 5000}]).decode()
    monkeypatch.setattr(
        macos,
        "command",
        lambda *cmd: (
            info if "ioreg" in cmd[0] else f" -InternalBattery-0 73%; {state}; 1:00 remaining"
        ),
    )
    assert status.battery() == status.Battery(73, 94, charging)


def test_intel_battery_health_and_desktop_without_battery(mac, monkeypatch):
    info = plistlib.dumps([{"MaxCapacity": 4200, "DesignCapacity": 5000}]).decode()
    monkeypatch.setattr(
        macos,
        "command",
        lambda *cmd: (
            info if "ioreg" in cmd[0] else " -InternalBattery-0 80%; discharging; 1:00 remaining"
        ),
    )
    assert status.battery() == status.Battery(80, 84, False)
    monkeypatch.setattr(macos, "command", lambda *cmd: "Now drawing from 'AC Power'")
    assert status.battery() is None


def test_native_cpu_delta(mac, monkeypatch):
    samples = iter([(800, 1000), (900, 1200)])
    monkeypatch.setattr(macos, "cpu_sample", lambda: next(samples))
    cpu = status.Cpu()
    assert cpu.percent() is None
    assert cpu.percent() == 50


def test_native_memory_accounts_for_compressor(mac, monkeypatch):
    monkeypatch.setattr(
        macos,
        "command",
        lambda *cmd: (
            "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
            "Pages active: 100.\nPages wired down: 50.\nPages occupied by compressor: 20.\n"
            "Pages stored in compressor: 1000.\nPages free: 10.\n"
        ),
    )
    assert status.mem_used() == 170 * 16384


def test_native_uptime(mac, monkeypatch):
    monkeypatch.setattr(macos, "command", lambda *cmd: "{ sec = 1000, usec = 123 } date")
    monkeypatch.setattr(macos.time, "time", lambda: 4600)
    assert status.uptime_minutes() == 60


def test_unavailable_native_statistics_do_not_crash(mac, monkeypatch):
    monkeypatch.setattr(macos, "command", lambda *cmd: "")
    assert status.battery() is None
    assert status.mem_used() == 0
    assert status.uptime_minutes() == 0


def test_native_font_directory_and_xdg_override(monkeypatch, tmp_path):
    monkeypatch.setattr(paths.sys, "platform", "darwin")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert paths.font_dir() == tmp_path / "Library/Fonts/athanor"
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert paths.font_dir() == tmp_path / "data/fonts/athanor"


def test_machine_sigil_uses_mac_uuid_without_ssh(mac, monkeypatch, tmp_path):
    monkeypatch.setattr(macos, "machine_id", lambda: "one-mac")
    first, label = sigil.host_digest(tmp_path)
    assert label == "platform-uuid"
    assert sigil.host_digest(tmp_path)[0] == first
    monkeypatch.setattr(macos, "machine_id", lambda: "another-mac")
    assert sigil.host_digest(tmp_path)[0] != first


def test_terminal_profiles_contain_all_schemes_and_colors(tmp_path):
    macos.render_profiles(tmp_path)
    for name in palette.SCHEMES:
        profile = plistlib.loads((tmp_path / f"athanor-{name}.terminal").read_bytes())
        assert profile["type"] == "Window Settings"
        assert len([key for key in profile if key.startswith("ANSI")]) == 16
        archive = plistlib.loads(profile["BackgroundColor"])
        assert archive["$objects"][2]["$classname"] == "NSColor"
        rgb = [float(v) for v in archive["$objects"][1]["NSRGB"].rstrip(b"\0").split()]
        assert rgb == pytest.approx([v / 255 for v in palette.rgb(palette.load(name).roles["bg"])])


def test_applescript_receives_paths_and_messages_as_arguments(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(macos, "command", lambda *cmd: calls.append(cmd) or "ok\n")
    path = tmp_path / 'a "quoted" wallpaper.png'
    assert macos.set_wallpaper(path)
    assert calls[-1][-1] == str(path)
    assert str(path) not in calls[-1][2]
    macos.notify('a "quoted" message')
    assert calls[-1][-1] == 'a "quoted" message'


def test_macos_transmute_has_no_linux_side_effects(mac, monkeypatch, tmp_path):
    for var in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(var, str(tmp_path / var))
    monkeypatch.setattr(transmute.wall, "render", lambda *a: None)
    monkeypatch.setattr(transmute.sigil, "host_digest", lambda: (b"a" * 32, "uuid"))
    monkeypatch.setattr(transmute, "recolor_terminals", lambda scheme: 0)
    monkeypatch.setattr(macos, "notify", lambda message: None)

    def linux_call(*args, **kwargs):
        pytest.fail("macOS transmute called a Linux desktop backend")

    monkeypatch.setattr(transmute.hypr, "request", linux_call)
    monkeypatch.setattr(transmute.cursor, "render", linux_call)
    monkeypatch.setattr(transmute, "run", linux_call)
    transmute.apply("vellum", size=(800, 600))
    assert transmute.saved_scheme() == "vellum"
    assert (paths.current_dir() / "terminal/athanor-vellum.terminal").is_file()
    assert (paths.current_dir() / "kitty/colors.conf").is_file()
    assert not (tmp_path / "XDG_DATA_HOME/icons").exists()


def test_doctor_skips_linux_checks(mac, monkeypatch):
    def linux_call():
        pytest.fail("macOS doctor ran a Linux-only check")

    monkeypatch.setattr(
        doctor, "CHECKS", (linux_call, lambda: [doctor.Result("x", doctor.OK, "y")])
    )
    monkeypatch.setattr(doctor, "LINUX_CHECKS", (linux_call,))
    assert [r.found for r in doctor.run_all()] == ["y"]


@pytest.mark.parametrize("command", ["quit", "windows"])
def test_unsupported_mac_commands_explain_requirement(mac, command):
    with pytest.raises(SystemExit, match="requires Linux and Hyprland"):
        cli.main([command])


def test_macos_guide_explains_terminal_profiles(mac):
    text = guide.text(False)
    assert "Terminal.app" in text and "wall N" in text
    assert "Hold Super" not in text


def test_native_crash_report_and_skipping_non_crash_reports(tmp_path):
    header = {"app_name": "Example", "timestamp": "2026-10-07 12:00:00+03:00"}
    report = {"procName": "Example", "exception": {"signal": "SIGSEGV"}}
    text = json.dumps(header) + "\n" + json.dumps(report)
    crash = tomb.parse_macos(text)
    assert crash.name == "Example" and crash.signal == 11
    assert crash.when.hour == 9
    (tmp_path / "crash.ips").write_text(text)
    (tmp_path / "analytics.ips").write_text('{"bug_type":"211"}')
    assert tomb.latest_macos((tmp_path,)) == crash
    assert tomb.parse_macos("not JSON") is None


def test_native_command_handles_failure(monkeypatch):
    monkeypatch.setattr(
        macos.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(returncode=1, stdout="unexpected output"),
    )
    assert macos.command("missing") == ""
