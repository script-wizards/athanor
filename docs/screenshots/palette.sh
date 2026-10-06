#!/usr/bin/env bash
# usage: palette.sh FONT_DIR OUT.png
set -euo pipefail

fonts=$1
out=$2
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

python3 - "$repo" >"$tmp/schemes" <<'EOF'
import sys, tomllib
sys.path.insert(0, sys.argv[1] + "/src")
from athanor import palette, stages
table = tomllib.load(open(sys.argv[1] + "/src/athanor/palette.toml", "rb"))
for name in palette.SCHEMES:
    s = table[name]
    stage = stages.STAGES[name]
    print(s["label"], stage, s["bg"], s["fg"], s["dim"], *s["ansi"])
EOF

col=88
panel_w=$((16 + 8 * col + 8))
panel_h=124
names=(ink vermilion olive ochre slate madder verdigris paper)
font=$fonts/Px437_Tandy2K.ttf

i=0
while read -r label stage bg fg dim rest; do
  read -r -a ansi <<<"$rest"
  draw=()
  for slot in {0..7}; do
    x=$((16 + slot * col))
    draw+=(-fill "${ansi[slot]}" -draw "rectangle $x,40 $((x + col - 9)),63")
    draw+=(-fill "${ansi[slot + 8]}" -draw "rectangle $x,64 $((x + col - 9)),87")
    draw+=(-fill "$dim" -annotate "+$x+108" "${names[slot]}")
  done
  magick -size "${panel_w}x${panel_h}" "xc:$bg" +antialias -font "$font" -pointsize 16 \
    -fill "$fg" -annotate +16+28 "$label" -fill "$dim" -annotate +120+28 "$stage" \
    -stroke none "${draw[@]}" "$tmp/panel$i.png"
  i=$((i + 1))
done <"$tmp/schemes"

magick "$tmp"/panel{0..3}.png -append "$out"
basename "$out"
