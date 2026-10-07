import os
from pathlib import Path

BIN = "~/.local/bin/athanor"


def _xdg(var: str, fallback: str) -> Path:
    return Path(os.environ.get(var) or Path.home() / fallback)


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "athanor"


def current_dir() -> Path:
    return config_dir() / "current"


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache") / "athanor"


def state_dir() -> Path:
    return _xdg("XDG_STATE_HOME", ".local/state") / "athanor"


def font_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share") / "fonts" / "athanor"


def data_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share") / "athanor"


def notch_plugin() -> Path:
    return data_dir() / "athanor-notch.so"


def runtime_dir() -> Path:
    return Path(os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/athanor-{os.getuid()}")


def write_atomic(path: Path, data: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    if isinstance(data, str):
        tmp.write_text(data)
    else:
        tmp.write_bytes(data)
    tmp.replace(path)
