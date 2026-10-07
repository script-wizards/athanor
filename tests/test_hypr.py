import os
import socket
import time

import pytest

from athanor import hypr, transmute


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    monkeypatch.setattr(hypr, "_bases", lambda: [tmp_path / "hypr"])
    return tmp_path / "hypr"


def instance(base, name: str, live: bool, age: float):
    d = base / name
    d.mkdir(parents=True)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(str(d / ".socket.sock"))
    if live:
        s.listen()
    else:
        s.close()
    stamp = time.time() - age
    os.utime(d, (stamp, stamp))
    return s


def test_outside_the_session_the_newest_live_instance_answers(runtime):
    older = instance(runtime, "a", live=True, age=60)
    newer = instance(runtime, "b", live=True, age=10)
    instance(runtime, "c", live=False, age=0)
    assert hypr._socket_path() == runtime / "b" / ".socket.sock"
    assert hypr._socket_path(".socket2.sock") == runtime / "b" / ".socket2.sock"
    older.close()
    newer.close()


def test_no_live_instance_means_no_socket(runtime):
    instance(runtime, "a", live=False, age=0)
    assert hypr._socket_path() is None


def test_the_signature_still_decides_inside_the_session(runtime, monkeypatch):
    live = instance(runtime, "a", live=True, age=0)
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "gone")
    assert hypr._socket_path() is None
    live.close()


def test_drawing_for_the_default_screen_says_so(monkeypatch):
    said = []
    monkeypatch.setattr(hypr, "screen_size", lambda: None)
    assert transmute.screen_or_default(said.append) == transmute.DEFAULT_SIZE
    assert "1920x1080" in said[0] and "inside the session" in said[0]
    monkeypatch.setattr(hypr, "screen_size", lambda: (1366, 768))
    assert transmute.screen_or_default(said.append) == (1366, 768)
    assert len(said) == 1
