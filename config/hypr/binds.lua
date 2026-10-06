local xdg = os.getenv("XDG_CONFIG_HOME")
local home = ((xdg and xdg ~= "") and xdg or (os.getenv("HOME") .. "/.config")) .. "/athanor"
local bin = os.getenv("HOME") .. "/.local/bin/athanor"
local mod = "SUPER"

local terminal = "foot --config " .. home .. "/current/foot/foot.ini"
local launcher = "fuzzel --config " .. home .. "/current/fuzzel/fuzzel.ini"

hl.bind(mod .. " + Return", hl.dsp.exec_cmd(terminal))
hl.bind(mod .. " + Space", hl.dsp.exec_cmd(launcher))
hl.bind(mod .. " + Tab", hl.dsp.exec_cmd(bin .. " windows"))
hl.bind(mod .. " + Q", hl.dsp.window.close())
hl.bind(mod .. " + F", hl.dsp.window.fullscreen({ action = "toggle" }))
hl.bind(mod .. " + V", hl.dsp.window.float({ action = "toggle" }))
hl.bind(mod .. " + P", hl.dsp.window.pseudo({ action = "toggle" }))
hl.bind(mod .. " + Escape", hl.dsp.exec_cmd("loginctl lock-session"))
hl.bind(mod .. " + T", hl.dsp.exec_cmd(bin .. " transmute --next"))
hl.bind(mod .. " + SHIFT + E", hl.dsp.exec_cmd(bin .. " quit"))
hl.bind("Print", hl.dsp.exec_cmd('grim -g "$(slurp)" - | wl-copy'))

local directions = {
    H = "left", L = "right", K = "up", J = "down",
    left = "left", right = "right", up = "up", down = "down",
}
for key, direction in pairs(directions) do
    hl.bind(mod .. " + " .. key, hl.dsp.focus({ direction = direction }))
    if #key == 1 then
        hl.bind(mod .. " + SHIFT + " .. key, hl.dsp.window.move({ direction = direction }))
    end
end

for level = 1, 7 do
    hl.bind(mod .. " + " .. level, hl.dsp.focus({ workspace = level }))
    hl.bind(mod .. " + SHIFT + " .. level, hl.dsp.window.move({ workspace = level }))
end

local media = { locked = true, repeating = true }
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%+"), media)
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%-"), media)
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), media)
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), media)
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked = true })
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), { locked = true })
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"), { locked = true })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"), { locked = true })

hl.bind(mod .. " + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind(mod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })
