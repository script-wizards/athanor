#!/usr/bin/env bash
#   ./install.sh [layer...]           install layers (default: shell desktop)
#   ./install.sh --dry-run [layer...] print what would happen
#   ./install.sh --uninstall          remove Athanor
#   ./install.sh --uninstall --purge  also remove settings, fonts, cache, state
#
# Layers:
#   shell    the command, fonts, zsh prompt and Helix theme
#   desktop  Hyprland, Waybar, mako, fuzzel, hyprlock, hypridle, hyprpaper,
#            foot and the coredump watcher (implies shell)
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
config=${XDG_CONFIG_HOME:-$HOME/.config}
home=$config/athanor
fonts=${XDG_DATA_HOME:-$HOME/.local/share}/fonts/athanor
cursors=${XDG_DATA_HOME:-$HOME/.local/share}/icons/athanor
cache=${XDG_CACHE_HOME:-$HOME/.cache}/athanor
state=${XDG_STATE_HOME:-$HOME/.local/state}/athanor
units=$config/systemd/user
athanor=$HOME/.local/bin/athanor

vga_zip=https://int10h.org/oldschool-pc-fonts/download/oldschool_pc_font_pack_v2.2_linux.zip
google=https://github.com/google/fonts/raw/main/ofl
cozette=https://github.com/the-moonwitch/Cozette/releases/download/v.1.30.0/CozetteVector.ttf
terminus_zip=https://files.ax86.net/terminus-ttf/files/4.49.3/terminus-ttf-4.49.3.zip
ttyp0=uw-ttyp0-2.1
ttyp0_tar=https://people.mpi-inf.mpg.de/~uwe/misc/uw-ttyp0/$ttyp0.tar.gz

markers() {
  local c='#'
  [[ $1 == *.lua ]] && c='--'
  begin="$c >>> athanor >>>"
  end="$c <<< athanor <<<"
}

shell_packages=(zsh uv imagemagick curl unzip fontconfig perl)
desktop_packages=(
  hyprland hyprlock hypridle waybar mako fuzzel foot hyprpaper swaybg
  libnotify grim slurp wl-clipboard brightnessctl playerctl
)

dry=0 mode=install purge=0 fresh_fonts=0
layers=()
for arg in "$@"; do
  case $arg in
    --dry-run) dry=1 ;;
    --uninstall) mode=uninstall ;;
    --purge) purge=1 ;;
    shell | desktop) layers+=("$arg") ;;
    -h | --help)
      sed -n '2,/^set -euo/{/^set -euo/d;s/^# \{0,1\}//;p}' "$0"
      exit 0
      ;;
    *)
      echo "unknown argument: $arg (try --help)" >&2
      exit 2
      ;;
  esac
done
((${#layers[@]})) || layers=(shell desktop)

has_layer() {
  local l
  for l in "${layers[@]}"; do [[ $l == "$1" ]] && return 0; done
  return 1
}
if has_layer desktop && ! has_layer shell; then
  layers=(shell "${layers[@]}")
fi

say() { printf '\033[33m@\033[0m %s\n' "$*"; }
warn() { printf '\033[31m!\033[0m %s\n' "$*" >&2; }
run() {
  if ((dry)); then
    printf '    %s\n' "$*"
  else
    "$@"
  fi
}

ours() { [[ -L $1 && $(readlink "$1") == "$root"/* ]]; }

link() {
  local src=$1 dest=$2
  if ours "$dest"; then
    [[ $(readlink "$dest") == "$src" ]] && return 0
    run ln -sfn "$src" "$dest"
    return 0
  fi
  if [[ -e $dest || -L $dest ]]; then
    warn "$dest already exists and isn't Athanor's. Leaving it alone."
    return 0
  fi
  run mkdir -p "$(dirname "$dest")"
  run ln -s "$src" "$dest"
}

unlink_ours() {
  if ours "$1"; then
    say "removing $1"
    run rm "$1"
  fi
}

# Editing a stow symlink or a chezmoi target in place would be lost or land in
# the wrong file.
editable() {
  local file=$1
  if [[ -L $file ]]; then
    reason="it is a symlink to $(readlink -f "$file")"
    return 1
  fi
  if command -v chezmoi >/dev/null && chezmoi source-path "$file" >/dev/null 2>&1; then
    reason="chezmoi manages it ($(chezmoi source-path "$file"))"
    return 1
  fi
  return 0
}

has_block() {
  markers "$1"
  [[ -f $1 ]] && grep -qxF -e "$begin" -- "$1"
}

only_block() {
  has_block "$1" || return 1
  [[ -z $(awk -v b="$begin" -v e="$end" '$0 == b { s = 1 } !s { print } $0 == e { s = 0 }' "$1" | tr -d '[:space:]') ]]
}

add_block() {
  local file=$1 body=$2 reason=''
  if has_block "$file"; then
    return 0
  fi
  local block
  block=$(printf '%s\n%s\n%s' "$begin" "$body" "$end")
  if ! editable "$file"; then
    warn "Not editing $file: $reason. Add this to its source yourself:"
    printf '%s\n' "$block" | sed 's/^/      /' >&2
    return 0
  fi
  say "adding the Athanor block to $file"
  ((dry)) && return 0
  mkdir -p "$(dirname "$file")"
  local tmp
  tmp=$(mktemp "$file.athanor.XXXXXX")
  {
    printf '%s\n' "$block"
    if [[ -s $file ]]; then
      printf '\n'
      cat "$file"
    fi
  } >"$tmp"
  [[ -f $file ]] && chmod --reference="$file" "$tmp"
  mv "$tmp" "$file"
}

remove_block() {
  local file=$1 reason=''
  has_block "$file" || return 0
  if ! editable "$file"; then
    warn "Not editing $file: $reason. Remove the Athanor block from its source yourself."
    return 0
  fi
  say "removing the Athanor block from $file"
  ((dry)) && return 0
  local tmp
  tmp=$(mktemp "$file.athanor.XXXXXX")
  awk -v b="$begin" -v e="$end" '
    $0 == b { skip = 1; next }
    skip && $0 == e { skip = 0; gap = 1; next }
    skip { next }
    gap && $0 == "" { gap = 0; next }
    { gap = 0; print }
  ' "$file" >"$tmp"
  chmod --reference="$file" "$tmp"
  if [[ -z $(tr -d '[:space:]' <"$tmp") ]]; then
    rm "$tmp" "$file"
  else
    mv "$tmp" "$file"
  fi
}

zshrc() {
  if command -v zsh >/dev/null; then
    # ZDOTDIR is set in .zshenv, the only file a non-interactive zsh reads.
    printf '%s/.zshrc' "$(zsh -c 'print -r -- "${ZDOTDIR:-$HOME}"')"
  else
    printf '%s/.zshrc' "$HOME"
  fi
}

hyprconf=$config/hypr/hyprland.conf
hyprlua=$config/hypr/hyprland.lua
zsh_body='[[ -r ~/.config/athanor/athanor.zsh ]] && source ~/.config/athanor/athanor.zsh'
hypr_body='source = ~/.config/athanor/hypr/athanor.conf'
hypr_binds='source = ~/.config/athanor/hypr/binds.conf'
# require() needs an absolute path.
lua_dir='local xdg = os.getenv("XDG_CONFIG_HOME")'$'\n''local athanor = ((xdg and xdg ~= "") and xdg or (os.getenv("HOME") .. "/.config")) .. "/athanor/hypr/"'
lua_body="$lua_dir"$'\n''require(athanor .. "athanor")'
lua_binds='require(athanor .. "binds")'

shell_links=(
  "config/zsh/athanor.zsh:$home/athanor.zsh"
  "config/helix/themes/athanor.toml:$config/helix/themes/athanor.toml"
  "config/fontconfig/60-athanor.conf:$config/fontconfig/conf.d/60-athanor.conf"
)
desktop_links=(
  "config/hypr/athanor.lua:$home/hypr/athanor.lua"
  "config/hypr/binds.lua:$home/hypr/binds.lua"
  "config/hypr/athanor.conf:$home/hypr/athanor.conf"
  "config/hypr/binds.conf:$home/hypr/binds.conf"
  "config/hypr/hypridle.conf:$home/hypr/hypridle.conf"
  "config/waybar/config.jsonc:$home/waybar/config.jsonc"
  "config/systemd/user/athanor-tomb.path:$units/athanor-tomb.path"
  "config/systemd/user/athanor-tomb.service:$units/athanor-tomb.service"
)
# Links the first version of the installer made over existing configs.
legacy_links=(
  "$config/hypr/hyprland.conf" "$config/hypr/hypridle.conf" "$config/hypr/hyprlock.conf"
  "$config/foot/foot.ini" "$config/waybar/config.jsonc" "$config/waybar/style.css"
  "$config/mako/config" "$config/fuzzel/fuzzel.ini"
)

install_packages() {
  local wanted=("$@") missing=() p
  if ! command -v pacman >/dev/null; then
    warn "No pacman here. Install these yourself: ${wanted[*]}"
    return 0
  fi
  for p in "${wanted[@]}"; do
    pacman -Q "$p" >/dev/null 2>&1 || missing+=("$p")
  done
  ((${#missing[@]})) || return 0
  # No -y so this never does a partial upgrade.
  say "installing ${missing[*]}"
  run sudo pacman -S --needed "${missing[@]}"
}

ttyp0_italic() {
  perl "$1/bin/bdfmangle" "$1/bdf/t0-16i.bdf" "$1/VARIANTS.dat" "$1/mgl/unicode.mgl" >"$2"
}

install_fonts() {
  say "fonts in $fonts"
  local f
  local oldschool=(PxPlus_IBM_VGA_8x16.ttf Px437_CompaqThin_8x16.ttf Px437_Tandy2K.ttf Px437_ATT_PC6300.ttf)
  for f in TerminusTTF-4.49.3.ttf CozetteVector.ttf t0-16i-uni.bdf "${oldschool[@]}"; do
    # Running terminals won't see new fonts until they restart.
    [[ -f $fonts/$f ]] || fresh_fonts=1
  done
  run mkdir -p "$fonts"
  local missing=()
  for f in "${oldschool[@]}"; do
    [[ -f $fonts/$f ]] || missing+=("ttf - Px (pixel outline)/$f")
  done
  if ((${#missing[@]})); then
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
    run curl -fsSL -o "$tmp/oldschool.zip" "$vga_zip"
    run unzip -j -o -q "$tmp/oldschool.zip" "${missing[@]}" -d "$fonts"
  fi
  if [[ ! -f $fonts/TerminusTTF-4.49.3.ttf ]]; then
    tmp=${tmp:-$(mktemp -d)}
    trap 'rm -rf "$tmp"' EXIT
    run curl -fsSL -o "$tmp/terminus.zip" "$terminus_zip"
    run unzip -j -o -q "$tmp/terminus.zip" \
      "terminus-ttf-4.49.3/TerminusTTF-4.49.3.ttf" \
      "terminus-ttf-4.49.3/TerminusTTF-Bold-4.49.3.ttf" -d "$fonts"
  fi
  if [[ ! -f $fonts/t0-16i-uni.bdf ]]; then
    tmp=${tmp:-$(mktemp -d)}
    trap 'rm -rf "$tmp"' EXIT
    run curl -fsSL -o "$tmp/ttyp0.tar.gz" "$ttyp0_tar"
    run tar -xzf "$tmp/ttyp0.tar.gz" -C "$tmp"
    run ttyp0_italic "$tmp/$ttyp0" "$fonts/t0-16i-uni.bdf"
  fi
  [[ -f $fonts/CozetteVector.ttf ]] ||
    run curl -fsSL -o "$fonts/CozetteVector.ttf" "$cozette"
  [[ -f $fonts/Jacquard24-Regular.ttf ]] ||
    run curl -fsSL -o "$fonts/Jacquard24-Regular.ttf" "$google/jacquard24/Jacquard24-Regular.ttf"
  [[ -f $fonts/IMFeENrm28P.ttf ]] ||
    run curl -fsSL -o "$fonts/IMFeENrm28P.ttf" "$google/imfellenglish/IMFeENrm28P.ttf"
  run fc-cache -f "$fonts"
}

link_all() {
  local pair
  for pair in "$@"; do
    link "$root/${pair%%:*}" "${pair#*:}"
  done
}

install_shell() {
  say "installing the shell layer"
  install_packages "${shell_packages[@]}"
  install_fonts

  say "installing the athanor command"
  run uv tool install --force --editable "$root"

  link_all "${shell_links[@]}"
  if [[ ! -f $home/athanor.toml ]]; then
    run mkdir -p "$home"
    run cp "$root/config/athanor/athanor.toml" "$home/athanor.toml"
  fi

  add_block "$(zshrc)" "$zsh_body"
  if ! grep -qs '^theme *= *"athanor"' "$config/helix/config.toml"; then
    say "For the Helix theme, set theme = \"athanor\" in $config/helix/config.toml."
    say "For the tabs and mode badge, set bufferline = \"always\" and color-modes = true under [editor]."
  fi
  run fc-cache -f
  local face
  face=$("$athanor" font 2>/dev/null || true)
  say "For a terminal other than Athanor's foot, set its font to ${face:-Terminus (TTF) at 16px}."
  if [[ $(basename "${SHELL:-}") != zsh ]]; then
    say "Your login shell is ${SHELL:-unknown}. The prompt needs zsh: chsh -s /usr/bin/zsh"
  fi
}

install_desktop() {
  say "installing the desktop layer"
  install_packages "${desktop_packages[@]}"
  link_all "${desktop_links[@]}"

  if [[ -f $hyprconf && ! -f $hyprlua ]] && only_block "$hyprconf"; then
    # Don't delete hyprland.conf. If the running session can't find it, Hyprland
    # writes a default one with its own keybindings.
    say "Moving Athanor to hyprland.lua. It takes effect at your next login."
    add_block "$hyprlua" "$lua_body"$'\n'"$lua_binds"
  elif [[ -f $hyprlua ]]; then
    if grep -qE 'exec_cmd\(.*\b(waybar|mako|hypridle|swaybg)\b' "$hyprlua"; then
      warn "$hyprlua starts its own waybar, mako, hypridle or swaybg. So does Athanor."
      warn "Comment yours out. Otherwise you'll get two of each."
    fi
    add_block "$hyprlua" "$lua_body"
    if ! grep -qF "$lua_binds" "$hyprlua"; then
      say "Your keybindings stay. Athanor's are in $home/hypr/binds.lua."
      say "To use them, add '$lua_binds' after Athanor's block in $hyprlua."
    fi
  elif [[ -f $hyprconf ]]; then
    warn "$hyprconf uses hyprlang. Hyprland is retiring that format."
    warn "Athanor still supports it for now. Move to hyprland.lua when you can."
    if grep -qE '^[[:space:]]*exec-once[[:space:]]*=.*\b(waybar|mako|hypridle|swaybg)\b' "$hyprconf"; then
      warn "$hyprconf starts its own waybar, mako, hypridle or swaybg. So does Athanor."
      warn "Comment yours out. Otherwise you'll get two of each."
    fi
    add_block "$hyprconf" "$hypr_body"
    if ! grep -qF "$hypr_binds" "$hyprconf"; then
      say "Your keybindings stay. Athanor's are in $home/hypr/binds.conf."
      say "To use them, add '$hypr_binds' to $hyprconf."
    fi
  else
    add_block "$hyprlua" "$lua_body"$'\n'"$lua_binds"
  fi

  say "starting the coredump watcher"
  run systemctl --user daemon-reload
  run systemctl --user enable --now athanor-tomb.path
}

render() {
  say "drawing the plates and fetching the deck"
  run "$athanor" transmute "$(cat "$state/scheme" 2>/dev/null || echo umber)" --no-reload
  run "$athanor" cards fetch || say "The tarot art did not download. Run 'athanor cards fetch' later."
}

uninstall() {
  remove_block "$(zshrc)"
  remove_block "$hyprconf"
  remove_block "$hyprlua"

  if [[ -L $units/athanor-tomb.path ]]; then
    run systemctl --user disable --now athanor-tomb.path || true
  fi
  local pair path bak
  for pair in "${shell_links[@]}" "${desktop_links[@]}"; do
    unlink_ours "${pair#*:}"
  done
  command -v fc-cache >/dev/null && run fc-cache -f
  if [[ -d $units ]] && command -v systemctl >/dev/null; then
    run systemctl --user daemon-reload || true
  fi

  for path in "${legacy_links[@]}"; do
    if ours "$path"; then
      unlink_ours "$path"
      bak=$(compgen -G "$path.athanor-bak.*" | sort | tail -n 1 || true)
      if [[ -n $bak ]]; then
        say "your old $(basename "$path") is at $bak"
      fi
    fi
  done

  if command -v uv >/dev/null && uv tool list 2>/dev/null | grep -q '^athanor '; then
    say "removing the athanor command"
    run uv tool uninstall athanor
  fi

  if [[ -d $home/current ]]; then
    say "removing rendered configs in $home/current"
    run rm -rf "$home/current"
  fi
  if [[ -d $cursors ]]; then
    say "removing the cursors in $cursors"
    run rm -rf "$cursors"
  fi
  if ((purge)); then
    say "purging settings, fonts, cache and state"
    run rm -rf "$home" "$fonts" "$cache" "$state"
    run fc-cache -f
  else
    say "Kept $home/athanor.toml, $fonts and $cache. --purge removes them too."
  fi
  say "No packages were removed. Athanor may have installed some of these:"
  say "  ${shell_packages[*]} ${desktop_packages[*]}"
  say "Only ash remains."
}

if [[ $mode == uninstall ]]; then
  uninstall
  exit 0
fi

has_layer shell && install_shell
has_layer desktop && install_desktop
render

if has_layer desktop; then
  say "Done. Log in to Hyprland to start it."
else
  say "Done. Open a new terminal."
fi
if ((fresh_fonts)); then
  say "New fonts installed. Restart any running terminal before switching its font."
fi
say "If something is wrong, run athanor doctor."
say "The athanor is lit."
