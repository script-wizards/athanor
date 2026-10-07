-- Keybindings live in binds.lua: Hyprland fires every bind on a key, so
-- defining them here would double up with yours.

local xdg = os.getenv("XDG_CONFIG_HOME")
local home = ((xdg and xdg ~= "") and xdg or (os.getenv("HOME") .. "/.config")) .. "/athanor"
local bin = os.getenv("HOME") .. "/.local/bin/athanor"
local data = os.getenv("XDG_DATA_HOME")
local notch = ((data and data ~= "") and data or (os.getenv("HOME") .. "/.local/share")) .. "/athanor/athanor-notch.so"

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })

hl.env("XCURSOR_THEME", "athanor")
hl.env("XCURSOR_SIZE", "24")

hl.config({
    general = {
        gaps_in = 6,
        gaps_out = 12,
        border_size = 2,
        layout = "dwindle",
        resize_on_border = true,
    },
    decoration = {
        rounding = 0,
        shadow = { enabled = false },
        blur = { enabled = false },
    },
    animations = { enabled = false },
    dwindle = { preserve_split = true },
    misc = {
        disable_hyprland_logo = true,
        disable_splash_rendering = true,
    },
    input = {
        kb_layout = "us",
        follow_mouse = 1,
    },
})

hl.on("hyprland.start", function()
    hl.exec_cmd(bin .. " wake --no-wall && hyprpaper --config " .. home .. "/current/hypr/hyprpaper.conf")
    hl.exec_cmd(bin .. " stages --follow")
    hl.exec_cmd("waybar --config " .. home .. "/waybar/config.jsonc --style " .. home .. "/current/waybar/style.css")
    hl.exec_cmd("mako --config " .. home .. "/current/mako/config")
    hl.exec_cmd("hypridle --config " .. home .. "/hypr/hypridle.conf")
end)

hl.on("workspace.active", function(ws)
    if not ws or ws.special then
        return
    end
    local ok, levels = pcall(dofile, home .. "/current/hypr/levels.lua")
    if not ok or #levels == 0 then
        return
    end
    local plate = levels[(math.max(ws.id, 1) - 1) % #levels + 1]
    hl.exec_cmd("hyprctl hyprpaper wallpaper '," .. plate .. "'")
end)

local built = io.open(notch)
if built then
    built:close()
    pcall(hl.plugin.load, notch)
end

require(home .. "/current/hypr/colors")
