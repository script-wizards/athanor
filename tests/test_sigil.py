import shutil
import subprocess

import pytest

from athanor import sigil

PUB = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl test"


def test_fingerprint_matches_ssh_keygen(tmp_path):
    if not shutil.which("ssh-keygen"):
        pytest.skip("ssh-keygen not installed")
    key = tmp_path / "k.pub"
    key.write_text(PUB + "\n")
    out = subprocess.run(
        ["ssh-keygen", "-lf", str(key)], capture_output=True, text=True, check=True
    )
    assert sigil.fingerprint_text(sigil.key_digest(PUB)) == out.stdout.split()[1]


def test_grid_is_framed_and_mirrored():
    cells = sigil.grid(sigil.key_digest(PUB))
    assert len(cells) == sigil.SIZE and all(len(r) == sigil.SIZE for r in cells)
    assert all(cells[0]) and all(cells[-1])
    assert all(row[0] and row[-1] for row in cells)
    for row in cells:
        assert row == row[::-1]


def test_different_keys_differ():
    other = sigil.key_digest(PUB.replace("AAAAIOMq", "AAAAIOMr"))
    assert sigil.grid(sigil.key_digest(PUB)) != sigil.grid(other)


def test_png_header():
    data = sigil.png(sigil.grid(sigil.key_digest(PUB)), "#d49a3a", scale=8)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert int.from_bytes(data[16:20]) == sigil.SIZE * 8


def test_host_digest_falls_back_to_machine_id(tmp_path):
    (tmp_path / "machine-id").write_text("abc\n")
    _, label = sigil.host_digest(tmp_path)
    assert label == "machine-id"
