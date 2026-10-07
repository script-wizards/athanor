import argparse
from datetime import UTC

from athanor import tomb


def test_stone_is_square():
    lines = tomb.stone("firefox", 11, 2026, dlvl=2).splitlines()
    walls = [line for line in lines if line.startswith("    |")]
    assert {len(line) for line in walls} == {len("    |") + tomb.WIDTH + 1}
    assert "SIGSEGV" in "\n".join(lines)
    assert "on Dlvl 2" in "\n".join(lines)


def test_long_names_are_cut():
    stone = tomb.stone("a-very-long-process-name-indeed", 6, 2026)
    assert "a-very-long-proces" in stone
    assert "on Dlvl" not in stone


def test_unknown_signal():
    assert tomb.cause(99) == "signal 99"


def test_parse_coredumpctl_json():
    crash = tomb.parse(
        [{"time": 1791120540000000, "pid": 4242, "sig": 11, "exe": "/usr/lib/firefox/firefox"}]
    )
    assert crash.name == "firefox"
    assert crash.signal == 11
    assert crash.when.tzinfo == UTC
    assert tomb.parse([]) is None


def test_parse_strips_control_characters():
    crash = tomb.parse([{"time": 1, "sig": 11, "exe": "/tmp/evil\x1b]0;pwned\x07"}])
    assert crash.name == "evil?]0;pwned?"


def test_notify_escapes_markup(monkeypatch, tmp_path):
    from athanor import cli, transmute

    monkeypatch.setattr(cli.macos, "available", lambda: False)

    crash = tomb.parse([{"time": 2, "sig": 11, "exe": "/tmp/-<i>x&y"}])
    sent = []
    monkeypatch.setattr(tomb, "latest", lambda: crash)
    monkeypatch.setattr(cli.hypr, "active_workspace", lambda: None)
    monkeypatch.setattr(transmute, "run", lambda *cmd: sent.append(cmd))
    monkeypatch.setattr(cli, "_tomb_state", lambda: tmp_path / "tomb.json")
    cli.cmd_tomb(argparse.Namespace(demo=False, notify=True))
    body = sent[0][-1]
    assert sent[0][-2] == "--"
    assert body.startswith("-&lt;i&gt;x&amp;y was killed")


def test_latest_asks_for_the_newest_crash(monkeypatch):
    import subprocess

    monkeypatch.setattr(tomb.macos, "available", lambda: False)

    seen = []

    def run(cmd, **_):
        seen.append(cmd)
        return subprocess.CompletedProcess(
            cmd, 0, '[{"time": 5, "sig": 11, "exe": "/usr/bin/sleep"}]'
        )

    monkeypatch.setattr(tomb.subprocess, "run", run)
    assert tomb.latest().name == "sleep"
    assert "--reverse" in seen[0]


def test_a_session_programs_crash_at_logout_is_not_a_tombstone():
    old = tomb.parse([{"time": 1_000 * 1_000_000, "sig": 6, "exe": "/usr/bin/hypridle"}])
    new = tomb.parse([{"time": 3_000 * 1_000_000, "sig": 6, "exe": "/usr/bin/hypridle"}])
    other = tomb.parse([{"time": 1_000 * 1_000_000, "sig": 11, "exe": "/usr/bin/sleep"}])
    assert tomb.from_last_session(old, 2_000)
    assert not tomb.from_last_session(new, 2_000)
    assert not tomb.from_last_session(other, 2_000)
    assert not tomb.from_last_session(old, None)
