![athanor](docs/screenshots/banner.png)

Athanor is an alchemical layer for Arch and Hyprland, inspired by Western
esotericism and dungeon crawling.

![Umber](docs/screenshots/desktop-umber.png)

## The Signs

The bar shows the planetary hour. Athanor calculates it from your own sunrise
and sunset and pairs each hour with a tarot trump from the Golden Dawn. Each
machine draws its own card of the day and gets a lockscreen sigil made from its
SSH host key. `athanor draw 3` lays a three-card spread. When a program crashes
you get a notification and `athanor tomb` draws its tombstone.

![The signs](docs/screenshots/readings.png)

## The Colors

There are four color schemes. Each one is a stage of the alchemical Magnum
Opus: Umber is *nigredo*, Vellum is *albedo*, Orpiment is *citrinitas* and
Cinnabar is *rubedo*. Switch between them with `athanor transmute`. If you set
`stages = true` they change on their own as the sun moves through the day.

| | |
|---|---|
| ![Vellum](docs/screenshots/desktop-vellum.png) | ![Orpiment](docs/screenshots/desktop-orpiment.png) |
| ![Cinnabar](docs/screenshots/desktop-cinnabar.png) | ![The lockscreen](docs/screenshots/lockscreen.png) |

The colors are named after old pigments. Orpiment is a yellow arsenic ore whose
name means gold paint. Cinnabar is the mercury ore that vermilion was ground
from. Body text has at least 7:1 contrast against the background and every
accent has 4.5:1.

![The palette](docs/screenshots/palette.png)

Helix, micro and nvim get themes built from the terminal's 16 colors. They
change with the scheme. The installer puts them in place and tells you the line
to add to each editor's config. Lualine has an athanor theme too. Its bar has
no background of its own. Set lualine's `section_separators` and
`component_separators` to `''` to keep the arrows from drawing as loose
triangles.

## The Levels

The seven workspaces are dungeon levels. There's one for each classical planet
and each has its own Doré engraving dithered down to two tones. Set
`levels = false` under `[display]` in `athanor.toml` to keep one plate on all
of them.

![The levels](docs/screenshots/levels.png)

The wallpapers are Gustave Doré's wood engravings, dithered to two colors with
Floyd-Steinberg. To make your own from any image you only need ImageMagick:

```sh
magick in.jpg -colorspace gray -resize 960x540^ -gravity center -extent 960x540 \
  -sigmoidal-contrast 4x50% -dither FloydSteinberg -monochrome \
  +level-colors '#16120e,#5c4c39' -filter point -resize 200% out.png
```

That draws the image at half of 1920x1080 and doubles every pixel. Doubling keeps
the dither crisp. The two colors are the ground and the ink. Doré's engravings are
all public domain on Wikimedia Commons.

## The Screen

The bar at the bottom is a roguelike status line. `Dlvl` stands for dungeon
level and shows the workspace you're on. `$` is free disk space. `Hp` is the
battery and `T` counts minutes since boot. Notifications show up one at a time
on the top line. `--More--` means more are waiting.

![The message line](docs/screenshots/message-line.png)

The window titles set into the frames come from the notch, an optional plugin
(see Install).

Super+Shift+E asks before quitting Hyprland. Run `athanor guide` for the rest.

![The quit prompt](docs/screenshots/quit.png)

## Install

```sh
git clone https://github.com/script-wizards/athanor
cd athanor
./install.sh --dry-run
./install.sh
```

Athanor keeps its files in `~/.config/athanor`. Outside that folder it only
adds a marked block to the top of your `.zshrc` and your `hyprland.lua`. Your
own settings load after the block and override it.

The prompt names each terminal window after its folder, or after the command
running in it. Set `ATHANOR_TITLE=0` in your `.zshrc` to keep your own titles.

Without Hyprland, `./install.sh shell` installs just the command, the prompt and
the fonts. `./install.sh --uninstall` removes everything.

`./install.sh notch` also builds a small Hyprland plugin. It sets each window's
title into the top of its border and draws a double rule round the focused
window. A plugin only runs on the Hyprland it was built for, so run it again
after every upgrade. `athanor doctor` tells you when.

## The Name

An athanor was an alchemist's furnace. The word comes from the Arabic
*al-tannūr* (the oven). Tandoor comes from the same root. The furnace was built
as a tower filled with charcoal that slid down into the fire as it burned. That
let it hold a low steady heat for weeks without anyone tending it. When did you
last turn off your laptop?

## Inspirations

Athanor borrows from Doré, the Golden Dawn, NetHack and a lot more. The full list
is in [INSPIRATIONS.md](INSPIRATIONS.md).

## License

MIT. The plates, cards and fonts have their own terms, listed in
[NOTICE.md](NOTICE.md).
