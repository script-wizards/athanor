import json
import os
import socket
from pathlib import Path


def _socket_path(name: str = ".socket.sock") -> Path | None:
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not sig:
        return None
    for base in (os.environ.get("XDG_RUNTIME_DIR"), "/tmp"):
        if base:
            path = Path(base) / "hypr" / sig / name
            if path.exists():
                return path
    return None


def events() -> socket.socket | None:
    path = _socket_path(".socket2.sock")
    if path is None:
        return None
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(str(path))
    except OSError:
        s.close()
        return None
    return s


def request(command: str) -> str | None:
    path = _socket_path()
    if path is None:
        return None
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(str(path))
            s.sendall(command.encode())
            chunks = []
            while chunk := s.recv(65536):
                chunks.append(chunk)
    except OSError:
        return None
    return b"".join(chunks).decode(errors="replace")


def focus_window(address: str) -> bool:
    # Lua sessions only take hl.dsp.focus, hyprlang sessions only focuswindow.
    # The hex check keeps the address from breaking out of the Lua string.
    if not address.startswith("0x") or not all(c in "0123456789abcdef" for c in address[2:]):
        return False
    for command in (
        f"dispatch hl.dsp.focus({{ window = 'address:{address}' }})",
        f"dispatch focuswindow address:{address}",
    ):
        if (request(command) or "").strip() == "ok":
            return True
    return False


def session_start() -> float | None:
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
    parts = sig.split("_")
    if len(parts) >= 2 and parts[1].isdigit():
        return float(parts[1])
    return None


def exit_session() -> bool:
    for command in ("dispatch hl.dsp.exit()", "dispatch exit"):
        if (request(command) or "").strip() == "ok":
            return True
    return False


def query(command: str):
    reply = request(f"j/{command}")
    if not reply:
        return None
    try:
        return json.loads(reply)
    except json.JSONDecodeError:
        return None


def active_workspace() -> int | None:
    ws = query("activeworkspace")
    return ws.get("id") if isinstance(ws, dict) else None


def screen_size() -> tuple[int, int] | None:
    monitors = query("monitors")
    if not monitors:
        return None
    sizes = []
    for m in monitors:
        scale = m.get("scale") or 1
        w, h = m["width"] / scale, m["height"] / scale
        if m.get("transform", 0) % 2:
            w, h = h, w
        sizes.append((round(w), round(h)))
    return max(sizes, key=lambda s: s[0] * s[1])
