#!/usr/bin/env bash
# Retakes the README images. Run inside Hyprland with athanor installed.
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/../.." && pwd)
config=${XDG_CONFIG_HOME:-$HOME/.config}
state=${XDG_STATE_HOME:-$HOME/.local/state}/athanor
athanor=$HOME/.local/bin/athanor

die() {
  printf '%s\n' "$*" >&2
  exit 1
}
[[ -n ${HYPRLAND_INSTANCE_SIGNATURE:-} ]] || die "Run this inside a Hyprland session."
for tool in hyprctl grim magick foot nvim fuzzel hyprlock makoctl notify-send python3 uv; do
  command -v "$tool" >/dev/null || die "screenshots need $tool"
done
[[ -x $athanor ]] || die "Athanor isn't installed; run ./install.sh first."

json() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
dispatch() { hyprctl dispatch "$1" >/dev/null; }

read -r W H < <(hyprctl monitors -j | json "d[0]['width'], d[0]['height']" | tr -d '(),')
scheme0=$(cat "$state/scheme" 2>/dev/null || echo umber)
workspace0=$(hyprctl activeworkspace -j | json "d['id']")
demo=$(mktemp -d)
mkdir -p "$demo/athanor"
sed "s|@demo@|$demo|g" "$here/athanor.toml" >"$demo/athanor/athanor.toml"
# The demo XDG_CONFIG_HOME would hide Athanor's fontconfig rules.
[[ -d $config/fontconfig ]] && ln -s "$config/fontconfig" "$demo/fontconfig"

mkdir -p "$demo/grimoire" "$demo/observatory"
almagest=$demo/almagest
git init -q -b main "$almagest"
cp "$here/planetary.c" "$almagest/"
echo planetary >"$almagest/.gitignore"
commit() { # date, message
  GIT_AUTHOR_DATE=$1 GIT_COMMITTER_DATE=$1 git -C "$almagest" \
    -c user.name=Prospero -c user.email=prospero@milan.invalid \
    -c commit.gpgsign=false -c core.hooksPath=/dev/null \
    commit -q --allow-empty -m "$2"
}
git -C "$almagest" add .
commit "2026-09-12T23:41:00" "first light"
commit "2026-09-19T03:12:00" "teach the clock the unequal hours"
commit "2026-09-28T22:07:00" "the moon ran a day behind. no longer"
commit "2026-10-03T01:56:00" "bind the seventh hour to saturn"
foot_ini=$config/athanor/current/foot/foot.ini

window() { # the address of the staged window with this app id
  hyprctl clients -j | json "next((c['address'] for c in d if c['class'] == '$1'), '')"
}
close() {
  local addr
  addr=$(window "$1")
  [[ -n $addr ]] && dispatch "hl.dsp.window.close({ window = 'address:$addr' })"
  return 0
}
restore() {
  local id
  for id in term edit tarot tomb sigil; do close "athanor-shot-$id"; done
  pkill -x fuzzel 2>/dev/null || true
  if pgrep -x hyprlock >/dev/null; then pkill -USR1 -x hyprlock || true; fi
  "$athanor" transmute "$scheme0" >/dev/null 2>&1 || true
  makoctl dismiss --all 2>/dev/null || true
  dispatch "hl.dsp.focus({ workspace = $workspace0 })"
  rm -rf "$demo"
}
trap restore EXIT

launch() { # app id, command, x, y, w, h
  dispatch "hl.dsp.exec_cmd('$2', { float = true, size = {$5, $6}, move = {$3, $4} })"
  for _ in $(seq 50); do
    [[ -n $(window "$1") ]] && return 0
    sleep 0.1
  done
  die "the $1 window never appeared"
}

quiet() { # clear the message line before a shot
  makoctl dismiss --all
  sleep 0.4
}

level=5
gap=12
bar=24
left_w=$((W / 2 - gap - gap / 2))
right_x=$((W / 2 + gap / 2))
right_w=$((W - right_x - gap))
term_h=$((H - bar - 2 * gap))
edit_h=$((H * 55 / 100))
edit_y=$((H - bar - gap - edit_h))

