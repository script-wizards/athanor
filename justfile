# run the tests
test:
    uv run pytest -q

# lint python and the installer
lint:
    uv run ruff check src tests
    uv run ruff format --check src tests
    shellcheck install.sh docs/screenshots/shoot.sh docs/screenshots/palette.sh

# format python
fmt:
    uv run ruff format src tests
    uv run ruff check --fix src tests

# install on this machine (Arch desktop or macOS shell)
install:
    ./install.sh

# print what the installer would do
dry-run:
    ./install.sh --dry-run

# render a scheme into ./preview without touching ~/.config
preview scheme="umber" size="1920x1080":
    XDG_CONFIG_HOME=$PWD/preview/config XDG_CACHE_HOME=$PWD/preview/cache XDG_STATE_HOME=$PWD/preview/state \
        uv run athanor transmute {{scheme}} --no-reload --size {{size}}

# check the configs with Hyprland and foot and build the notch (needs both installed)
verify:
    #!/usr/bin/env bash
    set -euo pipefail
    tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
    XDG_CONFIG_HOME=$tmp/config XDG_CACHE_HOME=$tmp/cache XDG_STATE_HOME=$tmp/state \
        uv run athanor transmute umber --no-reload --size 1366x768 >/dev/null
    mkdir -p "$tmp/config/athanor/hypr"
    ln -s "$PWD/config/hypr/athanor.lua" "$PWD/config/hypr/binds.lua" "$tmp/config/athanor/hypr/"
    printf 'require("%s/config/athanor/hypr/athanor")\nrequire("%s/config/athanor/hypr/binds")\n' "$tmp" "$tmp" >"$tmp/hyprland.lua"
    XDG_CONFIG_HOME=$tmp/config Hyprland --verify-config -c "$tmp/hyprland.lua" 2>&1 | grep -v DEBUG | tail -n +2
    foot --check-config --config "$tmp/config/athanor/current/foot/foot.ini" && echo "foot ok"
    make -s -C plugin OUT="$tmp/athanor-notch.so" && echo "notch ok"

# retake the README's images from inside Hyprland
screenshots:
    docs/screenshots/shoot.sh
