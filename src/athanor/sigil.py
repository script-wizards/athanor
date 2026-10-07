import base64
import hashlib
import struct
import zlib
from pathlib import Path

from . import macos

HOST_KEYS = ("ssh_host_ed25519_key.pub", "ssh_host_ecdsa_key.pub", "ssh_host_rsa_key.pub")
SIZE = 11


def key_digest(pub_line: str) -> bytes:
    blob = base64.b64decode(pub_line.split()[1])
    return hashlib.sha256(blob).digest()


def fingerprint_text(digest: bytes) -> str:
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


def host_digest(etc: Path = Path("/etc")) -> tuple[bytes, str]:
    for name in HOST_KEYS:
        path = etc / "ssh" / name
        try:
            digest = key_digest(path.read_text())
        except (OSError, IndexError, ValueError):
            continue
        return digest, fingerprint_text(digest)
    try:
        machine = (etc / "machine-id").read_text().strip()
    except OSError:
        machine = macos.machine_id() if macos.available() else ""
        if machine:
            digest = hashlib.sha256(machine.encode()).digest()
            return digest, "platform-uuid"
        # Keep a stable seed even on systems without SSH keys or a machine id.
        import socket

        machine = socket.gethostname()
    digest = hashlib.sha256(machine.encode()).digest()
    return digest, "machine-id"


def grid(digest: bytes) -> list[list[bool]]:
    cells = [[False] * SIZE for _ in range(SIZE)]
    for i in range(SIZE):
        cells[0][i] = cells[SIZE - 1][i] = cells[i][0] = cells[i][SIZE - 1] = True
    bit = 0
    for y in range(2, SIZE - 2):
        for x in range(2, SIZE // 2 + 1):
            on = bool(digest[bit // 8] >> (bit % 8) & 1)
            cells[y][x] = cells[y][SIZE - 1 - x] = on
            bit += 1
    return cells


def text(cells: list[list[bool]]) -> str:
    return "\n".join("".join("██" if on else "  " for on in row) for row in cells)


def png(cells: list[list[bool]], color: str, scale: int = 8) -> bytes:
    r, g, b = (int(color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    on, off = bytes((r, g, b, 255)), bytes(4)
    rows = []
    for row in cells:
        line = b"".join((on if c else off) * scale for c in row)
        rows.extend([b"\x00" + line] * scale)
    side = len(cells) * scale

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    header = struct.pack(">IIBBBBB", side, side, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
        + chunk(b"IEND", b"")
    )