dispatch "hl.dsp.focus({ workspace = $level })"
sleep 0.4
launch athanor-shot-term \
  "env XDG_CONFIG_HOME=$demo ATHANOR_DEMO_REPO=$almagest foot --config $foot_ini --app-id athanor-shot-term zsh $here/terminal.zsh" \
  "$gap" "$gap" "$left_w" "$term_h"
launch athanor-shot-edit \
  "foot --config $foot_ini --app-id athanor-shot-edit --working-directory=$almagest nvim --clean --cmd \"set rtp^=$repo/config/nvim\" -S $here/nvim.lua +13 planetary.c" \
  "$right_x" "$edit_y" "$right_w" "$edit_h"
sleep 2

font_dir=${XDG_DATA_HOME:-$HOME/.local/share}/fonts/athanor
banner() { # scheme
  local bg fg dim plates
  read -r bg fg dim < <(python3 -c "import tomllib; s = tomllib.load(open('$repo/src/athanor/palette.toml', 'rb'))['$1']; print(s['bg'], s['fg'], s['dim'])")
  mapfile -t plates < <(grep -o '"[^"]*\.png"' "$config/athanor/current/hypr/levels.lua" | tr -d '"')
  magick -background none -fill "$fg" +antialias -font "$font_dir/Jacquard24-Regular.ttf" \
    -pointsize 43 label:athanor -trim +repage -filter point -resize 400% "$demo/word.png"
  for line in 1 2; do
    magick -background none -fill "$dim" +antialias -font "$font_dir/Px437_Tandy2K.ttf" -pointsize 16 \
      "label:$([[ $line == 1 ]] && echo 'an alchemical layer' || echo 'for arch and hyprland')" \
      -trim +repage -filter point -resize 200% "$demo/line$line.png"
  done
  magick "${plates[3]}" -crop "320x400+$((W * 760 / 1366))+$((H * 208 / 768))" +repage \
    -fill "$bg" -draw 'rectangle 0,0 125,249' -flop "$demo/sage.png"
  magick "${plates[5]}" -crop "320x400+$((W * 580 / 1366))+$((H * 348 / 768))" +repage "$demo/couple.png"
  magick -size 1280x400 "xc:$bg" "$demo/sage.png" -composite "$demo/couple.png" -geometry +960+0 -composite \
    -gravity north "$demo/word.png" -geometry +0+88 -composite \
    "$demo/line1.png" -geometry +0+248 -composite "$demo/line2.png" -geometry +0+284 -composite \
    "$here/banner.png"
  echo "banner.png"
}

for scheme in umber vellum orpiment cinnabar; do
  "$athanor" transmute "$scheme" >/dev/null
  sleep 2
  quiet
  grim "$here/desktop-$scheme.png"
  echo "desktop-$scheme.png"
  [[ $scheme == umber ]] && banner "$scheme"
done

"$athanor" transmute umber >/dev/null
sleep 2
quiet
notify-send "The work passes into nigredo."
notify-send "sleep was killed by a SIGSEGV on Dlvl 3."
notify-send "A raven arrives" "your pull request was approved."
sleep 0.8
grim -g "0,0 480x42" "$here/message-line.png"
echo "message-line.png"
quiet

"$athanor" quit &
sleep 1.2
read -r qx qy qw qh < <(hyprctl layers -j | json "' '.join(str(v) for v in next((l['x'] - 24, l['y'] - 24, l['w'] + 48, l['h'] + 48) for m in d.values() for ls in m['levels'].values() for l in ls if l['namespace'] == 'launcher'))")
grim -g "$qx,$qy ${qw}x$qh" "$here/quit.png"
pkill -x fuzzel || true
wait || true
echo "quit.png"

"$athanor" draw --png >/dev/null 2>&1 || true
lock_at=2026-10-05T23:04
lock_card="death, reversed"
XDG_CONFIG_HOME=$demo uv run --quiet --project "$repo" python - \
  "$config/athanor/current/hypr/hyprlock.conf" "$demo" "$lock_at" "$lock_card" <<'PY'
import hashlib, json, re, socket, sys
from datetime import datetime
from pathlib import Path
from athanor import cli, config, palette, sigil, tarot, transmute, wall

conf, demo, at, card = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
host = "ariel"
digest = hashlib.sha256(host.encode()).digest()
real_digest, real_print = sigil.host_digest()
fake_print = sigil.fingerprint_text(digest)
now = datetime.fromisoformat(at).astimezone()
draw = tarot.draw_by_name(card)
lines = cli._hour_lines(now, config.load())
lines["card"] = f"Card of the day: {draw.title}"
r = palette.load(transmute.saved_scheme()).roles
markup = cli._lock_markup(lines, f"{r['fg']},{r['active']},{r['dim']}").replace("\n", "<br/>")
# hyprlang needs ## for a literal #.
markup = markup.replace("#", "##")
layout = json.loads(transmute._layout_state().read_text())
png = demo / "card.png"
art = tarot.art_path(draw.card, transmute.cache_dir() / "tarot")
scheme = palette.load(transmute.saved_scheme())
wall.card_image(art, scheme, draw.reversed, "png", png, width=layout["card_w"], scale=layout["scale"])
text = conf.read_text()
text = text.replace("text = $TIME", f"text = {now:%H:%M}")
text = re.sub(r"text = cmd\[update:60000\] .* hour --lock .*", f"text = {markup}", text)
text = re.sub(r"path = .*tarot-day\.png", f"path = {png}", text)
text = re.sub(r"(text = @ ).*(, speak the word:)", r"\1Prospero\2", text)
sigil_png = demo / "sigil.png"
sigil_png.write_bytes(sigil.png(sigil.grid(digest), r["sigil"]))
text = re.sub(r"path = .*/sigil-[a-z]+\.png", f"path = {sigil_png}", text)
text = text.replace(f"text = {socket.gethostname()}\n", f"text = {host}\n")
short = fake_print if len(fake_print) <= 24 else fake_print[:23] + "…"
text = re.sub(r"text = SHA256:\S+", f"text = {short}", text)
(demo / "hyprlock.conf").write_text(text)
PY
hyprlock --config "$demo/hyprlock.conf" >/dev/null 2>&1 &
sleep 4
grim "$here/lockscreen.png"
pkill -USR1 -x hyprlock || true
for _ in $(seq 30); do
  pgrep -x hyprlock >/dev/null || break
  sleep 0.2
  pkill -USR1 -x hyprlock 2>/dev/null || true
done
echo "lockscreen.png"

close athanor-shot-term
close athanor-shot-edit
tarot_w=$((W * 56 / 100))
side_x=$((gap + tarot_w + gap))
side_w=$((W - side_x - gap))
tomb_h=$((term_h * 52 / 100))
reading() { # what, x, y, w, h
  launch "athanor-shot-$1" \
    "env XDG_CONFIG_HOME=$demo ATHANOR_DEMO_REPO=$almagest ATHANOR_REPO=$repo foot --config $foot_ini --app-id athanor-shot-$1 zsh $here/readings.zsh $1" \
    "$2" "$3" "$4" "$5"
}
reading tarot "$gap" "$gap" "$tarot_w" "$term_h"
reading tomb "$side_x" "$gap" "$side_w" "$tomb_h"
reading sigil "$side_x" "$((gap + tomb_h + gap))" "$side_w" "$((term_h - tomb_h - gap))"
sleep 4
quiet
grim "$here/readings.png"
echo "readings.png"

mapfile -t plates < <(grep -o '"[^"]*\.png"' "$config/athanor/current/hypr/levels.lua" | tr -d '"')
# Point sampling, since any smoothing blurs the dither to grey. montage fails
# without a font even when there are no labels.
magick montage -font "$font_dir/Px437_Tandy2K.ttf" "${plates[@]}" -filter point -geometry "$((W / 2))x$((H / 2))+4+4" \
  -tile 4x2 -background '#16120e' "$here/levels.png"
echo "levels.png"

"$here/palette.sh" "$font_dir" "$here/palette.png"
